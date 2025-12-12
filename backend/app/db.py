# backend/app/db.py
import os
from sqlalchemy import create_engine, Column, String, Integer, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import json

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL or DB_URL is required for Postgres session storage")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    history = Column(Text, default="[]")  # JSON string of list[{"role":"user"/"assistant","text":...}]

def init_db():
    Base.metadata.create_all(bind=engine)

def get_history(session_id: str):
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.session_id == session_id).first()
        if not conv:
            return []
        return json.loads(conv.history)
    finally:
        db.close()

def save_history(session_id: str, history: list):
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.session_id == session_id).first()
        if not conv:
            conv = Conversation(session_id=session_id, history=json.dumps(history))
            db.add(conv)
        else:
            conv.history = json.dumps(history)
        db.commit()
    finally:
        db.close()
        
# -------------------------------------------------------------
# PRODUCT LOOKUP HELPERS (ADD THESE BELOW EXISTING FUNCTIONS)
# -------------------------------------------------------------
from sqlalchemy import text

def get_product_by_id(product_id: int):
    """
    Return product row as a dict or None if not found.
    Compatible across SQLAlchemy versions: converts Row/RowMapping to dict safely.
    """
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, sku, name, description, price, currency
                FROM products
                WHERE id = :id
            """),
            {"id": product_id}
        )
        row = result.fetchone()
        if not row:
            return None
        # row can be a RowMapping, Row, or a simple sequence — handle safely
        try:
            # preferred for SQLAlchemy 1.4+ Row mapping
            return dict(row._mapping)
        except Exception:
            try:
                # fallback if Row provides asdict-like API
                return dict(row)
            except Exception:
                # final fallback: build dict by index -> column names
                cols = result.keys()
                return {cols[i]: row[i] for i in range(len(cols))}

