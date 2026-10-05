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
DATABASE_PATH = os.getenv(
    "HELPDESK_DB_PATH",
    str(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "helpdesk.sqlite3")),
)
