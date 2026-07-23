"""Regression coverage for the 1.8.3 generation crash.

Historically select_diverse expected list[ScoredMod] and dereferenced
item.mod, while the orchestrator passed the unwrapped list[ModEntry],
raising `'ModEntry' object has no attribute 'mod'` on every generation.
These tests pin the scoring layer to the real ModEntry model.
"""

from app.schemas.mod import ModEntry, ModHash
from app.services.mod_scoring import rank_mods, select_diverse
from app.services.requirements import parse_requirements


def _mod(mod_id: str, *, source: str = "modrinth", categories: list[str] | None = None, downloads: int = 1000) -> ModEntry:
    return ModEntry(
        id=mod_id,
        source=source,
        name=f"Mod {mod_id}",
        slug=f"mod-{mod_id}",
        summary="A test mod",
        downloads=downloads,
        categories=categories or [],
        file_name=f"{mod_id}.jar",
        download_url=f"https://example.invalid/{mod_id}.jar",
        hashes=ModHash(sha1="a" * 40),
    )


def test_select_diverse_accepts_real_modentry_objects():
    mods = [
        _mod("a", categories=["horror"]),
        _mod("b", categories=["storage"]),
        _mod("c", categories=["horror"]),
    ]
    selected = select_diverse(mods, 2)
    assert len(selected) == 2
    assert all(isinstance(item, ModEntry) for item in selected)
    # Diversity pass must cover distinct categories first.
    assert {c for item in selected for c in item.categories} == {"horror", "storage"}


def test_select_diverse_deduplicates_by_source_and_id():
    duplicate = _mod("dup", categories=["horror"])
    mods = [duplicate, _mod("dup", categories=["horror"]), _mod("other", categories=["mobs"])]
    selected = select_diverse(mods, 5)
    keys = {f"{item.source}:{item.id}" for item in selected}
    assert len(selected) == len(keys)


def test_orchestrator_scoring_shape_does_not_crash():
    """Replay the exact _gather_candidates -> select_diverse shape."""
    requirements = parse_requirements("horror pack", theme="horror")
    mods = [_mod(str(i), categories=["horror", "mobs"], downloads=1000 + i) for i in range(5)]
    ranked = rank_mods(mods, requirements, seed=1)
    candidates = [item.mod for item in ranked if item.score >= 0]
    assert candidates and all(isinstance(item, ModEntry) for item in candidates)
    selected = select_diverse(candidates, 3)
    assert selected and all(isinstance(item, ModEntry) for item in selected)
