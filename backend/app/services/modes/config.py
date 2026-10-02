from dataclasses import dataclass
from typing import Literal

Verbosity = Literal["short", "medium", "long"]
TechnicalDepth = Literal["basic", "intermediate", "advanced"]


@dataclass(frozen=True)
class AnswerMode:
    key: str
    name: str
    description: str
    system_instruction: str
    verbosity: Verbosity
    technical_depth: TechnicalDepth
    include_examples: bool
    include_followups: bool


ANSWER_MODES: dict[str, AnswerMode] = {
    mode.key: mode
    for mode in (
        AnswerMode(
            key="learning",
            name="Learning",
            description="Builds understanding from fundamentals with simple examples.",
            system_instruction=(
                "Explain the topic in a progressive learning-oriented manner. "
                "Start with intuition, then explain the technical details. "
                "Explain technical terminology when you first use it and avoid unnecessary jargon. "
                "End with short key takeaways when appropriate."
            ),
            verbosity="medium",
            technical_depth="basic",
            include_examples=True,
            include_followups=False,
        ),
        AnswerMode(
            key="interview",
            name="Interview",
            description="Interview-ready, structured answers with likely follow-up questions.",
            system_instruction=(
                "Answer as an interview preparation assistant. "
                "Give a concise but technically strong, well-structured answer. "
                "Highlight the concepts an interviewer would expect to hear. "
                "Avoid unnecessarily long explanations unless asked."
            ),
            verbosity="medium",
            technical_depth="advanced",
            include_examples=True,
            include_followups=True,
        ),
        AnswerMode(
            key="research",
            name="Research",
            description="Detailed, structured analysis with trade-offs.",
            system_instruction=(
                "Provide a detailed, structured analysis organised into clear sections. "
                "Separate established facts from assumptions or opinions and explain trade-offs. "
                "You do not have web access, so say when information may be outdated or needs verification."
            ),
            verbosity="long",
            technical_depth="advanced",
            include_examples=True,
            include_followups=False,
        ),
        AnswerMode(
            key="concise",
            name="Concise",
            description="Short, direct answers.",
            system_instruction=(
                "Answer the question directly and briefly. "
                "Skip background, caveats and examples unless they are essential."
            ),
            verbosity="short",
            technical_depth="intermediate",
            include_examples=False,
            include_followups=False,
        ),
        AnswerMode(
            key="technical",
            name="Technical",
            description="Assumes technical background; focuses on implementation and architecture.",
            system_instruction=(
                "Assume the user has a strong technical background. "
                "Use precise terminology and focus on implementation details, architecture and trade-offs. "
                "Include code snippets where they clarify the answer."
            ),
            verbosity="medium",
            technical_depth="advanced",
            include_examples=True,
            include_followups=False,
        ),
        AnswerMode(
            key="detailed",
            name="Detailed",
            description="Thorough, comprehensive explanations.",
            system_instruction=(
                "Give a thorough, comprehensive answer that covers the topic end to end, "
                "including edge cases and practical considerations, organised with headings."
            ),
            verbosity="long",
            technical_depth="intermediate",
            include_examples=True,
            include_followups=False,
        ),
        AnswerMode(
            key="custom",
            name="Custom",
            description="Follows your own answer instructions from Settings.",
            system_instruction="Follow the user's custom answer instructions provided below.",
            verbosity="medium",
            technical_depth="intermediate",
            include_examples=False,
            include_followups=False,
        ),
    )
}

DEFAULT_MODE = "learning"


def get_mode(key: str) -> AnswerMode:
    try:
        return ANSWER_MODES[key]
    except KeyError:
        raise ValueError(f"Unknown answer mode '{key}'. Valid modes: {', '.join(ANSWER_MODES)}") from None
