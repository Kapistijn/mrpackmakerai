"""Entry point for running the MrPackMaker backend server."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

# run.py is inside backend/ and app/ is a sibling of this file.
# The old parent.parent path pointed at the repository root, so the installer
# completed successfully and the server crashed immediately afterwards.
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> None:
    host = os.getenv("MRPACK_HOST", "127.0.0.1")
    try:
        port = int(os.getenv("MRPACK_PORT", "8000"))
    except ValueError as exc:
        raise SystemExit("MRPACK_PORT must be a number, for example 8000") from exc
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
