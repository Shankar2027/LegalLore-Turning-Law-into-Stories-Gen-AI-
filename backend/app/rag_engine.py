"""FAISS + FastEmbed knowledge base for legal terms.

- Exact lookup    -> authoritative definitions from the dataset (a dict, no embedding error possible).
- Semantic search -> FAISS finds related concepts the story may reference lightly.

The index is saved to disk and automatically rebuilt when the dataset or embedding model changes.
"""
import hashlib
import json
import logging
import io
import PyPDF2
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from .utils import parse_glossary

log = logging.getLogger("legal_lore.rag")


class LegalKnowledgeBase:
    def __init__(self, data_file: Path, index_dir: Path,
                 embed_model: str = "BAAI/bge-small-en-v1.5",
                 embeddings: Embeddings | None = None):
        self.data_file = Path(data_file)
        self.index_dir = Path(index_dir)
        self.embed_model = embed_model

        self.glossary: dict[str, str] = parse_glossary(self.data_file)
        if not self.glossary:
            raise RuntimeError(f"No terms parsed from {self.data_file}")
        self._lookup = {t.lower(): (t, d) for t, d in self.glossary.items()}

        if embeddings is None:  # lazy import keeps tests/other code free of fastembed
            from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
            embeddings = FastEmbedEmbeddings(model_name=embed_model)
        self.embeddings = embeddings
        self.store: FAISS | None = None

    # ----- ingestion -----
    def _fingerprint(self) -> str:
        h = hashlib.sha256(self.data_file.read_bytes())
        h.update(self.embed_model.encode())
        return h.hexdigest()

    def ingest(self, force: bool = False) -> int:
        """Load the saved index if it is current, otherwise (re)build it."""
        meta_path = self.index_dir / "meta.json"
        fp = self._fingerprint()

        if not force and (self.index_dir / "index.faiss").exists() and meta_path.exists():
            if json.loads(meta_path.read_text()).get("fingerprint") == fp:
                self.store = FAISS.load_local(
                    str(self.index_dir), self.embeddings,
                    allow_dangerous_deserialization=True,  # index is created locally by this app
                )
                log.info("Loaded FAISS index (%d terms).", len(self.glossary))
                return len(self.glossary)

        docs = [Document(page_content=f"{t}: {d}", metadata={"term": t, "definition": d})
                for t, d in self.glossary.items()]
        self.store = FAISS.from_documents(docs, self.embeddings)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.store.save_local(str(self.index_dir))
        meta_path.write_text(json.dumps({"fingerprint": fp, "terms": len(docs)}))
        log.info("Built FAISS index with %d terms.", len(docs))
        return len(docs)

    # ----- queries -----
    def count(self) -> int:
        return len(self.glossary)

    def list_terms(self) -> list[str]:
        return sorted(self.glossary)

    def get_definitions(self, terms: list[str]) -> dict[str, str]:
        """Exact, case-insensitive lookup. Raises KeyError(list_of_unknown_terms)."""
        unknown = [t for t in terms if t.lower() not in self._lookup]
        if unknown:
            raise KeyError(unknown)
        return dict(self._lookup[t.lower()] for t in terms)

    def related_concepts(self, terms: list[str], definitions: dict[str, str], k: int = 3) -> dict[str, str]:
        """Nearest semantic neighbours of the chosen terms, excluding the terms themselves."""
        if self.store is None:
            return {}
        chosen = {t.lower() for t in terms}
        related: dict[str, str] = {}
        for term, definition in definitions.items():
            hits = self.store.similarity_search(f"{term}: {definition}", k=len(terms) + k)
            for doc in hits:
                name = doc.metadata["term"]
                if name.lower() not in chosen and len(related) < k:
                    related.setdefault(name, doc.metadata["definition"])
        return related

    # ----- pdf processing -----
    def parse_uploaded_pdfs(self, files: list[bytes]) -> str:
        """Extracts and combines text from multiple uploaded PDF documents."""
        combined_text = ""
        for idx, file_bytes in enumerate(files):
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                combined_text += f"\n--- Document {idx + 1} ---\n"
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        combined_text += text + "\n"
            except Exception as e:
                raise ValueError(f"Could not read Document {idx + 1}: {e}")
                
        return combined_text.strip()