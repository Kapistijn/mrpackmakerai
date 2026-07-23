"""Small, serializable generation diagnostics for the UI and event log."""
from __future__ import annotations
from dataclasses import dataclass, field
from time import monotonic

@dataclass
class GenerationDiagnostics:
    requested: int | None = None
    found: int = 0
    skipped: int = 0
    reasons: dict[str, int] = field(default_factory=dict)
    started_at: float = field(default_factory=monotonic)

    def skip(self, reason: str) -> None:
        self.skipped += 1
        self.reasons[reason] = self.reasons.get(reason, 0) + 1

    def snapshot(self) -> dict[str, object]:
        return {"mods_requested": self.requested, "mods_found": self.found, "skipped": self.skipped, "reasons": dict(self.reasons), "generation_seconds": round(monotonic() - self.started_at, 2)}
