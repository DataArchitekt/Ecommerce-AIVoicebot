# backend/app/seed_catalog.py
import os
from sqlalchemy import (create_engine, MetaData, Table, Column, Integer, String, Float, DateTime, ForeignKey, select, insert)
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

DB_URL = os.getenv("DB_URL", "sqlite:///./test.db")
engine = create_engine(DB_URL, echo=False, future=True)
metadata = MetaData()

products = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("sku", String(64), nullable=False, unique=True),
    Column("name", String(255), nullable=False),
    Column("description", String(1024)),
    Column("price", Float, nullable=False),
    Column("currency", String(8), default="INR")
)

orders = Table(
    "orders",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("order_number", String(64), nullable=False, unique=True),
    Column("product_id", Integer, ForeignKey("products.id")),
    Column("qty", Integer, default=1),
    Column("total", Float, nullable=False),
    Column("created_at", DateTime, default=datetime.utcnow)
)

def seed():
    metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()

    # seed products if none exist
    existing = s.execute(select(products.c.id)).first()
    if existing:
        print("Products already exist; skipping seeding.")
        return

    product_rows = []
    for i in range(1, 21):
        sku = f"SKU-{1000 + i}"
        name = f"Product {i}"
        desc = f"Demo description for {name}"
        price = round(random.uniform(199, 4999), 2)
        product_rows.append({"sku": sku, "name": name, "description": desc, "price": price, "currency": "INR"})

    result = s.execute(insert(products), product_rows)
    s.commit()

    # query inserted product IDs
    prods = list(s.execute(select(products.c.id, products.c.price)).all())

    # seed 20 orders
    order_rows = []
    base = datetime.utcnow()
    for i in range(1, 21):
        pid, price = random.choice(prods)
        qty = random.randint(1, 3)
        total = float(qty) * float(price)
        order_rows.append({
            "order_number": f"ORD-{10000 + i}",
            "product_id": int(pid),
            "qty": qty,
            "total": total,
            "created_at": base - timedelta(days=random.randint(0, 30))
        })

    s.execute(insert(orders), order_rows)
    s.commit()
    print("Seeded 20 products and 20 orders.")

if __name__ == "__main__":
    seed()