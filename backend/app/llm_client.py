# backend/app/llm_client.py
import os
from typing import Optional
from openai import OpenAI
from transformers import pipeline
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

from backend.app.config import EMBEDDING_BACKEND
from backend.app.metrics import LLM_CALL_COUNT

# ---------- OPENAI CHAT (DEMO-STYLE, HELICONE SAFE) ----------

def openai_chat(messages,session_id: Optional[str] = None):
    """
    EXACT demo-style OpenAI call.
    Guaranteed to log requests in Helicone UI.
    """
    print("🚀 openai_chat() CALLED — Helicone headers injected")
    LLM_CALL_COUNT.labels(backend="openai").inc()
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE", "https://ai-gateway.helicone.ai/v1"),
    )
    print("🚨 OPENAI_API_BASE =", client.base_url)
    print("🚨 HELICONE_API_KEY =", os.getenv("HELICONE_API_KEY")[:15])
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
    
    # llm_client.py
def openai_chat(messages):
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE", "https://ai-gateway.helicone.ai/v1"),
    )

    print("🚨 OPENAI_API_BASE =", client.base_url)
    print("🚨 HELICONE_API_KEY =", os.getenv("HELICONE_API_KEY")[:15])

    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        extra_headers={
            "Helicone-Auth": f"Bearer {os.getenv('HELICONE_API_KEY')}",
        }
    )



# ---------- HF FALLBACK ----------

def hf_chat(prompt: str):
    """
    Local HF fallback (no Helicone, expected).
    """
    pipe = pipeline("text-generation", model="distilgpt2")
    return pipe(prompt, max_new_tokens=150)[0]["generated_text"]


# ---------- EMBEDDINGS FACTORY (USED BY rag.py) ----------

def get_embeddings():
    """
    Embedding factory.
    This is SAFE to keep and is used by rag.py.
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
