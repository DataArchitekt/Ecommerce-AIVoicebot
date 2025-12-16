# backend/app/db.py
import os
from sqlalchemy import JSON, create_engine, Column, String, Integer, Text
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

class MCPCallLog(Base):
    __tablename__ = "mcp_calls"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    task_name = Column(String, nullable=False)   # 👈 REQUIRED by DB
    tool_name = Column(String, index=True)
    operation = Column(String)
    args = Column(JSON)
    result = Column(JSON)
    status = Column(String)
    duration_ms = Column(Integer)
    run_id = Column(String, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)
    


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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

def record_mcp_call(db, session_id, name, tool, args, result, status, duration_ms, run_id=None):
    # ✅ Allow db to be optional (WS / demo mode)
    print("🔥 MCP CALLED:", name, tool, status)
    if db is None:
        return
    try:
        entry = MCPCallLog(
            session_id=session_id,
            task_name=name,          
            tool_name=name,         
            operation=tool,         
            args=args,
            result=result,
            status=status,
            duration_ms=duration_ms,
            run_id=run_id
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
        raise

