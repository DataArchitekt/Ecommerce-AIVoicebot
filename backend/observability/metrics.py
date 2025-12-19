from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "agent_requests_total",
    "Total agent requests",
    ["endpoint"]
)

REQUEST_LATENCY = Histogram(
    "agent_request_latency_seconds",
    "Agent request latency",
    ["endpoint"]
)

LLM_CALL_COUNT = Counter(
    "llm_calls_total",
    "Total LLM calls",
    ["backend"]
)

STT_CALL_COUNT = Counter(
    "stt_calls_total",
    "Total STT calls"
)

PII_BLOCK_COUNT = Counter(
    "pii_blocked_requests_total",
    "Number of requests blocked due to PII"
)
