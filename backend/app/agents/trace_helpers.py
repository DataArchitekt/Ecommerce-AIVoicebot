import os
from langchain.callbacks import LangChainTracer
from langchain_core.runnables import RunnableConfig

# backend/app/agents/trace_helpers.py
import os
from langchain.callbacks import LangChainTracer
from langchain_core.runnables import RunnableConfig

def make_langchain_tracer(project_name: str = "Ecommerce-Voicebot"):
    # LANGSMITH_API_KEY must be set in env (you put it in backend/.env)
    # LangChainTracer bridges LangChain -> LangSmith
    tracer = LangChainTracer(project_name=project_name)
    return tracer

def runnable_config_for_tracer(tracer, run_name: str = None):
    # RunnableConfig allows passing callbacks into chain.invoke() and groups runs
    cfg = RunnableConfig(callbacks=[tracer])
    if run_name is not None:
        # Some LangChain versions accept run_name/run_id metadata here — include if supported
        try:
            cfg.run_name = run_name
        except Exception:
            pass
    return cfg

