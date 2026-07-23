# 1.9.0 deep audit

## Verified contracts

- Existing generation, compatibility, export, settings, loader-version and AI-model APIs remain present.
- Project construction and API serialization normalize 1.8.x rows and legacy objects with safe defaults.
- Editor changes require a stored plan id and explicit approval before apply.
- Approved edits use the existing typed dependency resolver and mark the project for review/export validation.
- Imported MRPack manifests are format/path/download validated; imported artifact metadata can be checked without a catalog lookup.
- Discovery uses the existing source registry and quality scoring, with typed loader boundaries.

## Release gates

Backend pytest and frontend build must be green. Import -> edit -> compatibility ->
export requires a real fixture because imported artifacts intentionally retain
manifest download metadata rather than inventing catalog project ids.

## Known boundary

Crash analysis is deliberately advisory in 1.9.0: it creates a repair report and
solution options, but never mutates a pack without an approved change plan.
Version-range-aware automatic conflict repair remains delegated to the existing
resolver contract and is not fabricated by the text analyzer.
