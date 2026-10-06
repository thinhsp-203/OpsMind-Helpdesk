import os
import secrets

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in {"1", "true", "yes"}
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if not DEMO_MODE:
        raise RuntimeError("SECRET_KEY must be configured when DEMO_MODE is disabled.")
    SECRET_KEY = secrets.token_urlsafe(48)
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))
if TOKEN_EXPIRE_MINUTES < 1:
    raise RuntimeError("TOKEN_EXPIRE_MINUTES must be positive.")
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
