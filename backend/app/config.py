# backend/app/config.py
import os

EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "hf").lower()
print("DEBUG EMBEDDING_BACKEND =", EMBEDDING_BACKEND)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Helicone
HELICONE_ENABLED = os.getenv("HELICONE_ENABLED", "false").lower() == "true"
HELICONE_API_KEY = os.getenv("HELICONE_API_KEY")

# Observability
PROMETHEUS_ENABLED = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"
