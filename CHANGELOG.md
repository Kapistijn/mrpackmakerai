# Changelog

## 1.9.5
- Added explainable Modpack Quality Score: realism, immersion, performance, compatibility, and content balance.
- Added Mod Synergy Analyzer with positive combinations and non-blocking high-risk world-generation overlap warnings.
- Added Performance Simulator based on mod count, worldgen, entities, particles, and shader preference.
- Added safe update planning with backup, dependency, compatibility, diff, and explicit approval steps.
- Added Mod Reputation signals for stability, maintenance, compatibility, and performance.
- Added approval-gated natural-language mod editing plans.
- Added Lite, Balanced, and Ultimate variant planning.
- Added `/api/insights` endpoints and regression tests.

## 1.9.2
- Added bounded, shared Modrinth request throttling with Retry-After support, exponential backoff, jitter, and duplicate request coalescing.
- Raised configurable modpack limits from 300 to 500 without removing the 1.8.x generation contracts.
- Added dependency graph safety limits and generation diagnostics.

## 1.9.0
- Added the approval-gated AI modpack editor, MRPack import, crash analysis, repair planning, and change history.

## 1.8.x
- Preserved legacy generation, compatibility, builder, and export behavior.
