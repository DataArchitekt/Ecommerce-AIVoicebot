# agents/langchain_prompts.py
"""
Build the ConversationalRetrievalChain. Hybrid LLM:
 - Use OpenAI Chat if OPENAI_API_KEY present
 - Else try a local HF-based LLM via HuggingFace pipeline
 - Else use a deterministic DummyLLM for tests
"""

import os
from typing import Any
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate

# load env from backend/.env if present for local runs
from pathlib import Path
BASE = Path(__file__).resolve().parents[1]
ENV_PATH = BASE / ".env"
if ENV_PATH.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def _build_openai_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.0, api_key=OPENAI_API_KEY)

def _build_local_hf_llm():
    """
    Try to build a local HF LLM using transformers + langchain_community's HuggingFacePipeline wrapper.
    This requires transformers & torch to be installed and a model that fits your machine.
    """
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
        from langchain_community.llms import HuggingFacePipeline
        # choose a small model for CPU if needed; change to a larger model if you have GPU
        model_id = os.getenv("HF_LOCAL_MODEL", "google/flan-t5-small")  # mapping: use text2text models for small CPU
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(model_id)
        pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=128)
        return HuggingFacePipeline(pipeline=pipe)
    except Exception:
        return None

# Simple deterministic fallback LLM
from langchain.llms.base import LLM
class DummyLLM(LLM):
    def _call(self, prompt: str, stop=None) -> str:
        # If user asks about "order", simulate an action
        if "order" in prompt.lower():
            return ("I can check that for you. "
                    "[[ACTION]]{\"name\":\"get_order_status\",\"args\":{\"order_id\":\"12345\"}}[[/ACTION]] "
                    "Order 12345 is currently IN_TRANSIT (simulated).")
        return "[DUMMY] I can't access OpenAI; this is a local fallback reply."

    @property
    def _identifying_params(self):
        return {}

    @property
    def _llm_type(self):
        return "dummy"

def build_chain(retriever) -> ConversationalRetrievalChain:
    """
    Build and return a ConversationalRetrievalChain configured to use the retriever provided.
    """
    # choose LLM
    llm = None
    if OPENAI_API_KEY:
        try:
            llm = _build_openai_llm()
        except Exception:
            llm = None
    if llm is None:
        llm = _build_local_hf_llm()
    if llm is None:
        llm = DummyLLM()

    system_prompt = (
        "You are an ecommerce assistant. Use retrieved documents to answer user queries. "
        "If user asks about order status, emit an action JSON in the response using markers: "
        "`[[ACTION]]{\"name\":\"get_order_status\",\"args\":{\"order_id\":\"12345\"}}[[/ACTION]]`"
        "You may receive graph_context which contains explicit product relationships"
        "(e.g., similar products, categories, brands)."
        "Graph data is factual and MUST be preferred over assumptions."
        "Use it to:"
        "- Compare products"
        "- Recommend alternatives"
        "- Explain relationships"
    )

    prompt_template = PromptTemplate(
        input_variables=["question", "chat_history", "retrieved_docs"],
        template=system_prompt + "\n\nContext:\n{retrieved_docs}\n\nConversation History:\n{chat_history}\n\nUser question: {question}\n\nProvide a concise answer."
    )

    chain = ConversationalRetrievalChain.from_llm(llm=llm, retriever=retriever, return_source_documents=True)
    # Note: We don't directly set chain.prompt_template (varies by LangChain version). This is a general pattern.
    return chain
