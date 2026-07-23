# Changelog

## 1.7.3

Requirement-driven generation update.

### Added

- Deterministic requirement parser for minimum/maximum mod counts, minimum
  downloads, multiplayer intent, requested content and forbidden features.
- Hard theme policy: horror generation excludes Cobblemon/Pokémon, technology,
  magic and farming unless explicitly requested.
- Intent-weighted scoring: user match 40%, compatibility 20%, quality 15%,
  downloads 10%, performance 10%, novelty 5%.
- Seeded ranking API for reproducible but varied generations.
- Manual/latest-stable loader resolver with clear incompatibility errors.
- Regression coverage for horror filtering, 150-mod requirements, scoring,
  loader pinning and invalid manual versions.

### Correctness

- Theme exclusions are evaluated before ranking, so unrelated popular projects
  cannot enter a hard horror pool merely because they are highly downloaded.
- Minimum mod requirements are represented as structured data instead of being
  left as unparsed prose.
- Loader resolution distinguishes manual selection from latest-stable fallback.

### Quality note

The parser, scoring and loader resolver are isolated deterministic services so
catalog clients and AI provider behavior stay decoupled. CI remains the source
of truth for the complete suite and frontend build.

## 1.7.2.5

Restored the recursive dependency prompt contract.
