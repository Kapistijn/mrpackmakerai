"""Dependency graph for modpack mods."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.mod import ModEntry, ModDependency


@dataclass
class GraphNode:
    key: str
    mod: ModEntry
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)


class DependencyGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}

    @staticmethod
    def mod_key(mod: ModEntry) -> str:
        return f"{mod.source}:{mod.id}"

    def add_mod(self, mod: ModEntry) -> None:
        key = self.mod_key(mod)
        if key not in self.nodes:
            self.nodes[key] = GraphNode(key=key, mod=mod)

        node = self.nodes[key]
        for dep in mod.dependencies:
            dep_key = self._dep_key(dep)
            if dep_key:
                if dep_key not in node.dependencies:
                    node.dependencies.append(dep_key)

    def _dep_key(self, dep: ModDependency) -> str | None:
        if not dep.project_id:
            return None
        source = dep.source or "modrinth"
        return f"{source}:{dep.project_id}"

    def get_missing_required(self) -> list[str]:
        missing: list[str] = []
        for key, node in self.nodes.items():
            for dep_key in node.dependencies:
                dep_mod = self._find_dep_mod(node.mod, dep_key)
                if dep_mod and dep_mod.dependency_type not in {"required", "embedded"}:
                    continue
                if dep_key not in self.nodes:
                    missing.append(dep_key)
        return list(dict.fromkeys(missing))

    def _find_dep_mod(self, mod: ModEntry, dep_key: str) -> ModDependency | None:
        for dep in mod.dependencies:
            if self._dep_key(dep) == dep_key:
                return dep
        return None

    def get_conflicts(self) -> list[tuple[str, str]]:
        conflicts: list[tuple[str, str]] = []
        for key, node in self.nodes.items():
            for dep in node.mod.dependencies:
                if dep.dependency_type == "incompatible":
                    dep_key = self._dep_key(dep)
                    if dep_key and dep_key in self.nodes:
                        conflicts.append((key, dep_key))
        return conflicts

    def get_all_dependency_keys(self) -> set[str]:
        keys: set[str] = set()
        for node in self.nodes.values():
            keys.update(node.dependencies)
        return keys
