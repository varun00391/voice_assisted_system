from pydantic import BaseModel


class ModeOut(BaseModel):
    key: str
    name: str
    description: str
    verbosity: str
    technical_depth: str
    include_examples: bool
    include_followups: bool


class ModesResponse(BaseModel):
    default: str
    modes: list[ModeOut]
