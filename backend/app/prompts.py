"""Prompt templates for the Architect (writer), Critic (reviewer) and Quiz agents."""
from langchain_core.prompts import ChatPromptTemplate

AGE_STYLE = {
    "6-8": "very simple sentences, concrete images, friendly tone, no scary content",
    "9-12": "clear language, light humour, relatable school-age characters",
    "13-15": "richer vocabulary, more plot depth and moral nuance, still age-appropriate",
}

ARCHITECT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are 'The Architect', a gifted children's author who teaches law through stories. "
     "If CASE LAW MODE is True, write a story based on a real, famous historical court case that used these terms, simplified for children. If False, invent a fun fictional story. "
     "Every legal term must be used NATURALLY and ACCURATELY so a young reader understands its real meaning from context. Never lecture; show the term through action and dialogue. "
     "Content must be safe for young learners (no graphic violence). "
     "You also act as Art Director: provide an 'image_prompt' describing the main scene for an AI image generator (e.g., 'A colorful digital illustration of a cute cartoon dog holding a legal gavel...')."),
    ("human",
     "Write a {genre} story for ages {age_group} ({age_style}).\n\n"
     "CASE LAW MODE: {case_law_mode}\n\n"
     "LANGUAGE REQUIREMENT: Write the entire story and title strictly in {language}. "
     "(CRITICAL: You must keep the 'image_prompt' in English so the image generator can understand it).\n\n"
     "LENGTH: about {word_count} words (acceptable range {min_words}-{max_words}).\n\n"
     "LEGAL TERMS (use each at least once, exactly as written, in the correct legal sense):\n"
     "{definitions}\n\n"
     "OPTIONAL related ideas you may touch on lightly:\n{related}\n\n"
     "{feedback}"
     "Structure: a beginning, a problem or conflict that needs the legal concepts, and a satisfying ending with a gentle takeaway. "
     "Return a short title, the story text in plain paragraphs, and the image_prompt."),
])

FEEDBACK_BLOCK = (
    "REVISION REQUIRED. Your previous draft was:\n\"\"\"\n{previous}\n\"\"\"\n"
    "Problems found:\n{issues}\n"
    "Reviewer suggestions: {suggestions}\n"
    "Rewrite the whole story fixing every problem.\n\n"
)

CRITIC_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are 'The Critic', a strict legal-education reviewer. You check children's stories "
     "for legal accuracy, age appropriateness and genre fit. Be honest and specific."),
    ("human",
     "Review this {genre} story written for ages {age_group}.\n\n"
     "LANGUAGE CONTEXT: The story is written in {language}. Evaluate it accordingly.\n\n"
     "STORY:\n\"\"\"\n{story}\n\"\"\"\n\n"
     "REQUIRED TERMS AND TRUE DEFINITIONS:\n{definitions}\n\n"
     "Judge:\n"
     "1. terms_used_correctly: is EACH term used in a way consistent with its definition "
     "(a reader could infer the meaning)?\n"
     "2. age_appropriate: safe and understandable for ages {age_group}?\n"
     "3. genre_match: does it genuinely read as {genre}?\n"
     "4. score 1-10 overall teaching + storytelling quality.\n"
     "List concrete issues (empty if none) and one short improvement suggestion."),
])

QUIZ_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You write short, fair multiple-choice quizzes for young learners."),
    ("human",
     "Based on this story and these definitions, create exactly 3 multiple-choice questions "
     "(4 options each) for ages {age_group}: one per legal term. \n\n"
     "DIFFICULTY LEVEL: {difficulty}\n"
     "- If Beginner: Test basic understanding of what the legal word means.\n"
     "- If Advanced: Create 'What if' application scenarios. Ask how a character should use the legal word in a new situation.\n\n"
     "LANGUAGE REQUIREMENT: Write all questions, options, and explanations in {language}.\n\n"
     "answer_index is the 0-based correct option. Add a one-sentence kid-friendly explanation.\n\n"
     "STORY:\n{story}\n\nDEFINITIONS:\n{definitions}"),
])