"""Dependency graph analysis for modpack resolution and compatibility checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.mod import ModDependency, ModEntry


REQUIRED_TYPES = {"required", "embedded"}


@dataclass
class GraphNode:
    key: str
    mod: ModEntry
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)


class DependencyGraph:
    """Directed graph with explicit missing, conflict and cycle analysis.

    Edges point from a mod to its dependencies. All public traversals are
    deterministic, which makes compatibility reports and generated manifests
    reproducible across runs and providers.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}

    @staticmethod
    def mod_key(mod: ModEntry) -> str:
        return f"{mod.source}:{mod.id}"

    @staticmethod
    def dependency_key(dep: ModDependency) -> str | None:
        if not dep.project_id:
            return None
        return f"{dep.source or 'modrinth'}:{dep.project_id}"

    def add_mod(self, mod: ModEntry) -> None:
        key = self.mod_key(mod)
        node = self.nodes.setdefault(key, GraphNode(key=key, mod=mod))
        for dep in mod.dependencies:
            dep_key = self.dependency_key(dep)
            if not dep_key or dep_key == key:
                continue
            if dep_key not in node.dependencies:
                node.dependencies.append(dep_key)
            # The dependent may not have been added yet. Link it when it is.
            dependency_node = self.nodes.get(dep_key)
            if dependency_node and key not in dependency_node.dependents:
                dependency_node.dependents.append(key)
        self._rebuild_reverse_edges()

    def _rebuild_reverse_edges(self) -> None:
        for node in self.nodes.values():
            node.dependents.clear()
        for node in self.nodes.values():
            for dep_key in node.dependencies:
                dependency_node = self.nodes.get(dep_key)
                if dependency_node and node.key not in dependency_node.dependents:
                    dependency_node.dependents.append(node.key)

    def _required_dependency(self, node: GraphNode, dep_key: str) -> bool:
        return any(self.dependency_key(dep) == dep_key and dep.dependency_type in REQUIRED_TYPES for dep in node.mod.dependencies)

    def get_missing_required(self) -> list[str]:
        missing = {
            dep_key
            for node in self.nodes.values()
            for dep_key in node.dependencies
            if self._required_dependency(node, dep_key) and dep_key not in self.nodes
        }
        return sorted(missing)

    def get_optional_missing(self) -> list[str]:
        missing = {
            dep_key
            for node in self.nodes.values()
            for dep_key in node.dependencies
            if not self._required_dependency(node, dep_key) and dep_key not in self.nodes
        }
        return sorted(missing)

    def get_all_dependency_keys(self) -> set[str]:
        return {dep_key for node in self.nodes.values() for dep_key in node.dependencies}

    def get_conflicts(self) -> list[tuple[str, str]]:
        conflicts: set[tuple[str, str]] = set()
        for key, node in self.nodes.items():
            for dep in node.mod.dependencies:
                if dep.dependency_type != "incompatible":
                    continue
                dep_key = self.dependency_key(dep)
                if dep_key and dep_key in self.nodes:
                    conflicts.add(tuple(sorted((key, dep_key))))
        return sorted(conflicts)

    def get_cycles(self) -> list[list[str]]:
        """Return canonical dependency cycles without recursion depth risk."""
        cycles: set[tuple[str, ...]] = set()
        visiting: list[str] = []
        active: set[str] = set()
        visited: set[str] = set()

        def canonical(path: list[str]) -> tuple[str, ...]:
            ring = path[:-1]
            rotations = [tuple(ring[i:] + ring[:i]) for i in range(len(ring))]
            return min(rotations)

        def visit(key: str) -> None:
            if key in active:
                start = visiting.index(key)
                cycles.add(canonical(visiting[start:] + [key]))
                return
            if key in visited:
                return
            active.add(key)
            visiting.append(key)
            for dep_key in sorted(self.nodes[key].dependencies):
                if dep_key in self.nodes:
                    visit(dep_key)
            visiting.pop()
            active.remove(key)
            visited.add(key)

        for key in sorted(self.nodes):
            visit(key)
        return [list(cycle) for cycle in sorted(cycles)]

    def topological_order(self) -> list[str]:
        """Return dependencies first, or raise a useful error for cycles."""
        cycles = self.get_cycles()
        if cycles:
            raise ValueError(f"Dependency cycle detected: {' -> '.join(cycles[0])}")
        indegree = {key: 0 for key in self.nodes}
        for node in self.nodes.values():
            for dep_key in node.dependencies:
                if dep_key in indegree:
                    indegree[node.key] += 1
        ready = sorted(key for key, degree in indegree.items() if degree == 0)
        result: list[str] = []
        while ready:
            key = ready.pop(0)
            result.append(key)
            for dependent in sorted(self.nodes[key].dependents):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    ready.append(dependent)
                    ready.sort()
        if len(result) != len(self.nodes):
            raise ValueError("Dependency graph could not be ordered")
        return result
