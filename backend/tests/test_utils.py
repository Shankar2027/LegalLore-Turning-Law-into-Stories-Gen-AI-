from app.utils import count_words, missing_terms, term_present, within_tolerance
from app.utils import parse_glossary
from pathlib import Path


def test_count_words():
    assert count_words("The judge's gavel - it's well-known!") == 5


def test_term_matching_and_plurals():
    assert term_present("witness", "Three Witnesses arrived.")
    assert term_present("Defense Attorney", "the defense attorney smiled")
    assert not term_present("bail", "bailiff")


def test_missing_terms():
    assert missing_terms(["jury", "bail"], "The jury sat.") == ["bail"]


def test_tolerance():
    assert within_tolerance(105, 100, 0.1)
    assert not within_tolerance(120, 100, 0.1)


def test_dataset_parses():
    g = parse_glossary(Path(__file__).parent.parent / "data" / "Legal_Problem_Statement.txt")
    assert len(g) >= 20 and "Verdict" in g
