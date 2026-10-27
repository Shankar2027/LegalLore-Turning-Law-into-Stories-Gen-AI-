"""RAG tests use a fake embedder, so no model download is needed."""
import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.rag_engine import LegalKnowledgeBase

DATA = "data/Legal_Problem_Statement.txt"


@pytest.fixture
def kb(tmp_path):
    k = LegalKnowledgeBase(DATA, tmp_path / "idx", embeddings=DeterministicFakeEmbedding(size=64))
    k.ingest()
    return k


def test_exact_lookup_case_insensitive(kb):
    d = kb.get_definitions(["verdict", "JURY", "Bail"])
    assert list(d) == ["Verdict", "Jury", "Bail"]


def test_unknown_term(kb):
    with pytest.raises(KeyError):
        kb.get_definitions(["Verdict", "Spaceship", "Bail"])


def test_related_excludes_chosen(kb):
    d = kb.get_definitions(["Verdict", "Jury", "Bail"])
    rel = kb.related_concepts(list(d), d, k=3)
    assert len(rel) == 3 and not set(rel) & set(d)


def test_index_persisted_and_reloaded(kb, tmp_path):
    k2 = LegalKnowledgeBase(DATA, tmp_path / "idx", embeddings=DeterministicFakeEmbedding(size=64))
    assert k2.ingest() == kb.count()          # loads from disk
    assert (tmp_path / "idx" / "index.faiss").exists()
