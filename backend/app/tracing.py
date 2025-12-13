# tracing.py
from langsmith import LangSmithTracer, Client  # adjust imports to langsmith SDK
from contextlib import contextmanager
import os

LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY", "")

@contextmanager
def langsmith_trace(trace_name="ecommerce_voicebot"):
    tracer = LangSmithTracer(api_key=LANGSMITH_API_KEY, run_name=trace_name)
    try:
        tracer.start_run()
        yield tracer
    finally:
        tracer.end_run()
