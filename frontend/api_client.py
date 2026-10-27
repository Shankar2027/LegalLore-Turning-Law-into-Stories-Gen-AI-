"""Thin HTTP client for the FastAPI backend."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

class APIError(Exception):
    pass

def _handle(resp: requests.Response):
    if resp.ok:
        return resp.json()
    try:
        detail = resp.json().get("detail", resp.text)
    except ValueError:
        detail = resp.text
    if isinstance(detail, list):
        detail = "; ".join(d.get("msg", str(d)) for d in detail)
    raise APIError(f"{resp.status_code}: {detail}")

def get_terms() -> list[str]:
    try:
        return _handle(requests.get(f"{BACKEND_URL}/terms", timeout=10))["terms"]
    except requests.RequestException as e:
        raise APIError(f"Cannot reach backend at {BACKEND_URL} ({e.__class__.__name__})")

def get_user(username: str) -> dict:
    return _handle(requests.get(f"{BACKEND_URL}/user/{username}"))

def update_score(username: str, points: int) -> dict:
    return _handle(requests.post(f"{BACKEND_URL}/user/{username}/score", json={"score": points}))

def upload_pdfs(files) -> str:
    resp = requests.post(f"{BACKEND_URL}/upload_pdf", files=files)
    return _handle(resp).get("extracted_text", "")

def generate_story(terms, word_count, genre, age_group, include_quiz, language="English", quiz_difficulty="Beginner", case_law_mode=False, pdf_context=None, username="guest") -> dict:
    payload = {
        "terms": terms, 
        "word_count": word_count, 
        "genre": genre,
        "age_group": age_group, 
        "include_quiz": include_quiz,
        "language": language,
        "quiz_difficulty": quiz_difficulty,
        "case_law_mode": case_law_mode,
        "pdf_context": pdf_context,
        "username": username
    }
    try:
        return _handle(requests.post(f"{BACKEND_URL}/story", json=payload, timeout=180))
    except requests.RequestException as e:
        raise APIError(f"Backend request failed ({e.__class__.__name__})")