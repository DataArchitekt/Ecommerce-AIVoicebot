# scripts/index_sample.py

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

from backend.app.rag import index_sample_docs, index_documents
if __name__ == "__main__":
    index_sample_docs()
    print("Sample docs indexed to FAISS local store.")