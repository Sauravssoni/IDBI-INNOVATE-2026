import os
from typing import Any
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()


def _clean_database_url(raw_url: str | None) -> str:
    if raw_url is None:
        return ""
    url = raw_url.strip().strip('"').strip("'")
    return url.replace("postgres://", "postgresql://", 1)


APP_ENV = os.getenv("APP_ENV", "development").lower()
DEFAULT_LOCAL_DATABASE_URL = (
    "postgresql://vyapar_local:vyapar_local_password@127.0.0.1:5433/vyapar_pulse"
)
DATABASE_URL = _clean_database_url(os.getenv("DATABASE_URL"))

if not DATABASE_URL and APP_ENV != "production":
    DATABASE_URL = DEFAULT_LOCAL_DATABASE_URL

if APP_ENV == "production":
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required in production")
    parsed = urllib.parse.urlparse(DATABASE_URL)
    hostname = (parsed.hostname or "").lower()
    if hostname in {"localhost", "127.0.0.1", "::1", "0.0.0.0", "db"}:
        raise RuntimeError(
            "Production DATABASE_URL must point to managed PostgreSQL, not localhost or compose"
        )
    if parsed.scheme != "postgresql":
        raise RuntimeError("Production DATABASE_URL must use postgresql://")
    query = urllib.parse.parse_qs(parsed.query)
    if query.get("sslmode", [""])[0] not in {"require", "verify-ca", "verify-full"}:
        raise RuntimeError(
            "Production DATABASE_URL must require TLS with sslmode=require or stronger"
        )

# When connecting from localhost to docker-compose postgres port 5432 we might need localhost instead of 'db' depending on execution context.
# We will check if we are in docker by a simple environment variable, or just use the connection string as provided.

engine_kwargs: dict[str, Any] = {"pool_pre_ping": True, "echo": False}
if APP_ENV == "production":
    engine_kwargs["poolclass"] = NullPool

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
