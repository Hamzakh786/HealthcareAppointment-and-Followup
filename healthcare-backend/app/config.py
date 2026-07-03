"""
Centralized configuration. Loads a `.env` file if present (see .env.example)
and falls back to development-safe defaults otherwise.
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./auth.db")

    # --- JWT ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-only-secret-CHANGE-ME")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # --- Forgot password ---
    RESET_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", "30"))

    # --- App ---
    APP_NAME: str = os.getenv("APP_NAME", "Authentication Module")
    ENV: str = os.getenv("ENV", "development")
    CORS_ORIGINS: list[str] = [
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()
    ]

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"


settings = Settings()

if settings.is_production and settings.SECRET_KEY == "dev-only-secret-CHANGE-ME":
    raise RuntimeError(
        "SECRET_KEY is still the default dev value. Set a strong SECRET_KEY "
        "in your environment before running in production."
    )
