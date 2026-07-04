import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Use standard postgresql:// for SQLAlchemy
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://vyapar_admin:vyapar_password_123@localhost:5433/vyapar_pulse")

# When connecting from localhost to docker-compose postgres port 5432 we might need localhost instead of 'db' depending on execution context.
# We will check if we are in docker by a simple environment variable, or just use the connection string as provided.

engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True, 
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
