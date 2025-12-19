"""
Index products, FAQs, and policies from Postgres into Chroma
(DEMO-SAFE VERSION)

IMPORTANT:
- Delete backend/data/chroma BEFORE running this script
"""

import os
from typing import List
from sqlalchemy import create_engine, text
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from backend.core.llm_client import get_embeddings

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

CHROMA_DIR = "backend/data/chroma"
COLLECTION_NAME = "ecommerce_docs"

DATABASE_URL = os.environ.get(
    "DB_URL",
    "postgresql://user:password@localhost:5432/ecommerce"
)

engine = create_engine(DATABASE_URL)
embeddings = get_embeddings()

# -------------------------------------------------------------------
# Text normalization (CRITICAL)
# -------------------------------------------------------------------

def clean_text(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "ethnic wear": "casual wear",
        "ethnic": "casual",
        "kurta": "shirt",
        "kurtas": "shirts",
    }

    out = text.lower()
    for k, v in replacements.items():
        out = out.replace(k, v)

    return out.strip()

# -------------------------------------------------------------------
# Fetchers
# -------------------------------------------------------------------

def fetch_products() -> List[dict]:
    query = text("""
        SELECT
            id,
            name,
            description,
            price,
            currency,
            sku,
            category
        FROM products
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()
    return rows

def fetch_faqs() -> List[dict]:
    query = text("""
        SELECT
            id,
            question,
            answer
        FROM faqs
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()
    return rows

def fetch_policies() -> List[dict]:
    query = text("""
        SELECT
            id,
            title,
            content
        FROM policies
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()
    return rows

# -------------------------------------------------------------------
# Document builders
# -------------------------------------------------------------------

def build_product_documents(rows: List[dict]) -> List[Document]:
    docs = []

    for row in rows:
        content_parts = [
            clean_text(row["name"]),
            clean_text(row.get("description", "")),
        ]

        page_content = ". ".join([p for p in content_parts if p])

        docs.append(
            Document(
                page_content=page_content,
                metadata={
                    "type": "product",
                    "product_id": row["id"],
                    "name": row["name"],
                    "price": row["price"],
                    "currency": row["currency"],
                    "sku": row["sku"],
                    "category": row.get("category"),
                },
            )
        )

    return docs

def build_faq_documents(rows: List[dict]) -> List[Document]:
    return [
        Document(
            page_content=f"{row['question']} {row['answer']}",
            metadata={"type": "faq", "faq_id": row["id"]},
        )
        for row in rows
    ]

def build_policy_documents(rows: List[dict]) -> List[Document]:
    return [
        Document(
            page_content=f"{row['title']} {row['content']}",
            metadata={"type": "policy", "policy_id": row["id"]},
        )
        for row in rows
    ]

# -------------------------------------------------------------------
# Main indexing logic
# -------------------------------------------------------------------

def main():
    print("Starting Chroma re-index from Postgres...")

    # Create vector store
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
    )

    all_docs: List[Document] = []

    products = fetch_products()
    faqs = fetch_faqs()
    policies = fetch_policies()

    product_docs = build_product_documents(products)
    faq_docs = build_faq_documents(faqs)
    policy_docs = build_policy_documents(policies)

    all_docs.extend(product_docs)
    all_docs.extend(faq_docs)
    all_docs.extend(policy_docs)

    print(f"Indexing {len(product_docs)} products")
    print(f"Indexing {len(faq_docs)} FAQs")
    print(f"Indexing {len(policy_docs)} policies")

    vectorstore.add_documents(all_docs)
    vectorstore.persist()

    print("Chroma indexing completed successfully.")

# -------------------------------------------------------------------

if __name__ == "__main__":
    main()
