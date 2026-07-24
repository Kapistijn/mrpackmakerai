# Changelog

## 2.5.4 Part 7

- Added a true parallel worker generation engine with independently seeded exploration directives.
- Each worker calls the configured AI provider for its own structured search strategy, searches real catalog providers, builds its own candidate pack, and records intent, performance, compatibility, dependency-quality and confidence evidence.
- Added bounded concurrency so large worker counts do not create an unbounded task storm.
- Added a shared in-flight coalescing cache so identical catalog requests are fetched once and shared by workers.
- Added automatic merge rounds for any worker count from 2 through 24. Uneven rounds carry the final candidate forward, while every paired merge preserves unique content from both candidates and records comparison evidence.
- Added `POST /api/ai/generate/{project_id}/workers` with configurable worker count and target mod count.
- Added frontend API support and regression tests for worker validation, merge convergence and cache coalescing.

## 2.5.4 Parts 4-6

- Replaced raw JSON AI editor output with a readable plan card and honest AI fallback labels.
- Added real top-p and retry controls wired into provider calls.

## 2.5.4

- Fixed Windows startup logging and made navigation and Intelligence import consistent.
