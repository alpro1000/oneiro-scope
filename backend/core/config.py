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
    # Comma-separated browser origins allowed to call this API with credentials.
    # The default is a DEVELOPMENT value: in production it lets nothing through,
    # and the only symptom is in the user's browser console, where the server
    # never looks. `cors_problem()` below turns that into a startup line and a
    # row in /connect/diagnostics rather than a mystery.
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    # Opt-in regex for origins that cannot be enumerated — Vercel gives every
    # preview deploy its own hostname. Left empty by default on purpose: this
    # API answers with credentials, so a pattern that is wider than intended
    # hands cookies to whoever matches it. Anchor it (^…$) and keep it tight.
    ALLOWED_ORIGIN_REGEX: str = ""

    # Where a quota refusal points the user to manage their plan. The portal
    # serves /account on this same service, so a relative path is the honest
    # default; set an absolute URL when the account page lives elsewhere.
    ACCOUNT_URL: str | None = None

    # --- Remote MCP (connector surface) -------------------------------------
    # Serves the MCP server over HTTP so Claude / ChatGPT / Gemini can add it
    # by URL. See docs/deploy/mcp-connector.md.
    MCP_ENABLED: bool = True
    MCP_PATH: str = "/mcp"
    # Public canonical URL of the MCP endpoint — also the OAuth audience.
    # e.g. https://oneiroscope-backend.onrender.com/mcp
    MCP_PUBLIC_URL: str | None = None
    # Host header values the MCP transport accepts (DNS-rebinding protection).
    # Comma-separated; empty means "derive from MCP_PUBLIC_URL". Localhost is
    # always allowed so local clients keep working.
    MCP_ALLOWED_HOSTS: str = ""

    # OAuth 2.1 resource-server settings. The authorization server itself is
    # external (Auth0 / Clerk / Stytch / WorkOS…); we only validate its tokens.
    MCP_REQUIRE_AUTH: bool = True
    MCP_AUTH_ISSUER: str | None = None
    MCP_AUTH_JWKS_URL: str | None = None  # defaults to issuer + /.well-known/jwks.json
    MCP_AUTH_AUDIENCE: str | None = None  # defaults to MCP_PUBLIC_URL
    MCP_REQUIRED_SCOPES: str = ""  # space-separated, empty = none required
    # Scopes advertised in RFC 9728 metadata when none are required (WP-15).
    # Clients (Claude connector, Auth0 dynamic registration) read
    # `scopes_supported` to decide what to request; publishing nothing made
    # them guess. Standard OIDC scopes are always safe to request.
    MCP_ADVERTISED_SCOPES: str = "openid profile email"
    # Local-only shortcut: a static bearer token. Refused in production.
    MCP_DEV_TOKEN: str | None = None

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

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}

    def cors_problem(self) -> str | None:
        """Why browsers will be refused, in one sentence — or None if fine.

        CORS is the one misconfiguration that leaves the server looking
        perfectly healthy: every endpoint answers 200, `/health` is green, the
        log is clean, and only the browser knows the response is unusable
        because it carries no `Access-Control-Allow-Origin`. That asymmetry is
        exactly the silent degradation conventions.md §12 forbids, so the
        condition is named here once and reported everywhere it matters.
        """
        origins = self.allowed_origins_list
        if not origins and not self.ALLOWED_ORIGIN_REGEX:
            return (
                "ALLOWED_ORIGINS is empty — every cross-origin browser request "
                "will be blocked by CORS."
            )
        if not self.is_production:
            return None

        remote = [
            o for o in origins
            if "localhost" not in o and "127.0.0.1" not in o
        ]
        if not remote and not self.ALLOWED_ORIGIN_REGEX:
            return (
                f"ENVIRONMENT=production but ALLOWED_ORIGINS is {origins!r} — "
                "only localhost is allowed, so the deployed frontend is blocked "
                "by CORS on every call (login, city search, lunar days). Set "
                "ALLOWED_ORIGINS to the site's own origin, with scheme, "
                "comma-separated for several."
            )
        return None

    # API Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    TOGETHER_API_KEY: str = ""

    # Accounts that operate this deployment: comma-separated emails and/or
    # OAuth subjects. They resolve to the PRO tier, so the people who build and
    # support the product can exercise the paid paths they ship. Empty by
    # default — a deployment that says nothing bypasses nothing. The identity
    # compared is the AUTHENTICATED one; nothing a caller asserts about itself
    # takes part. See `backend/services/billing/quotas.py::is_staff`.
    STAFF_ACCOUNTS: str = ""

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
