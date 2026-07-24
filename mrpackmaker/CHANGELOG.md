# Changelog

## 2.5.5

- Fixed the second Windows PowerShell startup bug: nested quotes in the Python preflight command were stripped before Python received them, turning `print("Backend import OK")` into invalid `print(Backend` syntax. The preflight now uses quote-free Python code, `import app.main; print(1)`, and prints the friendly success message from PowerShell.
- Added a clear validation error when `MRPACK_PORT` is not an integer from 1 through 65535.
- Added a preflight check for the backend launcher file so a broken or incomplete download fails with a useful message instead of a traceback.
- Bumped backend, frontend, installer, and launcher metadata to 2.5.5.
- Added regression coverage for the PowerShell argument-quoting failure, port bounds, missing launcher detection, and version alignment.

## 2.5.4

- Fixed the launcher crash `The ampersand (&) character is not allowed` (`AmpersandNotAllowed`). `start.bat` piped the server through PowerShell inline as `2^>^&1 | Tee-Object`, but cmd does not strip the `^` carets inside a double-quoted `-Command`, so PowerShell received them verbatim and refused to start. Startup now runs from a real `scripts/start.ps1` invoked with `-File`, so `2>&1 | Tee-Object` parses normally and live logs stream correctly.
- Fixed the stale frontend version (`package.json` was still `2.5.0` while the backend was `2.5.3`).
- Added a single source of truth for the version (`app.__version__`) used by the API, `/api/health`, the installer, and the launcher, so versions can no longer drift.
- Installer now prints the detected Python and Node versions (`Python check: ...   Node check: ...`) and an explicit `done` marker for the virtual-environment and config steps.
- Installer and launcher now show a clear version banner.
- Launcher startup banner now shows the version, detected Python version, host, port, and target URL, plus a `Press Ctrl+C to stop` hint.
- `/api/health` now reports the running application version for easier diagnostics.
- Startup log rotation (>5 MB) and clean live log streaming carried into `start.ps1`.
- Added regression tests asserting the ampersand crash pattern is gone, the launcher streams logs cleanly, and the version is single-sourced and bumped.

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
