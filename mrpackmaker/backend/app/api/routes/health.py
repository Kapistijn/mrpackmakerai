"""Health check endpoint."""

from fastapi import APIRouter

from app.config import config
from app.services.ai_provider import create_ai_provider

router = APIRouter()


@router.get("/health")
async def health_check():
    # Report the ACTIVE provider (LM Studio or LiteLLM), not a hardcoded one,
    # and always close the client so a health poll never leaks a socket.
    provider = create_ai_provider()
    try:
        status = await provider.connection_status()
    finally:
        await provider.close()

    return {
        "status": "ok",
        "ai": {
            "provider": status.provider,
            "reachable": status.reachable,
            "base_url": config.ai.base_url,
            "model": status.active_model or config.ai.model or "auto-select",
            "detail": status.detail,
        },
    }
