# backend/app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Read DB URL from env (tests can set this before importing)
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("DB_URL") or "sqlite:///:memory:"

# For sqlite, set check_same_thread flag
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# create engine but don't import models here
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Base declarative class for models to inherit
Base = declarative_base()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
