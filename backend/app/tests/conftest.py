# backend/app/tests/conftest.py
import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend/.env is loaded early so DB_URL is available
root = Path(__file__).resolve().parents[2]  # repo-root/backend/app/tests -> repo-root/backend
env_path = root / "backend" / ".env"
if env_path.exists():
    load_dotenv(env_path)

# For tests prefer an in-memory sqlite DB unless DB_URL explicitly set
if not os.environ.get("DATABASE_URL") and not os.environ.get("DB_URL"):
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Import database (engine + Base) first — this module must NOT import models
from backend.app import database as _database

# Now import models so they register with Base
from backend.app import db_models  # noqa: F401

# Create the tables once per test session
@pytest.fixture(scope="session", autouse=True)
def _create_test_db():
    _database.Base.metadata.create_all(bind=_database.engine)
    yield
    _database.Base.metadata.drop_all(bind=_database.engine)

# Provide a DB session fixture for tests
from sqlalchemy.orm import sessionmaker

SessionTesting = sessionmaker(bind=_database.engine)

@pytest.fixture(scope="function")
def db_session():
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()
