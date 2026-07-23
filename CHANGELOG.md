# Changelog

## 1.9.2
- Added bounded, shared Modrinth request throttling with Retry-After support, exponential backoff, jitter, and duplicate request coalescing.
- Raised configurable modpack limits from 300 to 500 without removing the 1.8.x generation contracts.
- Rate-limited catalog lookups now degrade per candidate and leave other providers available instead of flooding logs and collapsing immediately.

## 1.9.0
- Added the approval-gated AI modpack editor, MRPack import, crash analysis, repair planning, and change history.

## 1.8.x
- Preserved legacy generation, compatibility, builder, and export behavior.
