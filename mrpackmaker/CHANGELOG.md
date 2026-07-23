# Changelog

## 1.8.7

Real intent analysis and a fully functional advanced configuration system. Every
advanced option now flows through the entire pipeline: Frontend -> API ->
Requirements -> Intent -> Scoring -> Generation -> .mrpack -> Compatibility. No
more options that are only stored.

### Added

- **Machine-readable intent analysis** (`intent_analysis.py`): turns a request
  like "as close to real life as possible" into a structured goal + categories +
  avoid list (realism survival: weather, seasons, temperature, food, farming,
  animals, physics, sound, lighting, survival, world_generation, immersion) with
  an optional AI enrichment that can never weaken the deterministic result.
- **Multi-factor quality scoring** (`quality_scoring.py`): every candidate is
  scored on intent match, realism, popularity, maintenance, compatibility,
  performance cost and dependency quality. Pure performance mods are only
  selected when performance mode is active, the FPS target requires it, or the
  RAM budget demands it.
- **Pack profile** (`pack_profile.py`): maps RAM / FPS / shader / performance
  preference into concrete directives (content-mod budget, heavy-worldgen gate,
  shader mode + quality, performance floor).
- **Extended .mrpack writer**: emits an `overrides/` tree (config, options.txt,
  shaderpacks/ and resourcepacks/ folders) plus a `pack_info.json` descriptor,
  and supports shaderpack/resourcepack install paths, not just `mods/`.
- **Pre-export self-check** (`self_check.py`): verifies every requested intent
  category is covered and re-searches the candidate pool to fill gaps; strict
  mode blocks export until requirements are satisfied.
- **Advanced Configuration** in the New Project screen: RAM, FPS, shaders,
  shader quality, resource-pack support, min/max/required/forbidden mods and AI
  creativity/strictness/discovery depth, all persisted and wired to generation.

### Improved

- Dependency repair now reports the specific unresolved dependency and a
  concrete suggestion instead of an opaque "failed after 5 passes".
- Persisted advanced project fields via an additive SQLite migration.
- Added a full-flow test for "realistic survival modpack with shaders, 16GB RAM,
  120 FPS target" plus targeted tests for RAM, shaders, FPS, intent, export
  contents, self-check and dependency repair.

## 1.7.3.2

Personalization and generation-quality hardening on top of 1.7.3.

### Improved

- Added category-diverse candidate selection so large packs cover multiple
  requested content areas before filling by score.
- Connected persisted project minimum/maximum mod counts and download limits to
  the real orchestrator, not just the API schema.
- Fixed the generation minimum-count branch so it cannot silently use a falsey
  conditional expression or fall back to a smaller pack.
- Added explicit failure messages when the requested minimum cannot be met after
  theme filtering, compatibility checks and dependency resolution.
- Preserved prompt-level download thresholds when the project setting is zero.
- Added regression tests for diversity and threshold precedence.
- Bumped backend and frontend to 1.7.3.2.

### Quality contract

The generator now either produces a requirement-matched result or reports why
it cannot. It no longer quietly returns a popularity-ranked partial pack when a
user has set a hard minimum.

## 1.7.3

Requirement parser, hard theme policy, intent-weighted scoring, seeded ranking,
manual loader resolution and persisted requirement settings.
