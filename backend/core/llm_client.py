import os
from pathlib import Path
from typing import Optional

from openai import OpenAI
from transformers import pipeline
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings

from backend.core.config import EMBEDDING_BACKEND
from backend.observability.metrics import LLM_CALL_COUNT

from dotenv import load_dotenv

# ------------------------------------------------------------------
# Env loading
# ------------------------------------------------------------------
env_path = Path(__file__).resolve().parents[2] / "backend" / ".env"
load_dotenv(dotenv_path=env_path)

# ------------------------------------------------------------------
# Helicone shared config
# ------------------------------------------------------------------
HELICONE_BASE_URL = os.getenv(
    "OPENAI_API_BASE",
    "https://ai-gateway.helicone.ai/v1"
)

HELICONE_HEADERS = {
    "Helicone-Auth": f"Bearer {os.getenv('HELICONE_API_KEY')}",
    "Helicone-User-Id": os.getenv("HELICONE_USER_ID", "capstone_user"),
    "Helicone-Property-Project": os.getenv("HELICONE_PROJECT", "Capstone"),
    "Helicone-Property-App": "ecommerce-voicebot",
}

# ------------------------------------------------------------------
# OPENAI CHAT (used by agent / executor)
# ------------------------------------------------------------------

def openai_chat(messages, session_id: Optional[str] = None):
    """
    OpenAI chat completion via Helicone.
    This is what powers Helicone + LLM_CALL_COUNT.
    """
    print("openai_chat() CALLED — Helicone enabled")

    # Metrics
    LLM_CALL_COUNT.labels(backend="openai").inc()

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=HELICONE_BASE_URL,
        default_headers={
            **HELICONE_HEADERS,
            "Helicone-Property-Session": session_id,
        },
    )

    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )

# ------------------------------------------------------------------
# HF FALLBACK (no Helicone, local only)
# ------------------------------------------------------------------

def hf_chat(prompt: str):
    """
    Local HF fallback (no Helicone, no metrics).
    """
    pipe = pipeline("text-generation", model="distilgpt2")
    return pipe(prompt, max_new_tokens=150)[0]["generated_text"]

# ------------------------------------------------------------------
# EMBEDDINGS FACTORY (USED BY rag.py)
# ------------------------------------------------------------------

def get_embeddings():
    """
    Embedding factory.
    IMPORTANT:
    - OpenAI embeddings MUST inject Helicone headers explicitly
    - LangChain does NOT inherit OpenAI client settings automatically
    """

    if EMBEDDING_BACKEND == "openai":
        print("[RAG] Using OpenAI embeddings via Helicone")

        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=HELICONE_BASE_URL,
            default_headers=HELICONE_HEADERS, 
        )

    print("[RAG] Using HuggingFace embeddings")
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

# ------------------------------------------------------------------
# OPTIONAL: LangChain Chat LLM
# ------------------------------------------------------------------

def get_langchain_llm():
    """
    ChatOpenAI wrapped with Helicone headers.
    Useful if you later migrate agent logic to LangChain chains.
    """
    LLM_CALL_COUNT.labels(backend="openai").inc()

    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=HELICONE_BASE_URL,
        default_headers=HELICONE_HEADERS,
    )
