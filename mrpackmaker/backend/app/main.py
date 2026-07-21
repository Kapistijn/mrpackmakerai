"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import ai, compatibility, health, modpack, mods, projects, settings
from app.db.session import init_db
from app.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        setup_logging()
        await init_db()
    except Exception as e:
        print(f"Error during startup: {e}")
        import traceback
        traceback.print_exc()
        raise
    yield


app = FastAPI(
    title="MrPackMaker",
    description="AI Minecraft Modpack Generator",
    version="1.0.0",
    lifespan=lifespan,
)

try:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except Exception as e:
    print(f"Error adding CORS middleware: {e}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "code": "internal_error"},
    )


try:
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
    app.include_router(mods.router, prefix="/api/mods", tags=["mods"])
    app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
    app.include_router(compatibility.router, prefix="/api/compatibility", tags=["compatibility"])
    app.include_router(modpack.router, prefix="/api/modpack", tags=["modpack"])
    app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
except Exception as e:
    print(f"Error including routers: {e}")
    import traceback
    traceback.print_exc()

# Serve the SPA in production only after every API route has been registered.
# Static assets use their normal paths and unknown client-side routes fall back
# to index.html, making a page refresh on /settings or /project/12 work.
_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str = ""):
        requested = (_frontend_dist / full_path).resolve()
        if _frontend_dist.resolve() in requested.parents and requested.is_file():
            return FileResponse(requested)
        return FileResponse(_frontend_dist / "index.html")
