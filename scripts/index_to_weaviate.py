# scripts/index_to_weaviate.py

# >>> top of script file (add before other imports)
import os, sys
# ensure repo root (parent of 'backend') is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# then your existing imports
# try both import paths for resilience:
try:
    from app.rag import index_documents_to_weaviate
except Exception:
    from backend.app.rag import index_documents_to_weaviate

from backend.app.rag import index_documents_to_weaviate

SAMPLES = [
    {"id":"p1","text":"Order 12345 is processed and handed to courier. Typical ETA 2 days.", "meta":{"type":"order_note"}},
    {"id":"p2","text":"Blue jeans SKU 456. Ships in 3-5 days.", "meta":{"type":"product"}}
]

if __name__ == "__main__":
    vs = index_documents_to_weaviate(SAMPLES)
    print("Indexed to weaviate (or local FAISS).")