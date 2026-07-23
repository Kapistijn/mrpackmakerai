"""Dependency graph analysis for compatibility checks."""
from __future__ import annotations
from dataclasses import dataclass, field
from app.schemas.mod import ModDependency, ModEntry
REQUIRED_TYPES = {"required"}
@dataclass
class GraphNode:
    key: str
    mod: ModEntry
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)
class DependencyGraph:
    def __init__(self) -> None: self.nodes: dict[str, GraphNode] = {}
    @staticmethod
    def mod_key(mod: ModEntry) -> str: return f"{mod.source}:{mod.id}"
    @staticmethod
    def dependency_key(dep: ModDependency) -> str | None: return f"{dep.source or 'modrinth'}:{dep.project_id}" if dep.project_id else None
    def add_mod(self, mod: ModEntry) -> None:
        key = self.mod_key(mod); node = self.nodes.setdefault(key, GraphNode(key, mod))
        for dep in mod.dependencies:
            dep_key = self.dependency_key(dep)
            if dep_key and dep_key != key and dep_key not in node.dependencies: node.dependencies.append(dep_key)
        self._rebuild_reverse_edges()
    def _rebuild_reverse_edges(self) -> None:
        for node in self.nodes.values(): node.dependents.clear()
        for node in self.nodes.values():
            for dep_key in node.dependencies:
                if dep_key in self.nodes and node.key not in self.nodes[dep_key].dependents: self.nodes[dep_key].dependents.append(node.key)
    def _required_dependency(self, node: GraphNode, dep_key: str) -> bool: return any(self.dependency_key(dep) == dep_key and dep.dependency_type.casefold() in REQUIRED_TYPES for dep in node.mod.dependencies)
    def get_missing_required(self) -> list[str]: return sorted({dep_key for node in self.nodes.values() for dep_key in node.dependencies if self._required_dependency(node, dep_key) and dep_key not in self.nodes})
    def get_optional_missing(self) -> list[str]: return sorted({dep_key for node in self.nodes.values() for dep_key in node.dependencies if not self._required_dependency(node, dep_key) and dep_key not in self.nodes})
    def get_all_dependency_keys(self) -> set[str]: return {dep_key for node in self.nodes.values() for dep_key in node.dependencies}
    def get_conflicts(self) -> list[tuple[str, str]]:
        conflicts = set()
        for key, node in self.nodes.items():
            for dep in node.mod.dependencies:
                if dep.dependency_type.casefold() == "incompatible":
                    dep_key = self.dependency_key(dep)
                    if dep_key in self.nodes: conflicts.add(tuple(sorted((key, dep_key))))
        return sorted(conflicts)
    def get_cycles(self) -> list[list[str]]: return []
    def topological_order(self) -> list[str]: return sorted(self.nodes)
