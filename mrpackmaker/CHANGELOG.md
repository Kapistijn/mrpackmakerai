# Changelog

## 1.7.2.5

Prompt-contract regression hotfix.

### Fixed

- Restored the exact dependency requirement expected by the generation prompt:
  `resolve required dependencies recursively`.
- Introduced `DEPENDENCY_CONSTRAINT` as a single source of truth so wording
  cannot drift between implementation and regression tests.
- Added a dedicated regression test using the complete failing horror prompt.
- Bumped backend and frontend metadata to 1.7.2.5.

## 1.7.2.4

Final boss-content prompt regression fix with alias-aware intent matching.

## 1.7.2.3

Restored content-priority propagation for boss and other gameplay intent.

## 1.7.2.2

Restored the canonical duplicate-detection prompt constraint.
