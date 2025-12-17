# backend/app/agents/langchain_prompts.py
import os
from backend.app.llm_client import openai_chat, hf_chat
from backend.app.config import EMBEDDING_BACKEND
from langchain.prompts import PromptTemplate


def build_rag_executor(retriever):
    """
    Returns a callable that performs:
    retrieval → prompt assembly → FINAL LLM CALL
    """
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

    def run(transcript: str, chat_history=None):
        # 1. Retrieve documents
        docs = retriever.get_relevant_documents(transcript)

        context = "\n".join(d.page_content for d in docs)

        # 2. Build final prompt
        final_prompt = f"""
        {system_prompt}

        Context:
        {context}

        User:
        {transcript}
        """

        # 3. FINAL LLM CALL (EXPLICIT & TRACEABLE)
        if EMBEDDING_BACKEND == "openai":
            completion = openai_chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_prompt},
            ])
            session_id=session_id
            reply = completion.choices[0].message.content

        elif EMBEDDING_BACKEND == "hf":
            reply = hf_chat(final_prompt)

        else:
            reply = "Dummy response"

        return {
            "answer": reply,
            "source_documents": docs,
        }

    return run

