from langchain_core.runnables import RunnableLambda

def make_trace_runnable(helicone_llm_call):
    """
    Wraps an existing Helicone-backed LLM call so LangSmith can trace the execution.
    """

    def _wrapped(inputs: dict):

        return helicone_llm_call(inputs)

    return RunnableLambda(_wrapped)
