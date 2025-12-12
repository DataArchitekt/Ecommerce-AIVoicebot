# backend/app/rag.py
"""
RAG helper: embeddings, retriever, indexer.
Hybrid: use OpenAI embeddings when OPENAI_API_KEY present, otherwise use local HF embeddings.
Primary vector DB: Weaviate (cloud) if WEAVIATE_URL+KEY set, otherwise FAISS local fallback.
"""

import os
from typing import List, Dict
from pathlib import Path

# modern LangChain community imports
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Weaviate as LangWeaviate
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document

import weaviate as weav_client

# env (support DB_PATH names in backend/.env)
BASE = Path(__file__).resolve().parents[1]
ENV_PATH = BASE / ".env"
if ENV_PATH.exists():
    # lightweight loading; does not overwrite process env if already set
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # optional
WEAVIATE_URL = os.getenv("WEAVIATE_URL")      # optional
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", str(BASE / "../data/faiss_index"))

USE_OPENAI = bool(OPENAI_API_KEY)

# --- use HF embeddings always for indexing to avoid OpenAI quota issues ---
from langchain_community.embeddings import HuggingFaceEmbeddings

def get_embedding():
    """
    Always return a local HF embeddings instance for indexing and retrieval.
    If OPENAI_API_KEY is present and you want to use OpenAI, change this intentionally.
    """
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")





def _weaviate_client():
    """Return a Weaviate client if credentials present and reachable, else None."""
    if not WEAVIATE_URL or not WEAVIATE_API_KEY:
        return None
    try:
        auth = weav_client.auth.AuthApiKey(api_key=WEAVIATE_API_KEY)
        client = weav_client.Client(url=WEAVIATE_URL, auth_client_secret=auth)
        # quick ping
        client.schema.get()
        return client
    except Exception:
        return None

def ensure_weaviate_class(client, class_name: str = "ProductDoc"):
    schema = {
        "class": class_name,
        "properties": [
            {"name": "text", "dataType": ["text"]},
            {"name": "meta", "dataType": ["text"]}
        ]
    }
    try:
        existing = client.schema.get()
        classes = [c["class"] for c in existing.get("classes", [])]
        if class_name not in classes:
            client.schema.create_class(schema)
    except Exception:
        # ignore - may already exist or weaviate cloud has restrictions
        pass

def get_retriever():
    """
    Return retriever:
      1. Weaviate (if configured)
      2. Chroma local fallback (persisted to CHROMA_PERSIST_DIR, default: ./vector_db)
    """
    emb = get_embedding()

    # --- OPTION 1: Weaviate Cloud ---
    client = _weaviate_client()
    if client:
        ensure_weaviate_class(client, "ProductDoc")
        vs = LangWeaviate(client, "ProductDoc", embedding=emb)
        return vs.as_retriever(search_kwargs={"k": 4})

    # --- OPTION 2: Local Chroma fallback (persisted) ---
    from langchain_community.vectorstores import Chroma
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "vector_db")
    # create dir if missing (Chroma will populate when indexing)
    os.makedirs(persist_dir, exist_ok=True)

    # If Chroma already has persisted data, load it. Otherwise, create an empty but persistent store.
    try:
        vs = Chroma(persist_directory=persist_dir, embedding_function=emb)  # load existing
        # some langchain versions use Chroma.from_persisted; above works with recent wrappers
    except Exception:
        # fallback creation
        vs = Chroma.from_texts([""], embedding=emb, persist_directory=persist_dir)

    return vs.as_retriever(search_kwargs={"k": 4})


def index_documents_to_weaviate(docs: List[Dict]):
    """
    Index docs. Prefer Weaviate cloud if configured. Otherwise use Chroma local fallback.
    """
    emb = get_embedding()
    client = _weaviate_client()
    documents = [Document(page_content=d["text"], metadata=d.get("meta", {})) for d in docs]

    # 1) Try Weaviate if configured
    if client:
        ensure_weaviate_class(client, "ProductDoc")
        vs = LangWeaviate(client, "ProductDoc", embedding=emb)
        vs.add_documents(documents)
        return vs

    # 2) Chroma local fallback (works on macOS)
    print(">>> Using Chroma fallback for indexing")
    from langchain_community.vectorstores import Chroma
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "vector_db")
    texts = [d["text"] for d in docs]
    metadatas = [d.get("meta", {}) for d in docs]
    vs = Chroma.from_texts(texts, embedding=emb, metadatas=metadatas, persist_directory=persist_dir)
    return vs

def index_sample_docs():
    sample = [
        {"id":"p1","text":"Order 12345 is processed and handed to courier. Typical ETA 2 days.", "meta":{"type":"order_note"}},
        {"id":"p2","text":"Red cotton t-shirt, SKU 123, shipping 3-5 days", "meta":{"sku":"123","type":"product"}},
    ]
    return index_documents_to_weaviate(sample)
