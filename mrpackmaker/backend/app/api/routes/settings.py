"""Unified browser-facing settings, model discovery, TTS test and admin.

Model choice, connection endpoints and non-secret preferences are not secrets,
so the primary settings routes are open for this local, single-user app.  API
keys are still stored encrypted and are only ever returned masked.  The legacy
token-gated admin routes remain for shared deployments.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException, Response

from app.config import config
from app.schemas.settings import (
    AIModelSelection,
    AISettingsPublic,
    AdminSettingsResponse,
    AdminSettingsUpdate,
    SettingsOverview,
    TTSTestRequest,
    UnifiedSettingsUpdate,
)
from app.services.ai_provider import AIProviderError, create_ai_provider
from app.services.settings_service import SECRET_KEYS, settings_service
from app.services.tts import TTSClient, TTSError

router = APIRouter()


def _require_admin(x_admin_token: str | None) -> None:
    expected = config.security.admin_token
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Admin settings are disabled. Configure MRPACK_ADMIN_TOKEN first.",
        )
    if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=403, detail="Admin credentials are required")


@router.get("", response_model=SettingsOverview)
async def get_settings():
    return await settings_service.overview()


@router.patch("/config", response_model=SettingsOverview)
async def update_settings(body: UnifiedSettingsUpdate):
    """Apply the single unified settings form. Keys are stored encrypted."""
    try:
        return await settings_service.update_settings(body)
    except ValueError as exc:
        # Pydantic validation of provider / base_url etc.
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/secrets/{name}", response_model=SettingsOverview)
async def delete_secret(name: str):
    """Permanently delete a stored API key (modrinth, curseforge, ai, tts)."""
    try:
        return await settings_service.delete_secret(name)
    except KeyError as exc:
        allowed = ", ".join(sorted(SECRET_KEYS))
        raise HTTPException(status_code=404, detail=f"Unknown secret '{name}'. Allowed: {allowed}") from exc


@router.get("/ai/models")
async def list_models():
    provider = create_ai_provider()
    try:
        models = await provider.list_models()
        return {
            "provider": provider.provider_id,
            "models": models,
            "selected_model": config.ai.model or (models[0] if models else None),
        }
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        await provider.close()


@router.post("/ai/model", response_model=AISettingsPublic)
async def select_model(body: AIModelSelection):
    """Choose the active AI model. Not gated behind admin auth (not a secret).
    An empty model re-enables auto-selection."""
    model = body.model.strip()
    if model:
        provider = create_ai_provider()
        try:
            available = await provider.list_models()
        except AIProviderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        finally:
            await provider.close()
        if available and model not in available:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model}' is not available from the configured provider",
            )
    return settings_service.set_model(model)


@router.post("/ai/test")
async def test_ai_connection():
    provider = create_ai_provider()
    try:
        status = await provider.connection_status()
        return {
            "provider": status.provider,
            "reachable": status.reachable,
            "active_model": status.active_model,
            "detail": status.detail,
        }
    finally:
        await provider.close()


@router.post("/voice/tts/test")
async def test_tts(body: TTSTestRequest):
    """Synthesize a short sample and stream it back as audio for playback."""
    client = TTSClient()
    try:
        audio, content_type = await client.synthesize(body.text)
    except TTSError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(content=audio, media_type=content_type)


@router.get("/admin", response_model=AdminSettingsResponse)
async def get_admin_settings(x_admin_token: str | None = Header(default=None)):
    _require_admin(x_admin_token)
    return settings_service.admin_view()


@router.patch("/admin", response_model=AdminSettingsResponse)
async def update_admin_settings(
    body: AdminSettingsUpdate,
    x_admin_token: str | None = Header(default=None),
):
    _require_admin(x_admin_token)
    return settings_service.update(body)
