"""Pydantic schemas: API contracts + structured LLM outputs."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Genre = Literal[
    "Adventure", "Mystery", "Fantasy", "Sci-Fi", "Comedy",
    "Fable", "Historical", "Superhero", "Real Case Law"
]
AgeGroup = Literal["6-8", "9-12", "13-15"]


# ---------- API ----------
class StoryRequest(BaseModel):
    terms: list[str] = Field(..., min_length=3, max_length=3, description="Exactly 3 legal terms")
    word_count: int = Field(..., ge=50, le=1000)
    genre: Genre
    age_group: AgeGroup = "9-12"
    include_quiz: bool = True
    language: str = "English"          # <-- NEW: Multilingual Support
    quiz_difficulty: str = "Beginner"  # <-- NEW: Adaptive Quiz Difficulty
    case_law_mode: bool = False        # <-- NEW: Real Case Law Mode
    pdf_context: str | None = None     # <-- NEW: Holds extracted PDF text
    username: str = "guest"            # <-- NEW: Tracks the current user

    @field_validator("terms")
    @classmethod
    def _unique_clean(cls, v: list[str]) -> list[str]:
        cleaned = [t.strip() for t in v if t.strip()]
        if len({t.lower() for t in cleaned}) != 3:
            raise ValueError("Please choose 3 different legal terms.")
        return cleaned


# NEW: Chat Request schema for the interactive character chat
class ChatRequest(BaseModel):
    story_context: str = Field(..., description="The generated story text to give the character context")
    legal_terms: list[str] = Field(..., description="The 3 legal terms involved")
    user_message: str = Field(..., description="The message from the user")


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(..., min_length=4, max_length=4)
    answer_index: int = Field(..., ge=0, le=3)
    explanation: str


class QuizSet(BaseModel):
    questions: list[QuizQuestion] = Field(..., min_length=3, max_length=3)


class CriticReport(BaseModel):
    score: int = Field(..., ge=1, le=10)
    terms_used_correctly: bool
    age_appropriate: bool
    genre_match: bool
    issues: list[str] = []
    suggestions: str = ""


class StoryResponse(BaseModel):
    title: str
    story: str
    genre: str
    terms: list[str]
    definitions: dict[str, str]
    requested_words: int
    actual_words: int
    revisions_used: int
    critic: CriticReport
    quiz: QuizSet | None = None
    image_url: str | None = None      # <-- NEW: AI Illustration
    audio_base64: str | None = None   # <-- NEW: Audio TTS


class TermsResponse(BaseModel):
    count: int
    terms: list[str]


# ---------- Structured LLM output ----------
class StoryDraft(BaseModel):
    title: str = Field(..., description="Short catchy story title")
    story: str = Field(..., description="The full story text, plain paragraphs")
    image_prompt: str = Field(..., description="A highly descriptive prompt to generate an AI illustration of the story.")