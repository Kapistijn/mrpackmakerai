# Changelog

## 1.6.2

A correctness and robustness release focused on the generation pipeline.

### Fixed (critical)

- **Generation returned "No compatible mods were found" for valid version/loader combos.**
  Modrinth search was filtering with a `loaders:<loader>` facet, but Modrinth's
  search index has no `loaders` facet -- loaders live under `categories`. The
  facet matched zero documents, so every search came back empty even for
  popular combos like 1.20.1 / Forge. Now filtered via `categories:<loader>`.
- **AI connection test and generation returned HTTP 500** (`TypeError: 'NoneType'
  object is not iterable`) whenever an OpenAI-compatible endpoint replied with a
  body that had no `data` array (e.g. a base URL missing the `/v1` suffix).
  `list_models` now treats a missing payload as "no models" and the endpoint
  reports "not reachable" cleanly.

### Fixed

- **CurseForge could ship a jar for the wrong Minecraft version.** The file
  picker jumped straight from an exact version+loader match to *any* returned
  file. It now prefers, in order: exact version+loader, then the newest file
  matching the version, then the API's coarse pre-filter as a last resort.
- **Projects could get wedged in `GENERATING` forever.** If starting the
  background job failed after the status was committed, the project stayed
  `GENERATING` and every retry returned 409 until a server restart. The status
  is now rolled back to `DRAFT` when start-up fails.
- **Router registration failures were swallowed.** A broken import used to leave
  the app running with silently missing routes (confusing 404s on real
  endpoints). Registration errors now fail loudly at startup.

### Performance / robustness

- **Bounded the in-memory API cache.** The TTL cache only evicted a key when it
  was read again after expiry, so one-off search keys accumulated forever and
  slowly leaked memory. It now enforces a max size with LRU eviction and purges
  expired entries on write.

### Internal

- Added dependency-light regression tests for the CurseForge file picker and
  the cache bounds.
- Bumped backend and frontend versions to 1.6.2.
