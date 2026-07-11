import os
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
url = "postgresql://neondb_owner:npg_SmE7oIUa0wxn@ep-late-firefly-ahguzpnw-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
engine = sa.create_engine(url)
Session = sessionmaker(bind=engine)
db = Session()
try:
    for row in db.execute(sa.text("SELECT email FROM users")).fetchall():
        print(row.email)
except Exception as e:
    print(e)
