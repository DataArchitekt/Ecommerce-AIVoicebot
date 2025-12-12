# scripts/index_from_postgres.py
"""
Pull rows from Postgres (products and orders) and index into Weaviate (or local FAISS fallback)
Uses SQLAlchemy connection string from env: DATABASE_URL
Uses backend.app.rag.index_documents_to_weaviate
"""
# >>> top of script file (add before other imports)
import os, sys
# ensure repo root (parent of 'backend') is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# then your existing imports
# try both import paths for resilience:
try:
    from app.rag import index_documents_to_weaviate
except Exception:
    from backend.app.rag import index_documents_to_weaviate

import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# make sure env is loaded (if you use .env)
BASE = os.path.dirname(os.path.dirname(__file__))
DOTENV = os.path.join(BASE, ".env")
if os.path.exists(DOTENV):
    load_dotenv(DOTENV)

DATABASE_URL = os.getenv("DB_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in environment")

# import indexer function from your app (adjust import path if different)
try:
    # If your project uses package name 'backend' or 'app', adjust accordingly.
    from app.rag import index_documents_to_weaviate
except Exception:
    from backend.app.rag import index_documents_to_weaviate  # fallback

def fetch_table_as_docs(engine, table_name, id_col="id"):
    docs = []
    with engine.connect() as conn:
        # fetch useful columns generically; adjust SELECT if your tables have specific columns.
        res = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 1000"))
        columns = res.keys()
        for row in res.fetchall():
            d = dict(zip(columns, row))
            # create readable text from row
            text_parts = []
            for k, v in d.items():
                text_parts.append(f"{k}: {v}")
            text_blob = " | ".join(text_parts)
            meta = {"table": table_name, id_col: d.get(id_col)}
            docs.append({"id": f"{table_name}-{d.get(id_col)}", "text": text_blob, "meta": meta})
    return docs

def main():
    engine = create_engine(DATABASE_URL)
    # fetch products
    print("Fetching products...")
    prod_docs = fetch_table_as_docs(engine, "products", id_col="id")
    print(f"Found {len(prod_docs)} products")
    # fetch orders
    print("Fetching orders...")
    order_docs = fetch_table_as_docs(engine, "orders", id_col="id")
    print(f"Found {len(order_docs)} orders")

    all_docs = prod_docs + order_docs
    if not all_docs:
        print("No docs to index. Exiting.")
        return
    # index into Weaviate or FAISS via your indexer helper
    vs = index_documents_to_weaviate(all_docs)
    print("Indexing done. Vectorstore:", type(vs))

if __name__ == "__main__":
    main()