
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    Integer, String, Float, Date, DateTime, select
)
from sqlalchemy.orm import sessionmaker

# --------------------------------------------------
# ENV & DB SETUP
# --------------------------------------------------
load_dotenv()

DB_URL = os.getenv("DB_URL")
if not DB_URL:
    raise RuntimeError("DB_URL must be set")

engine = create_engine(DB_URL, echo=False, future=True)
metadata = MetaData()

# ---------------------------------------------------
# PRODUCTS TABLE (MATCHES products.json)
# ---------------------------------------------------
products = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("sku", String(64), nullable=False, unique=True),
    Column("name", String(255), nullable=False),
    Column("description", String(1024)),
    Column("category", String(64)),
    Column("color", String(32)),
    Column("size", String(16)),
    Column("material", String(64)),
    Column("price", Float, nullable=False),
    Column("stock", Integer, default=0),
    Column("currency", String(8), default="INR"),
    Column("created_at", DateTime, default=datetime.utcnow),
)

faqs = Table(
    "faqs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("faq_id", String(64), unique=True, nullable=False),
    Column("question", String, nullable=False),
    Column("answer", String, nullable=False),
    Column("created_at", DateTime, default=datetime.utcnow),
)

policies = Table(
    "policies",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("policy_id", String(64), unique=True, nullable=False),
    Column("title", String, nullable=False),
    Column("content", String, nullable=False),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# ---------------------------------------------------
# SEED FUNCTION
# ---------------------------------------------------
def seed_products_from_json(json_path: str):
    metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Skip if products already exist
    existing = session.execute(select(products.c.id)).first()
    if existing:
        print(" Products already exist. Skipping seed.")
        return

    with open(json_path, "r") as f:
        product_data = json.load(f)

    rows = []
    for p in product_data:
        rows.append({
            "sku": p["sku"],
            "name": p["name"],
            "description": p.get("description"),
            "category": p.get("category"),
            "color": p.get("color"),
            "size": p.get("size"),
            "material": p.get("material"),
            "price": float(p["price"]),
            "stock": int(p.get("stock", 0)),
            "currency": "INR",
            "created_at": datetime.utcnow(),
        })

    session.execute(products.insert(), rows)
    session.commit()
    session.close()

    print(f" Seeded {len(rows)} products from {json_path}")

# ---------------------------------------------------
# CLI ENTRY
# ---------------------------------------------------
if __name__ == "__main__":
    seed_products_from_json("backend/demo/products.json")
    

# --------------------------------------------------
# ORDERS TABLE
# --------------------------------------------------
orders = Table(
    "orders",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("order_id", String(64), unique=True, nullable=False),
    Column("customer_id", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("eta", Date),
    Column("total_amount", Float),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# --------------------------------------------------
# SESSIONS TABLE
# --------------------------------------------------
sessions = Table(
    "sessions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", String(64), unique=True, nullable=False),
    Column("customer_id", String(64), nullable=True),
    Column("auth_level", String(32), nullable=False),
    Column("channel", String(32), nullable=False),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# --------------------------------------------------
# SEED FUNCTION
# --------------------------------------------------
def seed_from_json():
    metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # ---------- Seed Orders ----------
    orders_exist = session.execute(select(orders.c.id)).first()
    if not orders_exist:
        with open("backend/demo/orders.json", "r") as f:
            order_data = json.load(f)

        order_rows = []
        for o in order_data:
            order_rows.append({
                "order_id": o["order_id"],
                "customer_id": o["customer_id"],
                "status": o["status"],
                "eta": datetime.strptime(o["eta"], "%Y-%m-%d").date()
                      if o.get("eta") else None,
                "total_amount": o.get("total_amount"),
                "created_at": datetime.utcnow()
            })

        session.execute(orders.insert(), order_rows)
        print(f" Seeded {len(order_rows)} orders")
    else:
        print(" Orders already exist, skipping")

    # ---------- Seed Sessions ----------
    sessions_exist = session.execute(select(sessions.c.id)).first()
    if not sessions_exist:
        with open("backend/demo/session.json", "r") as f:
            session_data = json.load(f)

        session_rows = []
        for s in session_data:
            session_rows.append({
                "session_id": s["session_id"],
                "customer_id": s.get("customer_id"),
                "auth_level": s["auth_level"],
                "channel": s["channel"],
                "created_at": datetime.utcnow()
            })

        session.execute(sessions.insert(), session_rows)
        print(f" Seeded {len(session_rows)} sessions")
    else:
        print(" Sessions already exist, skipping")

    session.commit()
    session.close()

# --------------------------------------------------
# ENTRYPOINT
# --------------------------------------------------
if __name__ == "__main__":
    seed_from_json()
