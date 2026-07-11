import os
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Use standard postgresql:// for SQLAlchemy
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://vyapar_local:vyapar_local_password@127.0.0.1:5433/vyapar_pulse",
)

if os.getenv("APP_ENV", "development").lower() == "production":
    if "DATABASE_URL" not in os.environ:
        raise RuntimeError("DATABASE_URL is required in production")
    parsed = urllib.parse.urlparse(DATABASE_URL)
    hostname = (parsed.hostname or "").lower()
    if hostname in {"localhost", "127.0.0.1", "::1", "0.0.0.0", "db"}:
        raise RuntimeError("Production DATABASE_URL must point to managed PostgreSQL, not localhost or compose")

# When connecting from localhost to docker-compose postgres port 5432 we might need localhost instead of 'db' depending on execution context.
# We will check if we are in docker by a simple environment variable, or just use the connection string as provided.

engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
