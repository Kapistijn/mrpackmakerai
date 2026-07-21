"""Entry point for running the MrPackMaker backend server."""

import sys
from pathlib import Path

import uvicorn

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
