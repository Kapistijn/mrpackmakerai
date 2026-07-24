"""Small, dependency-free safety primitives used by the 2.5.0 audit.

These helpers keep boundary behavior deterministic: bad user/config/catalog
values are rejected or normalized before they reach async jobs, exporters, or
provider clients. They are intentionally boring. Boring startup and exports are
a feature.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Iterable
from urllib.parse import urlparse


def bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    return " ".join(str(value).strip().split()) or default


def safe_http_url(value: Any, *, allow_local: bool = True) -> str | None:
    text = normalize_text(value)
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    if not allow_local and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        return None
    return text.rstrip("/")


def safe_port(value: Any, *, default: int = 8000) -> int:
    return bounded_int(value, default=default, minimum=1, maximum=65535)


def parse_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().casefold()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def dedupe_stable(values: Iterable[Any], *, key=str) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        identity = key(value)
        if identity not in seen:
            seen.add(identity)
            result.append(value)
    return result


def clamp_timeout(value: Any, *, default: float = 30.0) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        return default
    if timeout != timeout or timeout in {float("inf"), float("-inf")}:
        return default
    return max(0.1, min(300.0, timeout))


def retry_delay(attempt: int, *, retry_after: Any = None) -> float:
    try:
        server_delay = max(0.0, float(retry_after))
    except (TypeError, ValueError):
        server_delay = 0.0
    exponent = bounded_int(attempt, default=0, minimum=0, maximum=8)
    return max(server_delay, min(30.0, 0.5 * (2**exponent)))


def sanitize_filename(value: Any, *, fallback: str = "download.bin") -> str:
    text = normalize_text(value, default=fallback).replace("\\", "/")
    name = PurePosixPath(text).name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return name or fallback


def safe_relative_path(value: Any) -> bool:
    text = normalize_text(value).replace("\\", "/")
    path = PurePosixPath(text)
    return bool(text) and not path.is_absolute() and ".." not in path.parts and "\x00" not in text


def capped_list(values: Iterable[Any], *, limit: int = 500) -> list[Any]:
    return list(values)[:bounded_int(limit, default=500, minimum=0, maximum=5000)]


def downloads_count(value: Any) -> int:
    return bounded_int(value, default=0, minimum=0, maximum=2_147_483_647)


def choose_primary_file(files: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [item for item in files if isinstance(item, dict) and item.get("url")]
    return next((item for item in candidates if item.get("primary")), candidates[0] if candidates else None)


def best_version(versions: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    values = [item for item in versions if isinstance(item, dict)]
    if not values:
        return None
    rank = {"release": 0, "beta": 1, "alpha": 2}
    return min(values, key=lambda item: (rank.get(str(item.get("version_type", "release")).casefold(), 3), str(item.get("date_published", ""))))


def dependency_key(source: Any, project_id: Any) -> str | None:
    source_text = normalize_text(source).casefold()
    project_text = normalize_text(project_id)
    return f"{source_text}:{project_text}" if source_text and project_text else None


def has_dependency_cycle(edges: dict[str, Iterable[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(child) for child in edges.get(node, ())):
            return True
        visiting.remove(node)
        visited.add(node)
        return False
    return any(visit(node) for node in edges)


def json_object(value: Any, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    fallback = {} if default is None else dict(default)
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    return parsed if isinstance(parsed, dict) else fallback


def redact_secrets(value: Any) -> str:
    text = str(value)
    return re.sub(r"(?i)(api[_-]?key|token|password|secret)(\s*[=:]\s*)[^,\s]+", r"\1\2[REDACTED]", text)


def truncate_error(value: Any, *, limit: int = 4000) -> str:
    return normalize_text(value, default="Unknown error")[:bounded_int(limit, default=4000, minimum=80, maximum=20000)]


def cache_expired(created_at: Any, *, ttl_seconds: float, now: datetime | None = None) -> bool:
    if not isinstance(created_at, datetime):
        return True
    current = now or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return (current - created_at).total_seconds() >= max(0.0, ttl_seconds)


def progress_message(step: Any, total: Any, message: Any) -> dict[str, Any]:
    total_value = bounded_int(total, default=1, minimum=1, maximum=100)
    return {"step": bounded_int(step, default=0, minimum=0, maximum=total_value), "total": total_value, "message": normalize_text(message, default="Working...")}


def confidence_score(*, evidence: int, risks: int, intent_match: int) -> int:
    return bounded_int(50 + evidence * 8 + intent_match * 12 - risks * 10, default=50, minimum=0, maximum=99)


def config_fingerprint(config: dict[str, Any]) -> str:
    import hashlib
    safe = {key: value for key, value in config.items() if key.casefold() not in {"api_key", "token", "password", "secret"}}
    return hashlib.sha256(json.dumps(safe, sort_keys=True, default=str).encode()).hexdigest()[:16]


def health_payload(*, provider: str, reachable: bool, detail: str = "") -> dict[str, Any]:
    return {"status": "ok" if reachable else "degraded", "ai": {"provider": normalize_text(provider, default="unknown"), "reachable": bool(reachable), "detail": normalize_text(detail, default="")}}
