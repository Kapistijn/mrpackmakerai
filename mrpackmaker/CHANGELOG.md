# Changelog

## 2.5.3

- Fixed startup import crash by restoring `ModSearchResponse`.
- Fixed Windows MRPack permission errors by closing upload temp files before parsing.
- Added per-package installer progress such as `Installing fastapi (1/12)`, with spinner and full logs.
- Added live server logs in `start.bat` and preserved `startup-error.log`.
- Added Forge dependency diagnostics and non-fatal dropped-mod reporting where unresolved dependencies make a mod incompatible.
- Fixed stale generation streams after cancel and restart.

## 2.5.2

- Fixed the post-install startup crash caused by the missing `ModSearchResponse` schema.
- Added an application-import regression test that imports every registered route.
- Restored the typed `/api/mods/search` response contract.

## 2.5.1

- Restored the PowerShell spinner/loading screen.
- Added explicit installer failure output and backend import checks.

## 2.5.0

- Added audited boundary hardening and deterministic regression coverage.

## 2.1.2.1

- Restored deterministic CI installation and removed accidental lockfile/CI churn from the startup hotfix.

## 2.1.2

- Fixed the crash immediately after installer step 7/7.
- Corrected backend import resolution from `backend/run.py`.
- Made `start.bat` use absolute paths and verify the backend import before opening the browser.
- Added `startup-error.log` output and preserved the real traceback when the server exits.

## 2.1.0

- Added multi-round AI reasoning, per-mod memory, critique, confidence, and alternatives.
- Added QoL intent signals and bounded paginated candidate discovery.
- Added support for generation targets up to 500 mods.
