# Changelog

## 2.5.4 Parts 11-13

- Added a real multi-worker generation page with validated worker-count and target-mod controls, clear loading/error states, merge-round evidence and a direct builder handoff.
- Added a Workers entry to project navigation without hiding the existing core sections.
- Added regression coverage for the worker page route, navigation link, API contract and release verification contract.
- Added an offline release verifier covering Python compilation, API registration, worker engine, export validation, frontend route and Windows launcher contracts.
- CI now includes an offline verification job that depends on backend pytest and frontend build.
- CI now parses `start.ps1` on a real Windows runner and checks that `start.bat` delegates to it.
- External smoke gates remain explicit: real AI provider, catalog network, Windows launch with installed dependencies and MRPack round-trip.

## 2.5.4 Parts 8-10

- Merge decisions now score and expose intent coverage, compatibility, performance, dependency quality, confidence, redundancy, synergy, world-generation coverage and export-input completeness.
- Consolidated worker catalog coalescing into the reusable bounded cache module with TTL/LRU completed-result storage.
- Added the repository audit report and regression tests.

## 2.5.4 Part 7

- Added true parallel AI workers, bounded concurrency, shared request coalescing, automatic merge rounds and dependency/compatibility/analysis gates.

## 2.5.4 Parts 4-6

- Replaced raw JSON AI editor output with a readable plan card and honest AI fallback labels.
- Added real top-p and retry controls wired into provider calls.

## 2.5.4

- Fixed Windows startup logging and made navigation and Intelligence import consistent.
