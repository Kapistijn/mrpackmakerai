# Changelog

## 1.7.1

Release-readiness verification pass focused on correctness, compatibility
visibility, and preventing silent runtime assumptions.

### Added

- Compatibility metrics contract covering Minecraft/loader identity, pinned
  loader version, dependency counts, duplicate projects, missing files/libraries,
  incompatibilities, performance score, RAM/CPU/startup estimates, and download
  size. Unknown machine-specific values remain null instead of pretending to be
  measured.
- Duplicate projects are now explicit compatibility errors, not merely hidden
  during generation.
- Regression tests cover cross-source identity, metrics nullability, enum
  serialization, and pinned loader export behavior.

### Hardened

- Release metadata is now 1.7.1 for both backend and frontend.
- The previous 1.7 loader picker, additive migration, safe deletion, prompt
  pipeline, cross-catalog deduplication, and export pinning remain intact.

### Verification note

CI remains the source of truth for the full pytest suite and frontend build.
This branch adds tests for the new behavior but does not claim a green result
until GitHub Actions reports it.

## 1.7

Public-release hardening and product foundation.

- Loader-version picker and persistence.
- Structured prompt normalization.
- Cross-catalog deduplication.
- Safe project deletion and pinned export.

## 1.6.3

Reliability and correctness release for the generation pipeline.

## 1.6.2

Generation, provider, CurseForge selection, startup, and cache reliability fixes.
