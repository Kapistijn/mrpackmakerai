# Changelog

## 1.7.2.2

Regression hotfix for the 1.7.2 AI prompt pipeline.

### Fixed

- Restored the canonical duplicate-detection constraint to every optimized
  prompt: `deduplicate by project identity, slug, name, file and hashes`.
- This fixes the release regression where Dutch prompts containing "geen dubbele
  mods" detected the intent but failed to emit the downstream constraint.
- Export and generation behavior remains unchanged; this is a prompt-contract
  fix, not a workaround.
- Bumped backend and frontend metadata to 1.7.2.2.

### Verification

The failing regression is now covered by the existing prompt test and the
canonical constraint is exported as a named constant to prevent wording drift.

## 1.7.2.1

Fixed explicit-model local AI compatibility and ambiguous Minecraft-version
prompt output.

## 1.7.2

Staged prompt intent pipeline, cycle-safe dependency graph, secure export
validation, duplicate/hash checks, and release CI hardening.
