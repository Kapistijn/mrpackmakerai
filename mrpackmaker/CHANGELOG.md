# Changelog

## 1.7

Public-release hardening and product foundation.

### User-facing improvements

- Added a loader-version endpoint backed by Modrinth compatible metadata.
- Added loader-version selection to the new-project wizard, with stable release
  prioritization, refresh, loading and error states.
- Persisted the selected loader version through the API and additive SQLite
  migration.
- Export now honors a pinned loader version instead of silently replacing it
  with the resolver's latest version.
- Fixed the frontend delete-project false failure caused by parsing an empty
  HTTP 204 response as JSON.
- Delete now removes a generated `.mrpack` only when it is safely inside the
  configured output directory.

### AI and selection foundation

- Added a structured prompt pipeline that normalizes sparse requests, extracts
  minimum/maximum counts and exclusions, adds project invariants, and produces
  a safe generation system prompt.
- Added regression coverage for prompt expansion, safe empty prompts, and
  cross-source identity deduplication.
- Existing catalog deduplication is retained so equivalent Modrinth and
  CurseForge projects collapse to one best downloadable entry.

### Scope note

The compatibility dashboard, per-mod explanations, advanced gameplay controls,
multiplayer/server/shader profiles, and provider-backed prompt optimizer are
planned follow-up slices. They should be added behind tested API contracts,
not rushed into a single release branch.

## 1.6.3

Reliability and correctness release for the generation pipeline.

- Correct Modrinth loader facet regression coverage.
- Cross-catalog identity normalization and deduplication.
- Regression tests for richer-entry selection and distinct projects.
- Backend and frontend version metadata bumped to 1.6.3.

## 1.6.2

Generation, provider, CurseForge selection, startup, and cache reliability fixes.
