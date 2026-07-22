"""Entry point for running the MrPackMaker backend server."""

import os
import sys
from pathlib import Path

import uvicorn

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    # Bind to loopback by default. This is a local desktop app with no
    # authentication, and ARCHITECTURE.md explicitly warns against exposing it
    # on the network. Users who intentionally want LAN access can opt in with
    # MRPACK_HOST=0.0.0.0 (and optionally MRPACK_PORT).
    host = os.getenv("MRPACK_HOST", "127.0.0.1")
    port = int(os.getenv("MRPACK_PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
