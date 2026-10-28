import os

from dotenv import load_dotenv

# Load a local .env when present; real environment variables still take precedence.
load_dotenv()

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
SESSION_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", "72"))
COOKIE_NAME = "bs_session"

if ENVIRONMENT not in {"development", "test", "production"}:
    raise RuntimeError("ENVIRONMENT must be development, test, or production")
if SESSION_TTL_HOURS < 1:
    raise RuntimeError("SESSION_TTL_HOURS must be at least 1")
if ENVIRONMENT == "production" and not COOKIE_SECURE:
    raise RuntimeError("COOKIE_SECURE must be true in production")
