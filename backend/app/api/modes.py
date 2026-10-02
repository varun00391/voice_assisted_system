from fastapi import APIRouter

from app.schemas.mode import ModeOut, ModesResponse
from app.services.modes.config import ANSWER_MODES, DEFAULT_MODE

router = APIRouter(prefix="/api/v1", tags=["modes"])


@router.get("/modes", response_model=ModesResponse)
async def list_modes() -> ModesResponse:
    return ModesResponse(
        default=DEFAULT_MODE,
        modes=[
            ModeOut(
                key=mode.key,
                name=mode.name,
                description=mode.description,
                verbosity=mode.verbosity,
                technical_depth=mode.technical_depth,
                include_examples=mode.include_examples,
                include_followups=mode.include_followups,
            )
            for mode in ANSWER_MODES.values()
        ],
    )
