# Repository audit 2.5.4

Scope: backend Python, frontend TypeScript/React, launch scripts and API surface reviewed before Parts 8-10.

## Findings addressed

- **Duplicate catalog request paths:** worker generation now uses the shared bounded async coalescing cache; completed results have TTL/LRU bounds and concurrent identical requests share one future.
- **Duplicate merge decisions:** merge rounds now use one scoring path with explicit evidence for intent coverage, compatibility, performance, dependency quality, confidence, redundancy, synergy, world-generation coverage and export-input completeness.
- **Raw developer output:** AI editor plans are rendered as a user-facing card; technical JSON remains inside Developer Details.
- **Conditional navigation:** core navigation is stable without a project.
- **In-page MRPack intelligence import:** upload and report display remain inside Intelligence.
- **AI fallback ambiguity:** deterministic fallback responses are explicitly labelled and include the provider failure reason.
- **Startup diagnostics:** Windows launcher separates native stdout and stderr and only treats non-zero exit codes as process failure.

## Scan results

- TODO marker search: no matches returned.
- Placeholder marker search: no matches returned.
- Debug endpoint scan: no standalone debug route found in the registered API routes.
- Export validation: one shared strict validator is used for compatibility/export boundaries.
- Dependency repair: one resolver boundary is used by generation, editor apply and worker validation.

## Deliberately not removed

`repair_engine.py` and `conflict_resolver.py` are small service boundaries used by repair APIs and are retained. Replacing them with fake provider calls would make crash repair less reliable when AI is offline.

## Remaining release gates

The repository audit is not a claim that external systems are green. Before merge: full pytest, frontend build/typecheck, Windows PowerShell 5.1 startup smoke, real AI provider smoke, catalog smoke, MRPack import/export roundtrip and a worker-count stress run.
