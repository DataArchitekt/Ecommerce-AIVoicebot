from typing import List, Dict
from langchain_community.vectorstores import Chroma
from backend.core.llm_client import get_embeddings
from langchain_core.runnables import RunnableLambda

# -------------------------------------------------------------------
# Embeddings
# -------------------------------------------------------------------

embeddings = get_embeddings()

# -------------------------------------------------------------------
# Vector store initialization
# -------------------------------------------------------------------

def get_vectorstore():
    return Chroma(
        collection_name="ecommerce_docs",
        persist_directory="backend/data/chroma",
        embedding_function=get_embeddings(), 
    )

# -------------------------------------------------------------------
# Backward compatibility
# -------------------------------------------------------------------

def init_vectorstore():
    return get_vectorstore()

def get_retriever():
    return get_vectorstore().as_retriever(search_kwargs={"k": 4})


def handle_rag(query: str, session_id: str,lc_config=None):
    vectorstore = get_vectorstore()

    # -------------------------------
    # Extract simple constraints
    # -------------------------------
    q = query.lower()
    constraints = {}

    if "red" in q:
        constraints["color"] = "red"
    if "blue" in q:
        constraints["color"] = "blue"

    if "size m" in q or " m " in q:
        constraints["size"] = "M"
    if "size l" in q or " l " in q:
        constraints["size"] = "L"

    try:
        results = vectorstore._collection.query(
            query_texts=[query],
            n_results=5,  
            where={"type": {"$in": ["product"]}},
        )
    except Exception as e:
        return {
            "reply": "I'm having trouble accessing product information right now.",
            "sources": [],
            "result": {
                "error": str(e),
                "needs_human": False
            }
        }

    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]

    if not documents:
        return {
            "reply": "I could not find relevant information.",
            "sources": [],
            "result": {"needs_human": False}
        }

    # -------------------------------
    # Attribute-aware selection
    # -------------------------------
    selected_doc = None
    selected_meta = None

    for doc, meta in zip(documents, metadatas):
        content = doc.lower()

        if not constraints:
            selected_doc = doc
            selected_meta = meta
            break

        match = True
        for k, v in constraints.items():
            if v.lower() not in content:
                match = False
                break

        if match:
            selected_doc = doc
            selected_meta = meta
            break


    # -------------------------------
    # Fallback to top semantic hit
    # -------------------------------
    if not selected_doc:
        selected_doc = documents[0]
        selected_meta = metadatas[0]

# -------------------------------------------------------------------
# LangSmith trace hook (NO extra LLM call)
# -------------------------------------------------------------------

    def trace_only_runnable(inputs):
        # We only echo the selected content to create a trace
        return inputs["context"]

    trace_runnable = RunnableLambda(trace_only_runnable)

    if lc_config:
        print(" About to invoke LangChain runnable (RAG trace)")
        _ = trace_runnable.invoke(
            {
                "query": query,
                "context": selected_doc,
                "metadata": selected_meta,
            },
            config=lc_config,
        )
        print(" LangChain invoke completed (RAG trace)")
        
    return {
    "reply": selected_doc,
    "sources": [
        {
            "page_content": selected_doc,
            "metadata": selected_meta,
        }
    ],
    "result": {"needs_human": False}
}