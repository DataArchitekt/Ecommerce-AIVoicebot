from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from backend.db import db_models 
import os

db_url = os.getenv("DB_URL") or os.getenv("DATABASE_URL")
print("Using DB:", db_url)

engine = create_engine(db_url)

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Done.")