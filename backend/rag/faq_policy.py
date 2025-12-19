from langchain_community.vectorstores import Chroma
from backend.core.llm_client import get_embeddings

def get_vectorstore():
    return Chroma(
        collection_name="ecommerce_docs",
        persist_directory="backend/data/chroma",
        embedding_function=get_embeddings(),
    )

def handle_faq_query(query: str):
    vectorstore = get_vectorstore()
    results = vectorstore._collection.query(
        query_texts=[query],
        n_results=1,
        where={"type": "faq"},
    )

    docs = (results.get("documents") or [[]])[0]
    if not docs:
        return "I couldn't find the answer to that question."

    return docs[0]

def handle_policy_query(query: str):
    vectorstore = get_vectorstore()
    results = vectorstore._collection.query(
        query_texts=[query],
        n_results=1,
        where={"type": "policy"},
    )

    docs = (results.get("documents") or [[]])[0]
    if not docs:
        return "I couldn't find the policy information."

    return docs[0]
