import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.db.session import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE;"))
    conn.execute(text("CREATE SCHEMA public;"))
    conn.commit()

print("Dropped and recreated public schema.")
