# MrPackMaker 2.0.0

## Release scope

This release consolidates the verified AI modpack intelligence and production-hardening work into one release line. It preserves the existing 1.8.x, 1.9.x, and 2.x flows.

## Verified fixes and improvements

- Backend-owned generation validation flow: dependency repair, compatibility validation, analysis persistence, commit, then completion event.
- Safe MRPack import/export path validation with traversal protection and mixed relative instance folders.
- Modpack quality, realism, immersion, performance, compatibility, and content-balance analysis.
- Synergy analysis and non-blocking world-generation overlap warnings.
- Performance estimation for RAM, VRAM, CPU cores, FPS range, shaders, particles, entities, and world generation.
- Hardware-aware planning with CPU/GPU capability tiers, RAM, resolution, refresh rate, target FPS, and shader preference.
- Dependency graph diagnostics with cycles, missing dependencies, conflicts, optional/recommended edges, chains, causes, fixes, and confidence.
- Approval-gated AI editing with pre-change snapshots and rollback validation.
- Versioned pack-analysis history and snapshot history.
- Per-mod explanations, reputation signals, variants, recommendations, and intelligence dashboard support.
- Quick generation remains available when AI is unavailable.
- Modrinth and CurseForge provider boundaries remain explicit, with retry and rate-limit handling inherited from the existing clients.
- Legacy export-validation contracts remain compatible while unsafe filenames and install paths fail closed.
- Late SSE subscribers can receive the retained terminal generation event.

## Verification policy

This release deliberately does not claim an arbitrary number of critical bugs or AI improvements. Every item above maps to implemented code and regression coverage. Merge only after the release branch reports green backend compileall, backend pytest, and frontend build checks.
