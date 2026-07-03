"""
email_service.py

Core email-sending logic, designed to be called from FastAPI BackgroundTasks
so requests return immediately while emails send after the response.

Key design points:
    - `_safe_send()` is the only function background tasks should ever call
      directly (via the high-level `send_*` functions below) — it NEVER
      raises. Background tasks run after the response has already been
      sent, so an unhandled exception there can't reach the client anyway;
      it would just be a silent, unlogged failure. We log instead.
    - `_send_smtp_email()` retries transient failures a few times before
      giving up.
    - Swap `_send_smtp_email()` for a provider SDK (SendGrid, SES, Postmark,
      etc.) if you outgrow raw SMTP — the high-level `send_*` functions and
      the router don't need to change.
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.email_config import email_settings
from app.services import email_templates as templates

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Raised internally when an email fails to send after all retries."""


def _send_smtp_email(to_email: str, subject: str, html_body: str, retries: int = 2) -> None:
    """
    Low-level SMTP send with basic retry logic.
    Raises EmailSendError only after all attempts are exhausted.
    """
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{email_settings.FROM_NAME} <{email_settings.FROM_EMAIL}>"
    message["To"] = to_email
    message.attach(MIMEText(html_body, "html"))

    last_error: Optional[Exception] = None
    total_attempts = retries + 1

    for attempt in range(1, total_attempts + 1):
        try:
            with smtplib.SMTP(email_settings.HOST, email_settings.PORT, timeout=10) as server:
                if email_settings.USE_TLS:
                    server.starttls()
                if email_settings.USERNAME and email_settings.PASSWORD:
                    server.login(email_settings.USERNAME, email_settings.PASSWORD)
                server.sendmail(email_settings.FROM_EMAIL, [to_email], message.as_string())

            logger.info("Email sent to %s (subject='%s') on attempt %d", to_email, subject, attempt)
            return

        except smtplib.SMTPAuthenticationError as exc:
            # Bad credentials won't fix themselves on retry — fail fast
            logger.error("SMTP authentication failed: %s", exc)
            raise EmailSendError(f"SMTP authentication failed: {exc}") from exc

        except smtplib.SMTPException as exc:
            last_error = exc
            logger.warning("SMTP error sending to %s on attempt %d/%d: %s", to_email, attempt, total_attempts, exc)

        except (OSError, TimeoutError) as exc:
            last_error = exc
            logger.warning("Connection error sending to %s on attempt %d/%d: %s", to_email, attempt, total_attempts, exc)

        except Exception as exc:
            last_error = exc
            logger.exception("Unexpected error sending to %s on attempt %d/%d", to_email, attempt, total_attempts)

    logger.error("Failed to send email to %s after %d attempt(s): %s", to_email, total_attempts, last_error)
    raise EmailSendError(f"Failed to send email to {to_email}: {last_error}")


def _safe_send(to_email: str, subject: str, html_body: str) -> None:
    """
    Entry point for all background tasks. Never raises — failures are
    logged so a broken/slow SMTP server can't crash the background task
    runner or produce an unhandled exception after the response is sent.
    """
    try:
        _send_smtp_email(to_email, subject, html_body)
    except EmailSendError as exc:
        logger.error("Email delivery ultimately failed: %s", exc)
        # Hook a fallback here if desired, e.g.:
        #   - write to a "failed_emails" table for manual retry
        #   - push to a dead-letter queue
        #   - alert on-call via Slack/PagerDuty
    except Exception as exc:
        logger.exception("Unexpected failure in _safe_send: %s", exc)


# ---------------------------------------------------------------------------
# High-level notification functions — pass these to BackgroundTasks.add_task
# ---------------------------------------------------------------------------

def send_appointment_confirmation(
    to_email: str,
    patient_name: str,
    doctor_name: str,
    appointment_time: datetime,
    location: Optional[str] = None,
) -> None:
    subject, html = templates.appointment_confirmation_email(
        patient_name, doctor_name, appointment_time, location
    )
    _safe_send(to_email, subject, html)


def send_appointment_reminder(
    to_email: str,
    patient_name: str,
    doctor_name: str,
    appointment_time: datetime,
    hours_before: Optional[int] = None,
) -> None:
    subject, html = templates.appointment_reminder_email(
        patient_name, doctor_name, appointment_time, hours_before
    )
    _safe_send(to_email, subject, html)


def send_appointment_cancellation(
    to_email: str,
    patient_name: str,
    doctor_name: str,
    appointment_time: datetime,
    reason: Optional[str] = None,
) -> None:
    subject, html = templates.appointment_cancellation_email(
        patient_name, doctor_name, appointment_time, reason
    )
    _safe_send(to_email, subject, html)


def send_appointment_reschedule(
    to_email: str,
    patient_name: str,
    doctor_name: str,
    old_time: datetime,
    new_time: datetime,
) -> None:
    subject, html = templates.appointment_reschedule_email(
        patient_name, doctor_name, old_time, new_time
    )
    _safe_send(to_email, subject, html)


def send_medication_reminder(
    to_email: str,
    patient_name: str,
    medicine: str,
    dosage: Optional[str] = None,
    frequency: Optional[str] = None,
) -> None:
    subject, html = templates.medication_reminder_email(
        patient_name, medicine, dosage, frequency
    )
    _safe_send(to_email, subject, html)
