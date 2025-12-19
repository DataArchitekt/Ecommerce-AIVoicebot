
import os
from pathlib import Path
from typing import Optional
from openai import OpenAI
from transformers import pipeline
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

from backend.core.config import EMBEDDING_BACKEND
from backend.observability.metrics import LLM_CALL_COUNT

from dotenv import load_dotenv
env_path = Path(__file__).resolve().parents[2] / "backend" / ".env"
load_dotenv(dotenv_path=env_path)


# ---------- OPENAI CHAT  ----------

def openai_chat(messages,session_id: Optional[str] = None):
    """
    OpenAI call to log requests in Helicone UI.
    """
    print(" openai_chat() CALLED — Helicone headers injected")
    LLM_CALL_COUNT.labels(backend="openai").inc()
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE", "https://ai-gateway.helicone.ai/v1"),
    )
    print(" OPENAI_API_BASE =", client.base_url)
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        extra_headers={
            "Helicone-Auth": f"Bearer {os.getenv('HELICONE_API_KEY')}",
            "Helicone-User-Id": os.getenv("HELICONE_USER_ID", "capstone_user"),
            "Helicone-Property-Project": os.getenv("HELICONE_PROJECT", "Capstone"),
            "Helicone-Property-Session": session_id,
        },
    )

# ---------- HF FALLBACK ----------

def hf_chat(prompt: str):
    """
    Local HF fallback (no Helicone)
    """
    pipe = pipeline("text-generation", model="distilgpt2")
    return pipe(prompt, max_new_tokens=150)[0]["generated_text"]

# ---------- EMBEDDINGS FACTORY (USED BY rag.py) ----------

def get_embeddings():
    """
    Embedding factory.
    """

    if EMBEDDING_BACKEND == "openai":
        print("[RAG] Using OpenAI embeddings via Helicone")
        return OpenAIEmbeddings(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE", "https://ai-gateway.helicone.ai/v1"),
            default_headers={
                "Helicone-Auth": f"Bearer {os.getenv('HELICONE_API_KEY')}",
                "Helicone-Property-Project": os.getenv("HELICONE_PROJECT", "Capstone"),
            },
        )

    print("[RAG] Using HuggingFace embeddings")
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
