from backend.rag.rag import get_vectorstore
from langchain.schema import Document


def index_documents_to_weaviate(docs):
    vectorstore = get_vectorstore()

    documents = [
        Document(
            page_content=d["text"],
            metadata={
                "source": d.get("source", "postgres"),
                "type": d.get("type", "product"),
                "product_id": str(d.get("product_id")),
                **d.get("meta", {}),
            },
        )
        for d in docs
    ]

    vectorstore.add_documents(documents)

    print(f" Indexed {len(documents)} docs")
