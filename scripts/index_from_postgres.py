"""
Indexes knowledge entities into the vector store.

Included:
- products
- faqs
- policies

Excluded:
- orders
- sessions
- conversations
- mcp_calls
"""

from sqlalchemy import text
from backend.db.db_utils import SessionLocal
from backend.rag.rag import get_vectorstore   

# --------------------------------------------------
# DOCUMENT BUILDERS
# --------------------------------------------------

PRODUCT_METADATA_FIELDS = ["color", "size", "material", "category"]

def build_product_document(row):
    parts = [row["name"], row.get("description", "")]

    for field in PRODUCT_METADATA_FIELDS:
        if row.get(field):
            parts.append(f"{field.capitalize()}: {row[field]}")

    parts.append(f"Price: {row['price']} INR")
    return ". ".join(p for p in parts if p)


def build_faq_document(row):
    return f"Question: {row['question']}. Answer: {row['answer']}"


def build_policy_document(row):
    return f"{row['title']}. {row['content']}"

# --------------------------------------------------
# INDEXING FUNCTIONS
# --------------------------------------------------

def index_products(session, vectorstore):
    rows = session.execute(
        text("""
            SELECT sku, name, description, price, color, size, material, category
            FROM products
        """)
    ).mappings().all()

    docs = []
    for row in rows:
        metadata = {
            "type": "product",
            "sku": row["sku"],
            "price": row["price"]
        }

        for field in PRODUCT_METADATA_FIELDS:
            if row.get(field):
                metadata[field] = row[field].lower()

        docs.append({
            "page_content": build_product_document(row),
            "metadata": metadata
        })

    vectorstore.add_texts(
        texts=[d["page_content"] for d in docs],
        metadatas=[d["metadata"] for d in docs]
    )

    print(f" Indexed {len(docs)} products")


def index_faqs(session, vectorstore):
    rows = session.execute(
        text("SELECT faq_id, question, answer FROM faqs")
    ).mappings().all()

    vectorstore.add_texts(
        texts=[build_faq_document(r) for r in rows],
        metadatas=[{"type": "faq", "faq_id": r["faq_id"]} for r in rows]
    )

    print(f" Indexed {len(rows)} FAQs")


def index_policies(session, vectorstore):
    rows = session.execute(
        text("SELECT policy_id, title, content FROM policies")
    ).mappings().all()

    vectorstore.add_texts(
        texts=[build_policy_document(r) for r in rows],
        metadatas=[{"type": "policy", "policy_id": r["policy_id"]} for r in rows]
    )

    print(f" Indexed {len(rows)} policies")

# --------------------------------------------------
# ENTRYPOINT
# --------------------------------------------------

def main():
    print(" Indexing knowledge entities into vector store")

    session = SessionLocal()
    vectorstore = get_vectorstore()

    try:
        index_products(session, vectorstore)
        index_faqs(session, vectorstore)
        index_policies(session, vectorstore)

        vectorstore.persist()
        print(" Vector store persisted")

    finally:
        session.close()

    print(" Indexing complete")


if __name__ == "__main__":
    main()
