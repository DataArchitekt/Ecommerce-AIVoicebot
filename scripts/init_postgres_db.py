from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app import db_models   # ensures all models register with Base
import os

db_url = os.getenv("DB_URL") or os.getenv("DATABASE_URL")
print("Using DB:", db_url)

engine = create_engine(db_url)

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Done.")
