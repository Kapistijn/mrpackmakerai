# Changelog

## 1.7.2

Architecture and quality update for the path toward a stable v1.0.

### AI pipeline

- Added staged intent extraction for themes, gameplay styles, explicit
  preferences, exclusions, counts, multiplayer and performance signals.
- Added consistency validation for impossible mod-count bounds and competing
  themes.
- Prompt rendering keeps the original user wording out of the generation system
  prompt and adds stable project invariants, dependency and deduplication rules.
- AI transport now uses bounded exponential retries for transient failures,
  deterministic model discovery, and zero SDK-level retry duplication.

### Dependency and export correctness

- Refactored dependency graphs with deterministic traversal, reverse edges,
  required/optional separation, canonical cycle detection and topological order.
- Export validation now blocks cross-catalog duplicate identities, duplicate
  hashes, insecure HTTP downloads, unsafe filenames, missing checksums and
  missing file sizes.
- CI now runs Python compilation checks and triggers on release branches.

### Tests

- Added regression tests for dependency order, cycles, optional dependencies,
  prompt intent/validation, prompt privacy, duplicate hashes and export safety.
- Backend and frontend versions are 1.7.2.

## 1.7.1

Compatibility metrics, duplicate blockers and release-readiness verification.

## 1.7

Loader-version selection, pinned export, safe deletion, prompt foundation and
cross-catalog deduplication.
