# Changelog

## 1.7.2.1

Hotfix and optimization release for the 1.7.2 architecture update.

### Fixed

- Fixed JSON-mode regression tests and real local-provider compatibility when
  an explicit model is configured but the provider does not expose `/models`.
  Chat generation now uses the configured model directly; model discovery stays
  reserved for health checks and auto-selection.
- Fixed normalized prompt output so the Minecraft version is explicit in the
  generated brief (`Minecraft 1.20.1`), preventing ambiguous AI context and
  restoring the release regression test.

### Optimized

- Removed an unnecessary model-discovery round trip from the normal configured
  model path, reducing local AI latency and avoiding unsupported gateway routes.
- Kept provider retries bounded and SDK retries disabled, preventing duplicate
  retry storms.
- Added regression coverage that asserts explicit-model chat works with a
  completions-only fake provider and that normalized prompts preserve version
  and loader context.
- Updated backend and frontend version metadata to 1.7.2.1.

## 1.7.2

Staged prompt intent pipeline, cycle-safe dependency graph, secure export
validation, duplicate/hash checks, and release CI hardening.
