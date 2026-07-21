"""Safe settings, model discovery and protected admin configuration."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException

from app.config import config
from app.schemas.settings import AdminSettingsResponse, AdminSettingsUpdate, SettingsOverview
from app.services.ai_provider import create_ai_provider
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
        return {"provider": provider.provider_id, "models": models, "selected_model": config.ai.model or (models[0] if models else None)}
    finally:
        await provider.close()


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
