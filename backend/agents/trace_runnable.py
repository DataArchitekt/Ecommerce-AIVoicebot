from langchain_core.runnables import RunnableLambda

def make_trace_runnable(helicone_llm_call):
    """
    Wraps a Helicone-backed LLM call so LangSmith can trace execution.
    """

    def _wrapped(inputs: dict):
        # LangSmith will record inputs/outputs of this runnable
        return helicone_llm_call(
            messages=inputs["messages"],
            session_id=inputs.get("session_id"),
        )

    return RunnableLambda(_wrapped).with_config(
        {
            "run_name": "Helicone_OpenAI_Call",
            "tags": ["llm", "helicone", "openai"],
        }
    )
