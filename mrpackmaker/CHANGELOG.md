# Changelog

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
