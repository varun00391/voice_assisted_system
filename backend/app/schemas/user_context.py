from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import CleanStr, optional_clean_str

Skill = Annotated[CleanStr, Field(min_length=1, max_length=60)]


class UserContext(BaseModel):
    """Information the user explicitly chooses to share. All fields are optional."""

    model_config = ConfigDict(extra="forbid")

    name: optional_clean_str(100) = None
    professional_background: optional_clean_str(500) = None
    experience_years: Annotated[int | None, Field(ge=0, le=80)] = None
    skills: Annotated[list[Skill], Field(max_length=50)] = Field(default_factory=list)
    preferences: optional_clean_str(1000) = None
    learning_goals: optional_clean_str(1000) = None
    interview_goals: optional_clean_str(1000) = None
    other_information: optional_clean_str(2000) = None
