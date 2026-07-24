"""Low-risk launch hardening helpers shared by logs and boundary tests."""
from __future__ import annotations
import re
from typing import Any

_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization)(\s*[=:]\s*)([^,\s;]+)")
_ENV = re.compile(r"(?i)(MRPACK_[A-Z0-9_]+|OPENAI_API_KEY|MODRINTH_API_KEY|CURSEFORGE_API_KEY)(\s*[=:]\s*)([^,\s;]+)")

def redact_log_line(value: Any) -> str:
    text = str(value)
    text = _SECRET.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)
    return _ENV.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)

def bounded_upload_size(size: Any, *, maximum: int = 512 * 1024 * 1024) -> int:
    try: value = int(size)
    except (TypeError, ValueError): return 0
    return max(0, min(value, maximum))

def health_status(reachable: bool) -> str:
    return "ok" if reachable else "degraded"

def fallback_available(reachable: bool) -> bool:
    return True

def retry_budget(attempt: Any, *, maximum: int = 5) -> int:
    try: value = int(attempt)
    except (TypeError, ValueError): value = 0
    return max(0, min(value, maximum))

def progress_key(event: dict[str, Any]) -> tuple[Any, Any, Any]:
    return event.get("run_id"), event.get("step"), event.get("message")
