"""FastAPI application factory."""
from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import ai,compatibility,health,modpack,mods,projects,settings,editor,imports,repair,insights
from app.db.session import init_db,reset_orphaned_generations
from app.logging import setup_logging
logger=logging.getLogger(__name__)
@asynccontextmanager
async def lifespan(app:FastAPI):
 setup_logging();await init_db();await reset_orphaned_generations();yield
app=FastAPI(title='MrPackMaker',description='AI Minecraft Modpack Generator',version='2.2.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173','http://localhost:8000','http://127.0.0.1:8000'],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
@app.exception_handler(Exception)
async def global_exception_handler(request:Request,exc:Exception):logger.exception('Unhandled error on %s %s',request.method,request.url.path);return JSONResponse(status_code=500,content={'detail':'An internal server error occurred.','code':'internal_error'})
app.include_router(health.router,prefix='/api',tags=['health']);app.include_router(projects.router,prefix='/api/projects',tags=['projects']);app.include_router(mods.router,prefix='/api/mods',tags=['mods']);app.include_router(ai.router,prefix='/api/ai',tags=['ai']);app.include_router(compatibility.router,prefix='/api/compatibility',tags=['compatibility']);app.include_router(modpack.router,prefix='/api/modpack',tags=['modpack']);app.include_router(settings.router,prefix='/api/settings',tags=['settings']);app.include_router(editor.router,prefix='/api/editor',tags=['editor']);app.include_router(imports.router,prefix='/api/imports',tags=['imports']);app.include_router(repair.router,prefix='/api/repair',tags=['repair']);app.include_router(insights.router,prefix='/api/insights',tags=['insights'])
_frontend_dist=Path(__file__).resolve().parents[2]/'frontend'/'dist'
if _frontend_dist.exists():
 app.mount('/assets',StaticFiles(directory=str(_frontend_dist/'assets')),name='frontend-assets')
 @app.get('/',include_in_schema=False)
 @app.get('/{full_path:path}',include_in_schema=False)
 async def serve_frontend(full_path:str=''):
  if full_path=='api' or full_path.startswith('api/'):return JSONResponse(status_code=404,content={'detail':'Not found','code':'not_found'})
  requested=(_frontend_dist/full_path).resolve()
  if _frontend_dist.resolve() in requested.parents and requested.is_file():return FileResponse(requested)
  return FileResponse(_frontend_dist/'index.html')
