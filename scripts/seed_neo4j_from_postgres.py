print("🚀 Neo4j seed script started")

from sqlalchemy import select
from backend.app.database import engine
from backend.app.graph import get_driver

# IMPORTANT:
# import the SAME table or ORM object used in seed_catalog.py
# ↓↓↓ CHECK THIS IMPORT CAREFULLY ↓↓↓
from backend.app.seed_catalog import products  # Table object


def seed_neo4j_from_catalog():
    print("🏁 Entering seed_neo4j_from_catalog")

    # 1️⃣ Fetch products from Postgres
    with engine.connect() as conn:
        result = conn.execute(select(products))
        rows = result.fetchall()

    print(f"DEBUG: products fetched = {len(rows)}")

    if not rows:
        print("⚠️ No products found in Postgres — stopping")
        return

    # 2️⃣ Init Neo4j
    driver = get_driver()

    cypher = """
    MERGE (p:Product {id: $id})
    SET
        p.sku = $sku,
        p.name = $name,
        p.description = $description,
        p.price = $price,
        p.currency = $currency
    """



    # 3️⃣ Write to Neo4j
    with driver.session() as session:
        for r in rows:
            session.run(
                cypher,
                id=str(r.id),
                sku=r.sku,
                name=r.name,
                description=r.description,
                price=float(r.price),
                currency=r.currency,
            )

    print(f"✅ Seeded {len(rows)} products into Neo4j")


if __name__ == "__main__":
    seed_neo4j_from_catalog()