"""Rebuild the FAISS index:  python -m scripts.ingest   (run from backend/)"""
from app.config import get_settings
from app.rag_engine import LegalKnowledgeBase

s = get_settings()
kb = LegalKnowledgeBase(s.data_file, s.faiss_dir, s.embed_model)
print(f"Indexed {kb.ingest(force=True)} terms into {s.faiss_dir}")
