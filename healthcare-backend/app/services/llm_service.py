"""
llm_service.py

Hugging Face Transformers integration using Qwen/Qwen2.5-1.5B-Instruct.

Provides three high-level generation functions, each returning structured
JSON:
    - generate_pre_visit_summary(payload)
    - generate_post_visit_summary(payload)
    - generate_prescription_explanation(payload)

Design notes:
    - Model + tokenizer are loaded lazily and cached in a thread-safe
      singleton (ModelManager) so they're loaded once and reused across
      requests, not reloaded per-call.
    - Every failure mode (model load failure, OOM/runtime errors during
      generation, malformed JSON in the model's output) is caught and
      converted into a structured {"success": False, "error": "..."} result
      instead of raising / crashing the request.
    - Nothing here talks to the database — that's handled by the router /
      db_service layer, keeping this module a pure "prompt in, JSON out"
      service that's easy to test and swap models in.
"""

import json
import logging
import re
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"


class LLMNotReadyError(Exception):
    """Raised when the model/tokenizer failed to load."""


class LLMGenerationError(Exception):
    """Raised when text generation itself fails (OOM, runtime error, etc)."""


class LLMOutputParseError(Exception):
    """Raised when the model's output could not be parsed as valid JSON."""


class ModelManager:
    """
    Thread-safe singleton wrapper around the Qwen model + tokenizer.

    The model is NOT loaded at import time — importing this module is
    always safe and fast. Loading happens on first use (or via an explicit
    `preload_model()` call at app startup).
    """

    _instance: Optional["ModelManager"] = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = "cpu"
        self._load_lock = threading.Lock()
        self._loaded = False
        self._load_error: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "ModelManager":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = ModelManager()
        return cls._instance

    def load(self) -> None:
        """Load model + tokenizer. Safe to call multiple times (no-op once loaded)."""
        if self._loaded:
            return

        with self._load_lock:
            if self._loaded:  # re-check inside the lock
                return
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer

                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info("Loading model '%s' on device '%s'...", MODEL_NAME, self.device)

                self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
                self.model = AutoModelForCausalLM.from_pretrained(
                    MODEL_NAME,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map="auto" if self.device == "cuda" else None,
                )
                if self.device == "cpu":
                    self.model.to(self.device)

                self.model.eval()
                self._loaded = True
                self._load_error = None
                logger.info("Model '%s' loaded successfully.", MODEL_NAME)

            except Exception as exc:
                self._loaded = False
                self._load_error = str(exc)
                logger.exception("Failed to load model '%s'", MODEL_NAME)
                raise LLMNotReadyError(f"Failed to load model '{MODEL_NAME}': {exc}") from exc

    @property
    def is_ready(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.3,
    ) -> str:
        """Run one chat-style generation and return the raw decoded text."""
        if not self._loaded:
            self.load()  # attempt lazy load; raises LLMNotReadyError on failure

        try:
            import torch

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            prompt_text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = self.tokenizer(prompt_text, return_tensors="pt").to(self.device)

            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    do_sample=temperature > 0,
                    pad_token_id=self.tokenizer.eos_token_id,
                )

            generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
            text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
            return text.strip()

        except LLMNotReadyError:
            raise
        except RuntimeError as exc:
            # Commonly CUDA OOM or other runtime/hardware failures
            logger.exception("Runtime error during generation")
            raise LLMGenerationError(f"Model runtime error during generation: {exc}") from exc
        except Exception as exc:
            logger.exception("Unexpected error during generation")
            raise LLMGenerationError(f"Unexpected error during generation: {exc}") from exc


def preload_model() -> None:
    """
    Optional: call on app startup to eagerly load the model instead of
    lazily loading it on the first request. Non-fatal — if loading fails
    here, the app still starts; endpoints will surface a clear 502 error
    until the model becomes available (e.g. after fixing resources/network
    and restarting).
    """
    try:
        ModelManager.get_instance().load()
    except LLMNotReadyError as exc:
        logger.warning("Model preload failed at startup: %s", exc)


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Robustly extract a JSON object from raw model output. Handles:
      - plain JSON
      - JSON wrapped in ```json ... ``` fences
      - JSON with stray leading/trailing text around it
    """
    cleaned = text.strip()

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace_match:
            cleaned = brace_match.group(0)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMOutputParseError(
            f"Could not parse model output as JSON: {exc}. Raw output (truncated): {text[:500]}"
        ) from exc


def _safe_generate_json(
    system_prompt: str, user_prompt: str, max_new_tokens: int = 512
) -> Dict[str, Any]:
    """
    Wraps ModelManager.generate() + JSON extraction with unified error
    handling. Always returns a dict — either the parsed result or a
    structured error payload — and never raises to the caller.

    Return shape:
        {"success": bool, "data": dict | None, "raw_output": str | None, "error": str | None}
    """
    manager = ModelManager.get_instance()
    try:
        raw_output = manager.generate(system_prompt, user_prompt, max_new_tokens=max_new_tokens)
        parsed = _extract_json(raw_output)
        return {"success": True, "data": parsed, "raw_output": raw_output, "error": None}

    except LLMNotReadyError as exc:
        return {"success": False, "data": None, "raw_output": None, "error": f"Model unavailable: {exc}"}
    except LLMGenerationError as exc:
        return {"success": False, "data": None, "raw_output": None, "error": f"Generation failed: {exc}"}
    except LLMOutputParseError as exc:
        return {"success": False, "data": None, "raw_output": None, "error": f"Invalid model output: {exc}"}
    except Exception as exc:
        logger.exception("Unhandled error in _safe_generate_json")
        return {"success": False, "data": None, "raw_output": None, "error": f"Unexpected error: {exc}"}


# ---------------------------------------------------------------------------
# High-level, domain-specific functions
# ---------------------------------------------------------------------------

def generate_pre_visit_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload keys: patient_name, age, symptoms, medical_history, current_medications
    """
    system_prompt = (
        "You are a clinical assistant preparing a concise pre-visit summary for a doctor. "
        "Respond ONLY with a valid JSON object — no markdown, no commentary, no code "
        "fences — using exactly this schema:\n"
        '{"chief_complaint": string, "key_symptoms": [string], '
        '"relevant_history": string, "risk_flags": [string], "suggested_questions": [string]}'
    )
    user_prompt = (
        f"Patient name: {payload.get('patient_name')}\n"
        f"Age: {payload.get('age', 'unknown')}\n"
        f"Reported symptoms: {payload.get('symptoms')}\n"
        f"Medical history: {payload.get('medical_history') or 'none provided'}\n"
        f"Current medications: {payload.get('current_medications') or 'none provided'}\n"
        "Summarize this for the doctor ahead of the visit."
    )
    return _safe_generate_json(system_prompt, user_prompt)


def generate_post_visit_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload keys: patient_name, doctor_notes, diagnosis, treatment_plan
    """
    system_prompt = (
        "You are a clinical assistant creating a patient-friendly post-visit summary. "
        "Respond ONLY with a valid JSON object — no markdown, no commentary, no code "
        "fences — using exactly this schema:\n"
        '{"visit_summary": string, "diagnosis": string, "treatment_plan": string, '
        '"next_steps": [string], "warning_signs": [string]}'
    )
    user_prompt = (
        f"Patient name: {payload.get('patient_name')}\n"
        f"Doctor notes: {payload.get('doctor_notes')}\n"
        f"Diagnosis: {payload.get('diagnosis') or 'not specified'}\n"
        f"Treatment plan: {payload.get('treatment_plan') or 'not specified'}\n"
        "Write a clear, simple summary the patient can understand."
    )
    return _safe_generate_json(system_prompt, user_prompt)


def generate_prescription_explanation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload keys: medicines, doctor_notes, patient_language_level
    """
    level = payload.get("patient_language_level") or "simple"
    system_prompt = (
        f"You are a clinical assistant explaining a prescription to a patient in {level} "
        "language. Respond ONLY with a valid JSON object — no markdown, no commentary, no "
        "code fences — using exactly this schema:\n"
        '{"medicines": [{"name": string, "purpose": string, "how_to_take": string, '
        '"common_side_effects": [string]}], "general_instructions": string, '
        '"when_to_contact_doctor": string}'
    )
    user_prompt = (
        f"Prescribed medicines: {payload.get('medicines')}\n"
        f"Doctor notes: {payload.get('doctor_notes') or 'none'}\n"
        "Explain this prescription to the patient."
    )
    return _safe_generate_json(system_prompt, user_prompt)
