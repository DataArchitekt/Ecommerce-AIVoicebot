import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parents[2] / "backend" / ".env"
load_dotenv(dotenv_path=env_path)

_driver = None

def get_driver():
    
    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USER = os.getenv("NEO4J_USER")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")    
    global _driver
    if _driver is None:
        assert NEO4J_URI, "NEO4J_URI is not set"
        assert NEO4J_USER, "NEO4J_USER is not set"
        assert NEO4J_PASSWORD, "NEO4J_PASSWORD is not set"
        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
        print(" Neo4j driver initialized")
    return _driver


def get_similar_products(product_id: str):
    """
    Find similar products using graph relationships:
    - Same category
    - Same material
    - Same color (optional)
    - Same price band
    """

    print(" Running get_similar_products (graph-based similarity)")

    query = """
    MATCH (p:Product {id: $id})

    // Strong similarity: same category + material
    MATCH (p)-[:IN_CATEGORY]->(c)<-[:IN_CATEGORY]-(other)
    MATCH (p)-[:HAS_MATERIAL]->(m)<-[:HAS_MATERIAL]-(other)
    OPTIONAL MATCH (p)-[:HAS_COLOR]->(clr)<-[:HAS_COLOR]-(other)
    OPTIONAL MATCH (p)-[:IN_PRICE_BAND]->(pb)<-[:IN_PRICE_BAND]-(other)

    WHERE other.id <> $id

    WITH other,
         COUNT(DISTINCT c) AS category_score,
         COUNT(DISTINCT m) AS material_score,
         COUNT(DISTINCT clr) AS color_score,
         COUNT(DISTINCT pb) AS price_band_score

    WITH other,
         (category_score * 3 +
          material_score * 2 +
          color_score +
          price_band_score) AS similarity_score

    WHERE similarity_score > 0

    RETURN
        other.id   AS id,
        other.name AS name,
        similarity_score

    ORDER BY similarity_score DESC
    LIMIT 3
    """

    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, id=product_id)
        return result.data()

