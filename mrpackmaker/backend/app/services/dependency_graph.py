"""Safety limits and diagnostics for large dependency graphs."""
from __future__ import annotations
from dataclasses import dataclass

MAX_DEPENDENCY_DEPTH = 20
MAX_TOTAL_NODES = 5000

@dataclass(frozen=True)
class DependencyGraphLimits:
    max_depth: int = MAX_DEPENDENCY_DEPTH
    max_nodes: int = MAX_TOTAL_NODES

class DependencyGraphLimitError(RuntimeError):
    pass

class DependencyGraphGuard:
    def __init__(self, limits: DependencyGraphLimits | None = None) -> None:
        self.limits = limits or DependencyGraphLimits()
        self.nodes: set[str] = set()

    def visit(self, key: str, depth: int) -> bool:
        if key in self.nodes:
            return False
        if depth > self.limits.max_depth:
            raise DependencyGraphLimitError(f"Dependency graph exceeded safe depth ({self.limits.max_depth}). Possible circular dependency or broken metadata.")
        if len(self.nodes) >= self.limits.max_nodes:
            raise DependencyGraphLimitError(f"Dependency graph exceeded safe node limit ({self.limits.max_nodes}). Possible circular dependency or broken metadata.")
        self.nodes.add(key)
        return True
