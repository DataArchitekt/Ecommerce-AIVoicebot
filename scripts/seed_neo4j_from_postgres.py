import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import select

from backend.db.db import engine
from backend.rag.seed_catalog import products
from backend.memory.graph import get_driver

# -----------------------
# Load env explicitly
# -----------------------
env_path = Path(__file__).resolve().parents[2] / "backend" / ".env"
load_dotenv(dotenv_path=env_path)

print("🧪 NEO4J_URI =", os.getenv("NEO4J_URI"))

# -----------------------
# Helpers
# -----------------------
def price_band(price: float) -> str:
    if price < 1000:
        return "LOW"
    elif price < 2000:
        return "MID"
    else:
        return "HIGH"

# -----------------------
# Main seed function
# -----------------------
def seed_products_graph():
    print(" ENTERED seed_products_graph")

    driver = get_driver()

    with engine.connect() as conn:
        rows = conn.execute(select(products)).fetchall()

    print(f" Products fetched from Postgres: {len(rows)}")

    if not rows:
        raise RuntimeError("No products found in Postgres — aborting")

    with driver.session() as session:
        for row in rows:
            session.run(
                """
                MERGE (prod:Product {id: $id})
                SET prod.sku = $sku,
                    prod.name = $name,
                    prod.price = $price,
                    prod.currency = $currency

                MERGE (c:Category {name: $category})
                MERGE (m:Material {name: $material})
                MERGE (clr:Color {name: $color})
                MERGE (pb:PriceBand {name: $price_band})

                MERGE (prod)-[:IN_CATEGORY]->(c)
                MERGE (prod)-[:HAS_MATERIAL]->(m)
                MERGE (prod)-[:HAS_COLOR]->(clr)
                MERGE (prod)-[:IN_PRICE_BAND]->(pb)
                """,
                id=row.id,
                sku=row.sku,
                name=row.name,
                price=row.price,
                currency=row.currency,
                category=row.category or "unknown",
                material=row.material or "unknown",
                color=row.color or "unknown",
                price_band=price_band(row.price),
            )

    print(" Neo4j product graph seeded successfully")

# -----------------------
# Entry point
# -----------------------
if __name__ == "__main__":
    seed_products_graph()
