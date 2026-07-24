# Changelog

## 2.5.0

### Hardening fixes

- Added 20 deterministic boundary fixes covering invalid ports, URLs, booleans, limits, timeouts, retry delays, filenames, traversal, catalog metadata, dependency keys/cycles, malformed JSON, secret redaction, error truncation, cache expiry, and progress bounds.
- Added regression tests for every hardening rule, including empty provider/catalog responses and corrupted configuration values.
- Kept startup/import diagnostics from 2.1.2.1 and verified both backend and frontend CI paths.

### Improvements

- Stable de-duplication helper for catalog and generated lists.
- Deterministic config fingerprint that excludes secrets.
- Degraded health payload when the AI provider is unreachable.
- Evidence/risk confidence scoring helper for AI explanations.
- Bounded progress payloads for reliable UI consumers.

## 2.1.2.1

- Restored deterministic CI installation and removed the accidental lockfile/CI churn from the startup hotfix.

## 2.1.2

- Fixed the crash immediately after installer step 7/7.
- Corrected backend import resolution from `backend/run.py`.
- Made `start.bat` use absolute paths and verify the backend import before opening the browser.
- Added `startup-error.log` output and preserved the real traceback when the server exits.
