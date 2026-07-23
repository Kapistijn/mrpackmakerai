# Changelog

## 1.7.3

Requirement-driven, personalized generation update.

### Added

- Persisted minimum/maximum mod counts and minimum download threshold in the
  project API and SQLite migration.
- Requirement parser now merges saved project limits with prompt intent, so a
  configured minimum such as 150 cannot be silently replaced by the default 40.
- Integrated requirement filtering and intent-weighted ranking into the real
  generation orchestrator, with hard theme exclusions before selection.
- Seeded candidate ranking and cross-source identity deduplication reduce
  popularity bias while producing varied, reproducible results.
- Manual/latest-stable loader resolution remains part of the generation path,
  with explicit failure when no compatible loader exists.
- Added regression coverage for persisted requirement overrides, horror policy,
  minimum 150 mods, scoring, duplicate filtering and loader selection.

### Selection policy

- User/theme match: 40%
- Compatibility: 20%
- Quality: 15%
- Downloads: 10%
- Performance: 10%
- Novelty: 5%

### Safety

- Horror excludes Cobblemon/Pokémon, technology, magic and farming unless the
  user explicitly asks for them.
- Generation refuses to silently return a smaller pack when the requested
  minimum cannot be met after compatibility and dependency resolution.

## 1.7.2.5

Restored the recursive dependency prompt contract.
