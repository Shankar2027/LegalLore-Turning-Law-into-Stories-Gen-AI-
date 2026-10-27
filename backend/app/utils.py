"""Small, dependency-free helpers (unit-testable without an LLM)."""
import re
from pathlib import Path


def count_words(text: str) -> int:
    """Counts words safely across all languages by splitting on whitespace."""
    if not text:
        return 0
    # స్పేస్‌ల ఆధారంగా విడదీయడం ద్వారా తెలుగు, హిందీ తదితర భాషల పదాలు కూడా సరిగ్గా లెక్కించబడతాయి
    return len(text.split())


def term_present(term: str, text: str) -> bool:
    """Whole-phrase, case-insensitive match; tolerates simple plurals (witness -> witnesses)."""
    pattern = r"\b" + re.escape(term.lower()) + r"(?:s|es)?\b"
    return re.search(pattern, text.lower()) is not None


def missing_terms(terms: list[str], text: str) -> list[str]:
    return [t for t in terms if not term_present(t, text)]


def within_tolerance(actual: int, target: int, tol: float) -> bool:
    return abs(actual - target) <= target * tol


def slugify(term: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-")


def parse_glossary(path: Path) -> dict[str, str]:
    """Parse lines like `Term: definition` (also accepts `Term - definition`)."""
    entries: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for sep in (":", " - ", " – "):
            if sep in line:
                term, definition = line.split(sep, 1)
                if term.strip() and definition.strip():
                    entries[term.strip()] = definition.strip()
                break
    return entries