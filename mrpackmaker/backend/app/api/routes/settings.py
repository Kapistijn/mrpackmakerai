"""Safe settings, model discovery and protected admin configuration."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException

from app.config import config
from app.schemas.settings import (
    AIModelSelection,
    AISettingsPublic,
    AdminSettingsResponse,
    AdminSettingsUpdate,
    SettingsOverview,
)
from app.services.ai_provider import AIProviderError, create_ai_provider
from app.services.settings_service import settings_service

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
    finally:
        await provider.close()


@router.post("/ai/model", response_model=AISettingsPublic)
async def select_model(body: AIModelSelection):
    """Choose the active AI model. Model choice is not a secret, so this is not
    gated behind admin auth. An empty model re-enables auto-selection."""
    model = body.model.strip()
    if model:
        provider = create_ai_provider()
        try:
            available = await provider.list_models()
        except AIProviderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        finally:
            await provider.close()
        # Only reject when the provider actually reported a model list that does
        # not contain the request; some providers expose no listing at all.
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
