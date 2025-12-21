"""Application configuration"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Application
    APP_NAME: str = "OneiroScope"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database (optional in test environments)
    DATABASE_URL: str | None = None
    DATABASE_URL_SYNC: str | None = None

    # Redis
    REDIS_URL: str | None = None

    # Security
    SECRET_KEY: str | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    @property
    def allowed_origins_list(self) -> List[str]:
        origins: List[str] = []
        for origin in self.ALLOWED_ORIGINS.split(","):
            cleaned = origin.strip()
            if not cleaned:
                continue

            if not cleaned.startswith(("http://", "https://")):
                cleaned = f"https://{cleaned}"

            origins.append(cleaned)

        return origins

    # API Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    TOGETHER_API_KEY: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # YooKassa
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""

    # LLM Configuration
    LLM_PRIMARY_MODEL: str = "gpt-4o-mini"
    LLM_FALLBACK_MODEL: str = "claude-3-haiku-20240307"
    LLM_CONFIDENCE_THRESHOLD: float = 0.60
    LLM_BUDGET_LIMIT_USD: float = 100.0
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1000

    # ASR Configuration
    ASR_CONFIDENCE_THRESHOLD: float = 0.90
    ASR_MAX_DURATION: int = 180  # seconds

    # Monitoring
    SENTRY_DSN: str = ""
    PROMETHEUS_ENABLED: bool = True

    # Rate Limiting
    RATE_LIMIT_PER_USER: int = 10
    RATE_LIMIT_GLOBAL: int = 1000


# Global settings instance
settings = Settings()
