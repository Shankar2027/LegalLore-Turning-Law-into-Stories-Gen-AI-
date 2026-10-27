"""Reusable Streamlit widgets."""
import re

import streamlit as st

GENRES = ["Adventure", "Mystery", "Fantasy", "Sci-Fi", "Comedy", "Fable", "Historical", "Superhero"]
AGE_GROUPS = ["6-8", "9-12", "13-15"]

CSS = """
<style>
.block-container {max-width: 900px; padding-top: 2rem;}
.story-card {background:#fffdf7; border:1px solid #f0e6c8; border-radius:16px;
             padding:1.5rem 2rem; line-height:1.85; font-size:1.08rem; color:#2b2b2b;}
.story-card mark {background:#ffe08a; padding:0 .25em; border-radius:6px; font-weight:600;}
.badge {display:inline-block; padding:.15rem .7rem; border-radius:999px;
        background:#eef2ff; color:#3730a3; font-size:.8rem; margin-right:.4rem;}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def sidebar_inputs(all_terms: list[str]) -> dict:
    with st.sidebar:
        st.header("Story settings")
        
        # Wrapping everything inside an st.form stops the page from reloading instantly
        with st.form(key="story_settings_form"):
            terms = st.multiselect("Pick exactly 3 legal terms", all_terms, max_selections=3,
                                   placeholder="Choose 3 terms…")
            genre = st.selectbox("Genre", GENRES)
            age = st.select_slider("Reader age", AGE_GROUPS, value="9-12")
            words = st.slider("Word count", 50, 1000, 300, step=25)
            # Toggles inside forms check their state only on submit
            quiz = st.checkbox("Add a quick quiz", value=True) 
            
            # Use form_submit_button instead of standard button inside forms
            go = st.form_submit_button("✨ Create story", type="primary", use_container_width=True)
            
        # Form validation: Ensure exactly 3 terms are selected when they click submit
        if go and len(terms) != 3:
            st.error(f"Please select exactly 3 terms. You only picked {len(terms)}.")
            go = False  # Cancel the submission if validation fails

    return dict(terms=terms, genre=genre, age_group=age, word_count=words, include_quiz=quiz, go=go)


def highlight_terms(story: str, terms: list[str]) -> str:
    html = story.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for t in terms:
        # Added (?i) directly into the regex pattern to guarantee it catches variations 
        # like "Appeal", "appeal", or "APPEAL" without missing any selected terms.
        html = re.sub(rf"(?i)\b({re.escape(t)}(?:s|es)?)\b", r"<mark>\1</mark>", html)
    return html.replace("\n", "<br>")


def story_view(res: dict):
    st.subheader(res["title"])
    st.markdown(f'<span class="badge">{res["genre"]}</span>'
                f'<span class="badge">{res["actual_words"]} / {res["requested_words"]} words</span>'
                f'<span class="badge">quality {res["critic"]["score"]}/10</span>',
                unsafe_allow_html=True)
    body = highlight_terms(res["story"], res["terms"])
    st.markdown(f'<div class="story-card">{body}</div>', unsafe_allow_html=True)
    st.download_button("⬇ Download story", f'{res["title"]}\n\n{res["story"]}',
                       file_name="legal_lore_story.txt")


def glossary_view(defs: dict[str, str]):
    st.subheader("📖 What the words mean")
    for term, d in defs.items():
        with st.expander(term, expanded=True):
            st.write(d)


def critic_view(c: dict, revisions: int):
    with st.expander("🔍 Critic's report"):
        cols = st.columns(3)
        cols[0].metric("Score", f'{c["score"]}/10')
        cols[1].metric("Revisions", revisions)
        cols[2].metric("Terms correct", "✅" if c["terms_used_correctly"] else "⚠️")
        for i in c.get("issues", []):
            st.warning(i)
        if c.get("suggestions"):
            st.caption(f'Suggestion: {c["suggestions"]}')

# Note: The old `quiz_view` function has been intentionally removed from this file 
# because your quiz scoring, database updates, and balloon logic are now entirely 
# handled directly inside your updated `app.py` file!