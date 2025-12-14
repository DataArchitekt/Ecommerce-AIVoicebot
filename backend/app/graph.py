import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
        print("✅ Neo4j driver initialized")
    return _driver


def get_similar_products(product_id: str):
    print("🔥 Running UPDATED get_similar_products (currency-based)")

    query = """
    MATCH (p:Product {id: $id})
    MATCH (other:Product)
    WHERE other.id <> $id
        AND other.currency = p.currency
    RETURN other.id AS id, other.name AS name
    LIMIT 3
    """

    driver = get_driver()
    with driver.session() as session:
        return session.run(query, id=product_id).data()
