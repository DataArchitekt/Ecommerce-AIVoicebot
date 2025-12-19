
from langchain.callbacks import LangChainTracer
from langchain_core.runnables import RunnableConfig

def make_langchain_tracer(project_name: str = "default"):
    # LangChainTracer for LangChain -> LangSmith
    tracer = LangChainTracer(project_name=project_name)
    return tracer

def runnable_config_for_tracer(tracer, run_name: str = None):

    cfg = RunnableConfig(callbacks=[tracer])
    if run_name is not None:

        try:
            cfg.run_name = run_name
        except Exception:
            pass
    return cfg

