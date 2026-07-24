# Changelog

## 2.5.1

- Restored the PowerShell spinner/loading screen for long install steps.
- Kept the installer window open after success or failure instead of disappearing.
- Added a backend import gate before frontend installation/build, so the real crash is shown at the failing step.
- Preserved full pip/npm output in install-log.txt while keeping the console readable.
- Added explicit exit-code checks for venv, pip, backend import, npm, and Vite.

## 2.5.0

- Added audited boundary hardening and deterministic regression coverage.
