from typing import List, Dict
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# -------------------------------------------------------------------
# Embeddings (MUST match indexing)
# -------------------------------------------------------------------

def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

# -------------------------------------------------------------------
# Vector store (single source of truth)
# -------------------------------------------------------------------

def get_vectorstore():
    return Chroma(
        collection_name="ecommerce_docs",
        persist_directory="backend/data/chroma",
        embedding_function=get_embeddings(),  # 🔥 CRITICAL
    )

# -------------------------------------------------------------------
# Backward compatibility (do NOT remove)
# -------------------------------------------------------------------

def init_vectorstore():
    return get_vectorstore()

def get_retriever():
    return get_vectorstore().as_retriever(search_kwargs={"k": 4})

# -------------------------------------------------------------------
# FINAL SAFE RAG (no LangChain wrapper bugs)
# -------------------------------------------------------------------

def handle_rag(query: str, session_id: str):
    vectorstore = get_vectorstore()

    try:
        results = vectorstore._collection.query(
            query_texts=[query],
            n_results=4,
            where={"type": {"$in": ["product", "video_transcript"]}},
        )
    except Exception as e:
        # Hard failure from vector DB
        return {
            "reply": "I'm having trouble accessing product information right now.",
            "sources": [],
            "result": {
                "error": str(e),
                "needs_human": False
            }
        }

    # 🔐 SAFETY GUARD 1: results can be None
    if not results:
        return {
            "reply": "I could not find relevant information.",
            "sources": [],
            "result": {"needs_human": False}
        }

    # 🔐 SAFETY GUARD 2: values inside results can be None
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]

    if not documents:
        return {
            "reply": "I could not find relevant information.",
            "sources": [],
            "result": {"needs_human": False}
        }

    # ✅ Take ONLY the top document
    top_doc = documents[0]
    top_meta = (metadatas[0] if metadatas else {})

    return {
        "reply": top_doc,
        "sources": [
            {
                "page_content": top_doc,
                "metadata": top_meta,
            }
        ],
        "result": {"needs_human": False}
    }

