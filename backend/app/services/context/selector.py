import re
from typing import Any

CONTEXT_FIELD_LABELS: dict[str, str] = {
    "name": "Name",
    "professional_background": "Professional background",
    "experience_years": "Years of experience",
    "skills": "Skills",
    "preferences": "Answer preferences",
    "learning_goals": "Learning goals",
    "interview_goals": "Interview goals",
    "other_information": "Other information",
}

_PERSONAL = re.compile(r"\b(my|me|mine|myself)\b", re.IGNORECASE)
_CAREER = re.compile(
    r"\b(interview\w*|job|jobs|role|career|resume|cv|hiring|hire|promotion|position)\b", re.IGNORECASE
)
_LEARNING = re.compile(r"\b(learn\w*|study\w*|roadmap|prepare|preparation|practice|upskill\w*)\b", re.IGNORECASE)

_ALWAYS = {"preferences"}
_CAREER_FIELDS = {"professional_background", "experience_years", "skills", "interview_goals"}
_LEARNING_FIELDS = {"professional_background", "learning_goals"}


def select_relevant_context(question: str, mode_key: str, context: dict[str, Any]) -> dict[str, Any]:
    """Return only the parts of the stored user context that are relevant to this question."""
    available = {key: value for key, value in context.items() if value not in (None, "", [])}
    if not available:
        return {}

    if _PERSONAL.search(question):
        selected = set(available)
    else:
        selected = set(_ALWAYS)
        if mode_key == "interview" or _CAREER.search(question):
            selected |= _CAREER_FIELDS
        if mode_key == "learning" or _LEARNING.search(question):
            selected |= _LEARNING_FIELDS
        if _mentions_skill(question, available.get("skills") or []):
            selected |= {"skills", "professional_background"}

    return {key: available[key] for key in CONTEXT_FIELD_LABELS if key in selected and key in available}


def _mentions_skill(question: str, skills: list[str]) -> bool:
    lowered = question.lower()
    return any(
        re.search(rf"(?<!\w){re.escape(skill.lower())}(?!\w)", lowered) for skill in skills if skill.strip()
    )
