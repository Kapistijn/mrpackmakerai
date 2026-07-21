"""Health check endpoint."""

from fastapi import APIRouter

from app.config import config
from app.services.lmstudio import LMStudioClient

router = APIRouter()


@router.get("/health")
async def health_check():
    lm = LMStudioClient()
    lm_available = await lm.is_available()
    
    response = {
        "status": "ok",
        "lmstudio": "connected" if lm_available else "offline",
        "ai_config": {
            "provider": config.ai.provider,
            "url": config.ai.url,
            "model": config.ai.model or "auto-select",
        }
    }
    
    if lm_available:
        try:
            model = await lm.get_model()
            response["current_model"] = model
        except Exception as e:
            response["model_error"] = str(e)
    
    return response
