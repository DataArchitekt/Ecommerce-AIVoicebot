from sqlalchemy.orm import Session
from backend.app.db import SessionLocal
from backend.app.rag import get_vectorstore
from langchain.schema import Document
from backend.app.seed_catalog import products as Product

def index_products():
    db: Session = SessionLocal()
    vectorstore = get_vectorstore()

    products = db.query(Product).all()

    docs = []
    for p in products:
        docs.append(
            Document(
                page_content=f"Product {p.id}: {p.name}. {p.description}",
                metadata={
                    "type": "product",          
                    "product_id": str(p.id),
                    "name": p.name,
                    "price": p.price,
                },
            )
        )

    vectorstore.add_documents(docs)

    print(f"✅ Indexed {len(docs)} products into vector store")


if __name__ == "__main__":
    index_products()
