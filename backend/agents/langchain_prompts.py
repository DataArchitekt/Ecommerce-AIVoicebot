
import os
from langchain.prompts import PromptTemplate
from backend.core.llm_client import openai_chat, hf_chat
from backend.core.config import EMBEDDING_BACKEND
from langchain_core.runnables import RunnableLambda


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

    def run(transcript: str, chat_history=None, lc_config=None):
        # Retrieve documents
        docs = retriever.get_relevant_documents(transcript)

        context = "\n".join(d.page_content for d in docs)

        # Build final prompt
        final_prompt = f"""
        {system_prompt}

        Context:
        {context}

        User:
        {transcript}
        """

        # FINAL LLM CALL
        def helicone_llm_call(inputs: dict):
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": inputs["prompt"]},
            ]

            if EMBEDDING_BACKEND == "openai":
                completion = openai_chat(messages)
                return completion.choices[0].message.content

            elif EMBEDDING_BACKEND == "hf":
                return hf_chat(inputs["prompt"])

            return "Dummy response"

        trace_runnable = RunnableLambda(lambda x: x["prompt"])

        reply = trace_runnable.invoke(
            {"prompt": final_prompt},
            config=lc_config
        )
        print(" LangChain invoke completed")
        
        return {
            "answer": reply,
            "source_documents": docs,
        }

    return run