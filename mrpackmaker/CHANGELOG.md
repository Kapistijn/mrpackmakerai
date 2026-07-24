# Changelog

## 2.5.4 Parts 4-6

- Replaced raw JSON AI editor output with a readable plan card showing goal, reason, risk, benefits, performance, compatibility, realism, dependencies and alternatives.
- Kept technical payloads available only under an expandable Developer Details section.
- Editor proposals now call the configured AI provider with a typed schema when available.
- Deterministic rules remain available as an explicitly labelled fallback when AI is unavailable; no fallback is presented as AI output.
- Added honest fallback metadata and actionable provider failure details.
- Added editable AI controls for top-p sampling and retry attempts, persisted through the settings API and used by the provider.
- Added provider health and model discovery controls to the AI settings surface.
- Added regression tests for typed plans, raw-JSON visibility, fallback honesty and settings persistence contracts.

## 2.5.5

- Fixed the second Windows PowerShell startup bug: nested quotes in the Python preflight command were stripped before Python received them, turning `print("Backend import OK")` into invalid `print(Backend` syntax. The preflight now uses quote-free Python code, `import app.main; print(1)`, and prints the friendly success message from PowerShell.
- Added a clear validation error when `MRPACK_PORT` is not an integer from 1 through 65535.
- Added a preflight check for the backend launcher file so a broken or incomplete download fails with a useful message instead of a traceback.
- Bumped backend, frontend, installer, and launcher metadata to 2.5.5.
- Added regression coverage for the PowerShell argument-quoting failure, port bounds, missing launcher detection, and version alignment.

## 2.5.4

- Fixed the launcher crash `The ampersand (&) character is not allowed` (`AmpersandNotAllowed`). Startup now runs from a real PowerShell file invoked with `-File` and separate process logging.
- Added single-source version reporting, richer installer diagnostics and launch hardening.
