"""MrPackMaker backend application package."""

# Single source of truth for the application version. The FastAPI app, the
# /api/health payload, the installer and the launcher all read this so the
# reported version can never drift again.
__version__ = "2.5.4"
