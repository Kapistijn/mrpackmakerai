# Changelog

## 2.5.6

- Consolidates the complete Parts 1-13 implementation into one release branch; duplicate PRs #51-#54 are superseded by the canonical release PR.
- Aligns backend, frontend, installer and Windows launcher version metadata to 2.5.6.
- Part 7 workers now use persisted project defaults, support per-run overrides, perform real concurrent Modrinth and CurseForge searches, coalesce identical requests, deduplicate cross-source projects and return explicit validation evidence.
- Existing projects receive an additive `worker_count` database migration with a safe default of 4.
- Advanced project settings remain closed by default and expose worker count without hiding the rest of the modpack configuration.
- Startup uses explicit stdout/stderr capture, so normal INFO logs do not become PowerShell exceptions.
- CI verification remains required for pytest, frontend build and Windows PowerShell parsing.

## 2.5.4 Parts 11-13

- Added the multi-worker generation page, release verification gate and regression coverage.

## 2.5.4 Parts 8-10

- Added evidence-based merge scoring, reusable bounded async coalescing cache and repository audit.

## 2.5.4 Parts 4-6

- Added structured AI plans, honest deterministic fallbacks and real provider tuning controls.

## 2.5.4 Parts 1-3

- Added clean Windows startup, stable navigation and in-page Intelligence MRPack import.
