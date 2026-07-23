from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common import CompatibilityStatus, Loader, to_json_safe


@dataclass(frozen=True)
class CompatibilityIssue:
    code: str
    message: str
    fatal: bool = False

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError("issue code and message are required")

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({"code": self.code, "message": self.message, "fatal": self.fatal})


@dataclass(frozen=True)
class MeasuredMetrics:
    min_ram_mb: int | None = None
    recommended_ram_mb: int | None = None
    java_version: int | None = None

    def __post_init__(self) -> None:
        values = (self.min_ram_mb, self.recommended_ram_mb, self.java_version)
        if any(value is not None and value < 0 for value in values):
            raise ValueError("metrics cannot be negative")
        if self.min_ram_mb is not None and self.recommended_ram_mb is not None and self.recommended_ram_mb < self.min_ram_mb:
            raise ValueError("recommended RAM cannot be below minimum RAM")

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({"min_ram_mb": self.min_ram_mb, "recommended_ram_mb": self.recommended_ram_mb, "java_version": self.java_version})


@dataclass(frozen=True)
class CompatibilityReport:
    minecraft_version: str
    loader: Loader
    loader_version: str | None = None
    issues: tuple[CompatibilityIssue, ...] = ()
    metrics: MeasuredMetrics = field(default_factory=MeasuredMetrics)
    evaluated: bool = False

    def __post_init__(self) -> None:
        if not self.minecraft_version.strip():
            raise ValueError("minecraft_version is required")
        if not isinstance(self.loader, Loader):
            object.__setattr__(self, "loader", Loader.from_str(str(self.loader)))
        object.__setattr__(self, "issues", tuple(self.issues))

    @property
    def status(self) -> CompatibilityStatus:
        if not self.evaluated:
            return CompatibilityStatus.UNKNOWN
        return CompatibilityStatus.INCOMPATIBLE if any(issue.fatal for issue in self.issues) else CompatibilityStatus.COMPATIBLE

    @property
    def is_exportable(self) -> bool:
        return self.evaluated and self.status is not CompatibilityStatus.INCOMPATIBLE

    def with_issue(self, issue: CompatibilityIssue) -> "CompatibilityReport":
        return CompatibilityReport(self.minecraft_version, self.loader, self.loader_version, (*self.issues, issue), self.metrics, self.evaluated)

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({"minecraft_version": self.minecraft_version, "loader": self.loader, "loader_version": self.loader_version, "issues": self.issues, "metrics": self.metrics, "evaluated": self.evaluated, "status": self.status})
