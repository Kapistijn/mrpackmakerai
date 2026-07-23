"""Dependency graph analysis with large-pack safety limits."""
from __future__ import annotations
from dataclasses import dataclass, field
from app.schemas.mod import ModDependency, ModEntry
REQUIRED_TYPES = {"required"}
MAX_DEPENDENCY_DEPTH = 20
MAX_TOTAL_NODES = 5000
@dataclass
class GraphNode:
    key: str
    mod: ModEntry
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)
class DependencyGraphLimitError(RuntimeError): pass
@dataclass(frozen=True)
class DependencyGraphLimits:
    max_depth: int = MAX_DEPENDENCY_DEPTH
    max_nodes: int = MAX_TOTAL_NODES
class DependencyGraphGuard:
    def __init__(self, limits: DependencyGraphLimits | None = None) -> None:
        self.limits = limits or DependencyGraphLimits(); self.nodes: set[str] = set()
    def visit(self, key: str, depth: int) -> bool:
        if key in self.nodes: return False
        if depth > self.limits.max_depth: raise DependencyGraphLimitError(f"Dependency graph exceeded safe depth ({self.limits.max_depth}). Possible circular dependency or broken metadata.")
        if len(self.nodes) >= self.limits.max_nodes: raise DependencyGraphLimitError(f"Dependency graph exceeded safe node limit ({self.limits.max_nodes}). Possible circular dependency or broken metadata.")
        self.nodes.add(key); return True
class DependencyGraph:
    """Legacy graph API retained for compatibility and export validation."""
    def __init__(self, limits: DependencyGraphLimits | None = None) -> None:
        self.nodes: dict[str, GraphNode] = {}; self.guard = DependencyGraphGuard(limits)
    @staticmethod
    def mod_key(mod: ModEntry) -> str: return f"{mod.source}:{mod.id}"
    @staticmethod
    def dependency_key(dep: ModDependency) -> str | None: return f"{dep.source or 'modrinth'}:{dep.project_id}" if dep.project_id else None
    def add_mod(self, mod: ModEntry) -> None:
        key=self.mod_key(mod)
        if key not in self.nodes: self.guard.visit(key, 0)
        node=self.nodes.setdefault(key, GraphNode(key,mod)); node.mod=mod
        for dep in mod.dependencies:
            dep_key=self.dependency_key(dep)
            if dep_key and dep_key != key and dep_key not in node.dependencies: node.dependencies.append(dep_key)
        self._rebuild_reverse_edges()
    def _rebuild_reverse_edges(self) -> None:
        for node in self.nodes.values(): node.dependents.clear()
        for node in self.nodes.values():
            for dep_key in node.dependencies:
                dependency=self.nodes.get(dep_key)
                if dependency and node.key not in dependency.dependents: dependency.dependents.append(node.key)
    def _required_dependency(self,node:GraphNode,dep_key:str)->bool:
        return any(self.dependency_key(dep)==dep_key and dep.dependency_type.casefold() in REQUIRED_TYPES for dep in node.mod.dependencies)
    def get_missing_required(self)->list[str]: return sorted({dep for node in self.nodes.values() for dep in node.dependencies if self._required_dependency(node,dep) and dep not in self.nodes})
    def get_optional_missing(self)->list[str]: return sorted({dep for node in self.nodes.values() for dep in node.dependencies if not self._required_dependency(node,dep) and dep not in self.nodes})
    def get_all_dependency_keys(self)->set[str]: return {dep for node in self.nodes.values() for dep in node.dependencies}
    def get_conflicts(self)->list[tuple[str,str]]:
        conflicts=set()
        for key,node in self.nodes.items():
            for dep in node.mod.dependencies:
                if dep.dependency_type.casefold() == 'incompatible':
                    dep_key=self.dependency_key(dep)
                    if dep_key and dep_key in self.nodes: conflicts.add(tuple(sorted((key,dep_key))))
        return sorted(conflicts)
    def get_cycles(self)->list[list[str]]:
        cycles=set(); visiting=[]; active=set(); visited=set()
        def canonical(path):
            ring=path[:-1]; rotations=[tuple(ring[i:]+ring[:i]) for i in range(len(ring))]; return min(rotations)
        def visit(key):
            if key in active: cycles.add(canonical(visiting[visiting.index(key):]+[key])); return
            if key in visited: return
            active.add(key); visiting.append(key)
            for dep in sorted(self.nodes[key].dependencies):
                if dep in self.nodes: visit(dep)
            visiting.pop(); active.remove(key); visited.add(key)
        for key in sorted(self.nodes): visit(key)
        return [list(cycle) for cycle in sorted(cycles)]
    def topological_order(self)->list[str]:
        cycles=self.get_cycles()
        if cycles: raise ValueError(f"Dependency cycle detected: {' -> '.join(cycles[0])}")
        indegree={key:0 for key in self.nodes}
        for node in self.nodes.values():
            for dep in node.dependencies:
                if dep in indegree: indegree[node.key]+=1
        ready=sorted(key for key,degree in indegree.items() if degree==0); result=[]
        while ready:
            key=ready.pop(0); result.append(key)
            for dependent in sorted(self.nodes[key].dependents):
                indegree[dependent]-=1
                if indegree[dependent]==0: ready.append(dependent); ready.sort()
        if len(result)!=len(self.nodes): raise ValueError('Dependency graph could not be ordered')
        return result
