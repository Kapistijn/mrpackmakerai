"""Catalog search endpoints backed by the source registry."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.enums import LoaderType
from app.schemas.mod import ModSearchResponse
from app.services.source_registry import (
    UnknownModSourceError,
    create_default_registry,
)

router = APIRouter()


@router.get("/search", response_model=ModSearchResponse)
async def search_mods(
    q: str = Query("", description="Search query"),
    mc: str = Query(..., description="Minecraft version"),
    loader: LoaderType = Query(..., description="Mod loader"),
    category: str | None = Query(None, description="Category filter"),
    source: str = Query("all", description="Catalog source ID, all (or legacy both)"),
    limit: int = Query(20, ge=1, le=50),
):
    registry = create_default_registry()
    source = source.lower()
    try:
        if source in {"all", "both"}:
            providers = registry.providers(available_only=True)
        else:
            provider = registry.get(source)
            if not provider.available:
                raise HTTPException(status_code=503, detail=f"Catalog source '{source}' is not configured")
            providers = (provider,)

        results = []
        total = 0
        for provider in providers:
            hits, count = await provider.search(q, mc, loader, category, limit)
            results.extend(hits)
            total += count
        results.sort(key=lambda mod: mod.downloads, reverse=True)
        availability = {source_id: registry.is_available(source_id) for source_id in registry.ids()}
        return ModSearchResponse(
            results=results[:limit],
            total=total,
            modrinth_available=availability.get("modrinth", False),
            curseforge_available=availability.get("curseforge", False),
            available_sources=availability,
        )
    except UnknownModSourceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        await registry.close()


@router.get("/{source}/{mod_id}")
async def get_mod_detail(
    source: str,
    mod_id: str,
    mc: str = Query(...),
    loader: LoaderType = Query(...),
):
    registry = create_default_registry()
    try:
        provider = registry.get(source)
        if not provider.available:
            raise HTTPException(status_code=503, detail=f"Catalog source '{source}' is not configured")
        detail = await provider.get_mod_detail(mod_id, mc, loader)
        if not detail:
            raise HTTPException(status_code=404, detail="Mod not found or no compatible version")
        return detail
    except UnknownModSourceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        await registry.close()
