# Changelog

## 2.1.2

- Fixed the crash immediately after installer step 7/7.
- Corrected backend import resolution from `backend/run.py`.
- Made `start.bat` use absolute paths and verify the backend import before opening the browser.
- Added `startup-error.log` output and preserved the real traceback when the server exits.

## 2.1.1

- Fixed Windows startup after installation.
- Added startup diagnostics and launcher exit-code handling.

## 2.1.0

- Added multi-round AI reasoning, per-mod memory, critique, confidence, and alternatives.
- Added QoL intent signals and bounded paginated candidate discovery.
- Added support for generation targets up to 500 mods.
