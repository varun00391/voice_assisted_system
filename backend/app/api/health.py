from fastapi import APIRouter

from app.api.deps import RouterDep, SettingsDep

router = APIRouter()


@router.get("/health")
async def health(settings: SettingsDep) -> dict:
    return {"status": "healthy", "version": settings.app_version}


@router.get("/api/v1/config")
async def client_config(settings: SettingsDep) -> dict:
    return {
        "max_audio_duration_seconds": settings.max_audio_duration_seconds,
        "max_audio_size_mb": settings.max_audio_size_mb,
    }


@router.get("/api/v1/providers/health")
async def provider_health(llm_router: RouterDep) -> dict:
    return {"providers": llm_router.health()}
