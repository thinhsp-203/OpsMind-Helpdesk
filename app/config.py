import logging
import os
import secrets

logger = logging.getLogger(__name__)

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes"}
SECRET_KEY = os.getenv("SECRET_KEY")
INSECURE_SECRET_KEYS = {
    "change-this-to-a-secure-random-secret-key-at-least-32-chars",
    "secret",
    "secretkey",
    "your-secret-key",
}
if not DEMO_MODE and SECRET_KEY:
    if SECRET_KEY in INSECURE_SECRET_KEYS or len(SECRET_KEY) < 32:
        raise RuntimeError(
            "Insecure or short SECRET_KEY detected in production/non-demo environment (minimum 32 characters required). "
            "Please configure a unique cryptographically random SECRET_KEY in your environment variables."
        )
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(48)
    if not DEMO_MODE:
        logger.warning(
            "SECRET_KEY not set in environment. Auto-generated a secure ephemeral key for this session. "
            "For persistent sessions across restarts, set SECRET_KEY in your environment variables."
        )
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))
if TOKEN_EXPIRE_MINUTES < 1:
    raise RuntimeError("TOKEN_EXPIRE_MINUTES must be positive.")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
INITIAL_ADMIN_USERNAME = os.getenv("INITIAL_ADMIN_USERNAME", "").strip()
INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD", "")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DATABASE_PATH = os.getenv(
    "HELPDESK_DB_PATH",
    str(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "helpdesk.sqlite3")),
)
STORAGE_PATH = os.getenv(
    "HELPDESK_STORAGE_PATH",
    str(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")),
)

# LLM Generation settings for RAG (optional, with safe fallback)
ENABLE_LLM_GENERATION = os.getenv("ENABLE_LLM_GENERATION", "false").lower() in {"1", "true", "yes"}
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", os.getenv("GROQ_API_KEY", ""))).strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "5.0"))

def _get_env_case_insensitive(key: str, default: str = "") -> str:
    val = os.getenv(key)
    if val is not None:
        return val
    key_upper = key.upper()
    for k, v in os.environ.items():
        if k.upper() == key_upper:
            return v
    return default


# Email settings (Multi-provider support: SMTP, Resend API, Brevo API, Webhook, Mock/Console)
EMAIL_PROVIDER = _get_env_case_insensitive("EMAIL_PROVIDER", "").strip().lower()
RESEND_API_KEY = _get_env_case_insensitive("RESEND_API_KEY", "").strip()
BREVO_API_KEY = _get_env_case_insensitive("BREVO_API_KEY", "").strip()
EMAIL_WEBHOOK_URL = _get_env_case_insensitive("EMAIL_WEBHOOK_URL", "").strip()

# SMTP Email settings
SMTP_ENABLED = os.getenv("SMTP_ENABLED", "false").lower() in {"1", "true", "yes"}
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@opsmind.internal")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}
SMTP_SSL_VERIFY = os.getenv("SMTP_SSL_VERIFY", "true").lower() in {"1", "true", "yes"}

# Effective Sender Address: prefer explicit EMAIL_FROM or SMTP_FROM_EMAIL, or fallback to SMTP_USER if it's an email
EMAIL_FROM = _get_env_case_insensitive("EMAIL_FROM", "").strip() or SMTP_FROM_EMAIL
if (not EMAIL_FROM or EMAIL_FROM == "noreply@opsmind.internal") and SMTP_USER and "@" in SMTP_USER:
    EMAIL_FROM = SMTP_USER

RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", "15"))
if RESET_TOKEN_EXPIRE_MINUTES < 1:
    raise RuntimeError("RESET_TOKEN_EXPIRE_MINUTES must be positive.")
