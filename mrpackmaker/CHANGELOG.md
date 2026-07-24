# Changelog

## 2.1.2

- Fixed the crash immediately after installer step 7/7.
- Corrected backend import resolution from `backend/run.py`.
- Made `start.bat` use absolute paths and verify the backend import before opening the browser.
- Added `startup-error.log` output and preserved the real traceback when the server exits.
- Aligned frontend and backend release metadata to 2.1.2.

## 2.1.1

- Fixed Windows startup after installation.
- Added startup diagnostics and launcher exit-code handling.

## 2.1.0

- Added multi-round AI reasoning, per-mod memory, critique, confidence, and alternatives.
- Added QoL intent signals and bounded paginated candidate discovery.
- Added support for generation targets up to 500 mods.

## 1.9.0

AI modpack development environment layered on top of the stable 1.8.x pipeline.

- Added approval-gated AI Modpack Editor with natural-language change planning.
- Added direct catalog discovery and ranked recommendations using the existing resolver/scoring boundaries.
- Added additive MRPack import that creates an editable project from `modrinth.index.json`.
- Added crash analysis, repair reports and conflict-resolution options.
- Added additive change history, AI request, import and repair-report persistence.
- Added editor API and frontend page without replacing the existing generator/builder flow.
- Added regression coverage for import, edit planning, repair, conflicts and legacy projects.

## 1.8.8

Pipeline integrity fixes for the 1.8.7 review blockers.
