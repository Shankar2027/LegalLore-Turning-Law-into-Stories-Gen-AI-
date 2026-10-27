"""FastAPI application: /health, /terms, /story, /chat (FAISS + FastEmbed retrieval, Groq LLM)."""
import logging
import io
import PyPDF2
import docx  # <-- Added for Word Document support (run: pip install python-docx)
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from .agents import StoryTeam
from .config import get_settings
from .models import StoryRequest, StoryResponse, TermsResponse, ChatRequest
from .rag_engine import LegalKnowledgeBase
from .utils import count_words
from .database import init_db, get_or_create_user, update_score_and_badges  # <-- DB IMPORTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("legal_lore.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # <-- Starts the SQLite User Database
    s = get_settings()
    kb = LegalKnowledgeBase(s.data_file, s.faiss_dir, s.embed_model)
    kb.ingest()
    app.state.kb = kb
    app.state.team = StoryTeam(s) if s.groq_api_key else None
    if not s.groq_api_key:
        log.warning("GROQ_API_KEY missing - /story and /chat will return 503.")
    yield


app = FastAPI(title="LegalLore API", version="1.0.0",
              description="Turn legal concepts into stories for young learners.", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_list,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health(request: Request):
    return {"status": "ok", "terms_loaded": request.app.state.kb.count(),
            "llm_ready": request.app.state.team is not None}


@app.get("/terms", response_model=TermsResponse)
def terms(request: Request):
    t = request.app.state.kb.list_terms()
    return TermsResponse(count=len(t), terms=t)


# ==========================================
# User Profile & Gamification Endpoints
# ==========================================
@app.get("/user/{username}")
def get_user(username: str):
    return get_or_create_user(username)


@app.post("/user/{username}/score")
def add_score(username: str, points: dict):
    return update_score_and_badges(username, points.get("score", 0))


# ==========================================
# Universal File Upload Endpoint (PDF, DOCX, TXT)
# ==========================================
@app.post("/upload_pdf")
async def upload_documents(files: List[UploadFile] = File(...)):
    extracted_text = ""
    
    for file in files:
        content = await file.read()
        filename = file.filename.lower()
        
        try:
            # 1. Handle PDFs
            if filename.endswith(".pdf"):
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n"
                        
            # 2. Handle Word Documents
            elif filename.endswith(".docx"):
                doc = docx.Document(io.BytesIO(content))
                for para in doc.paragraphs:
                    extracted_text += para.text + "\n"
                    
            # 3. Handle ALL Other Text Formats (.txt, .md, .csv, etc.)
            else:
                extracted_text += content.decode("utf-8") + "\n"
                
        except UnicodeDecodeError:
            log.warning(f"Skipped {filename}: Not a readable text format.")
            continue
        except Exception as e:
            log.warning(f"Error reading {filename}: {e}")
            continue
                
    return {"extracted_text": extracted_text}


@app.post("/story", response_model=StoryResponse)
async def create_story(req: StoryRequest, request: Request):
    kb: LegalKnowledgeBase = request.app.state.kb
    team: StoryTeam | None = request.app.state.team
    if team is None:
        raise HTTPException(503, "LLM not configured. Set GROQ_API_KEY in backend/.env")

    try:
        defs = kb.get_definitions(req.terms)
    except KeyError as e:
        raise HTTPException(422, f"Unknown terms: {e.args[0]}")

    related = kb.related_concepts(req.terms, defs)

    # Inject File text silently so the Architect uses it in the story
    if req.pdf_context:
        related["Source Material"] = req.pdf_context

    try:
        # Unpacking 6 variables returned from the updated agents.py
        draft, report, revisions, quiz, image_url, audio_b64 = await team.run(req, defs, related)
    except Exception as exc:
        log.exception("Story generation failed")
        error_msg = str(exc)
        
        # Graceful handling for Google Gemini 503 Traffic errors
        if "503" in error_msg or "UNAVAILABLE" in error_msg:
            raise HTTPException(
                status_code=503, 
                detail="Google's AI servers are currently busy. Please wait 10 seconds and click Create Story again!"
            )
            
        raise HTTPException(502, f"Story generation failed: {error_msg}")

    return StoryResponse(
        title=draft.title, story=draft.story, genre=req.genre,
        terms=list(defs.keys()), definitions=defs,
        requested_words=req.word_count, actual_words=count_words(draft.story),
        revisions_used=revisions, critic=report, quiz=quiz,
        image_url=image_url,         # <-- AI Image
        audio_base64=audio_b64       # <-- Audio TTS
    )


@app.post("/chat")
async def chat_with_character(req: ChatRequest, request: Request):
    team: StoryTeam | None = request.app.state.team
    if team is None:
        raise HTTPException(503, "LLM not configured. Set GROQ_API_KEY in backend/.env")
    
    try:
        reply = await team.chat(req.story_context, req.legal_terms, req.user_message)
        return {"reply": reply}
    except Exception as exc:
        log.exception("Chat generation failed")
        raise HTTPException(502, f"Chat generation failed: {exc}")