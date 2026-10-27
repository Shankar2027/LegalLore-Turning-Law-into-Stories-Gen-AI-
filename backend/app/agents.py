"""Multi-agent pipeline: Architect (writes) <-> Critic (reviews) with a bounded revision loop, plus Quizmaster, Character Chat, Audio, and Images."""
import asyncio
import logging
import urllib.parse
import io
import base64
from gtts import gTTS

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from .config import Settings
from .models import CriticReport, QuizSet, StoryDraft, StoryRequest
from .prompts import (AGE_STYLE, ARCHITECT_PROMPT, CRITIC_PROMPT, FEEDBACK_BLOCK,
                      QUIZ_PROMPT)
from .utils import count_words, missing_terms, within_tolerance

log = logging.getLogger("legal_lore.agents")


def _fmt(defs: dict[str, str]) -> str:
    return "\n".join(f"- {t}: {d}" for t, d in defs.items()) or "(none)"


def generate_audio_sync(text: str, language: str) -> str | None:
    """Generates TTS audio and returns base64 string."""
    try:
        # Map spoken languages to gTTS codes
        lang_map = {"English": "en", "Kannada": "kn", "Telugu": "te", "Hindi": "hi"}
        # FIXED: Added tld="co.in" to bypass regional connection blocks
        tts = gTTS(text=text, lang=lang_map.get(language, "en"), slow=False, tld="co.in")
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return base64.b64encode(fp.getvalue()).decode()
    except Exception as e:
        log.error(f"Audio generation failed: {e}")
        return None
class StoryTeam:
    def __init__(self, settings: Settings):
        self.s = settings

        # Switch to the Lite model which rarely gets 503 traffic jams
        writer = ChatGoogleGenerativeAI(
            model="gemini-flash-lite-latest", 
            google_api_key=settings.groq_api_key,
            temperature=0.85,
            max_retries=5
        )
        judge = ChatGoogleGenerativeAI(
            model="gemini-flash-lite-latest", 
            google_api_key=settings.groq_api_key,
            temperature=0.0,
            max_retries=5
        )
        chat_llm = ChatGoogleGenerativeAI(
            model="gemini-flash-lite-latest", 
            google_api_key=settings.groq_api_key,
            temperature=0.7,
            max_retries=5
        )
        
        self.architect = ARCHITECT_PROMPT | writer.with_structured_output(StoryDraft)
        self.critic = CRITIC_PROMPT | judge.with_structured_output(CriticReport)
        self.quizmaster = QUIZ_PROMPT | judge.with_structured_output(QuizSet)



        # Chat Agent for interactive character cross-examination
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are the main character from the story provided below.\n"
                "A young student is cross-examining you and asking you questions.\n"
                "Stay fully in character, friendly, and age-appropriate!\n"
                "Help the learner understand what happened and explain these legal concepts: {legal_terms}.\n\n"
                "Story Context:\n{story_context}"
            )),
            ("human", "{user_message}"),
        ])
        self.chat_agent = chat_prompt | chat_llm

    # ---------- agents ----------
    async def _write(self, req: StoryRequest, defs: dict, related: dict,
                     prev: StoryDraft | None, issues: list[str], suggestions: str) -> StoryDraft:
        feedback = ""
        if prev is not None:
            feedback = FEEDBACK_BLOCK.format(
                previous=prev.story,
                issues="\n".join(f"- {i}" for i in issues) or "- (see suggestions)",
                suggestions=suggestions or "n/a",
            )
        tol = self.s.word_tolerance
        return await self.architect.ainvoke({
            "genre": req.genre,
            "age_group": req.age_group,
            "age_style": AGE_STYLE[req.age_group],
            "word_count": req.word_count,
            "min_words": int(req.word_count * (1 - tol)),
            "max_words": int(req.word_count * (1 + tol)),
            "definitions": _fmt(defs),
            "related": _fmt(related),
            "feedback": feedback,
            "language": req.language,
            "case_law_mode": str(req.case_law_mode),  # <-- Tells LLM if it's Case Law or Fiction
        })

    async def _review(self, req: StoryRequest, draft: StoryDraft, defs: dict) -> CriticReport:
        return await self.critic.ainvoke({
            "genre": req.genre,
            "age_group": req.age_group,
            "story": draft.story,
            "definitions": _fmt(defs),
            "language": req.language,
        })

    # ---------- orchestration ----------
    async def run(self, req: StoryRequest, defs: dict[str, str], related: dict[str, str]):
        draft: StoryDraft | None = None
        report: CriticReport | None = None
        issues: list[str] = []
        suggestions = ""
        best: tuple[int, StoryDraft, CriticReport] | None = None
        revisions = 0

        for attempt in range(self.s.max_revisions + 1):
            draft = await self._write(req, defs, related, draft if attempt else None,
                                     issues, suggestions)
            words = count_words(draft.story)

            # Deterministic checks first (cheap, never wrong)
            hard_issues: list[str] = []
            if (m := missing_terms(req.terms, draft.story)):
                hard_issues.append(f"Missing required terms: {', '.join(m)}.")
            if not within_tolerance(words, req.word_count, self.s.word_tolerance):
                hard_issues.append(
                    f"Story has {words} words but target is {req.word_count} "
                    f"(+/-{int(self.s.word_tolerance*100)}%)."
                )

            report = await self._review(req, draft, defs)
            issues = hard_issues + list(report.issues)
            suggestions = report.suggestions
            revisions = attempt

            passed = (not hard_issues and report.terms_used_correctly and report.age_appropriate
                      and report.genre_match and report.score >= self.s.min_critic_score)

            rank = report.score - 3 * len(hard_issues)
            if best is None or rank > best[0]:
                best = (rank, draft, report)

            log.info("Attempt %d: words=%d score=%d passed=%s", attempt, words, report.score, passed)
            if passed:
                break
        else:
            # Revisions exhausted -> return best draft
            _, draft, report = best  # type: ignore[misc]

        quiz = None
        if req.include_quiz:
            try:
                quiz = await self.quizmaster.ainvoke({
                    "age_group": req.age_group,
                    "story": draft.story,
                    "definitions": _fmt(defs),
                    "difficulty": req.quiz_difficulty,
                    "language": req.language,
                })
            except Exception:
                log.exception("Quiz generation failed")

        # Feature: AI Illustration (Free using Pollinations API)
        encoded_prompt = urllib.parse.quote(f"Childrens book illustration: {draft.image_prompt}")
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=400&nologo=true"

        # Feature: Audio TTS
        audio_b64 = await asyncio.to_thread(generate_audio_sync, draft.story, req.language)

        return draft, report, revisions, quiz, image_url, audio_b64

    # ---------- interactive cross-examination chat ----------
    async def chat(self, story_context: str, legal_terms: list[str], user_message: str) -> str:
        """Roleplays as the main character answering questions from the young learner."""
        response = await self.chat_agent.ainvoke({
            "story_context": story_context,
            "legal_terms": ", ".join(legal_terms),
            "user_message": user_message,
        })
        return response.content