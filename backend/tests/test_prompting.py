from types import SimpleNamespace

import pytest

from app.services.context.selector import select_relevant_context
from app.services.modes.config import ANSWER_MODES, get_mode
from app.services.prompt_builder import build_messages

CONTEXT = {
    "name": "Varun",
    "professional_background": "Data Scientist",
    "experience_years": 10,
    "skills": ["Python", "RAG", "FastAPI"],
    "preferences": "Use Python examples",
    "learning_goals": "Learn LLM systems design",
    "interview_goals": "Prepare for Senior AI Architect interviews",
    "other_information": "Lives in India",
}


def test_all_modes_have_complete_configuration():
    assert {"learning", "interview", "research", "concise", "technical", "detailed", "custom"} <= set(ANSWER_MODES)
    for mode in ANSWER_MODES.values():
        assert mode.system_instruction and mode.description


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        get_mode("poetry")


def test_messages_include_mode_history_and_question_in_order():
    history = [SimpleNamespace(role="user", content="What is RAG?"), SimpleNamespace(role="assistant", content="RAG is...")]
    messages = build_messages(
        question="Why embeddings?", mode=get_mode("interview"), history=history, user_context={}
    )

    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert "Answer mode: Interview." in messages[0]["content"]
    assert "follow-up questions" in messages[0]["content"]
    assert messages[-1]["content"] == "Why embeddings?"
    assert "Background the user chose" not in messages[0]["content"]


def test_custom_instructions_only_apply_in_custom_mode():
    custom = build_messages(
        question="q", mode=get_mode("custom"), history=[], user_context={}, custom_instructions="Answer in haiku"
    )
    concise = build_messages(
        question="q", mode=get_mode("concise"), history=[], user_context={}, custom_instructions="Answer in haiku"
    )
    assert "Answer in haiku" in custom[0]["content"]
    assert "Answer in haiku" not in concise[0]["content"]


def test_user_context_is_rendered_as_background():
    messages = build_messages(
        question="q", mode=get_mode("concise"), history=[], user_context={"skills": ["Python", "RAG"]}
    )
    assert "- Skills: Python, RAG" in messages[0]["content"]


def test_generic_question_only_gets_preferences():
    selected = select_relevant_context("What is a vector database?", "concise", CONTEXT)
    assert selected == {"preferences": "Use Python examples"}


def test_interview_question_gets_career_context():
    selected = select_relevant_context("How should I prepare for this interview?", "concise", CONTEXT)
    assert {"professional_background", "experience_years", "skills", "interview_goals"} <= set(selected)
    assert "name" not in selected
    assert "other_information" not in selected


def test_interview_mode_gets_career_context():
    selected = select_relevant_context("Explain transformers", "interview", CONTEXT)
    assert "interview_goals" in selected


def test_personal_question_gets_everything():
    assert select_relevant_context("What do you know about me?", "concise", CONTEXT) == CONTEXT


def test_skill_mention_gets_skills():
    selected = select_relevant_context("Compare FastAPI and Flask", "concise", CONTEXT)
    assert "skills" in selected


def test_empty_context_selects_nothing():
    assert select_relevant_context("about me", "interview", {"skills": [], "name": None}) == {}
