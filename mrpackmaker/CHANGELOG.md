# Changelog

## 2.5.3

- Fixed startup import crash by restoring ModSearchResponse.
- Fixed Windows MRPack permission errors by closing upload temp files before parsing.
- Added per-package installer progress such as Installing fastapi (1/12), with spinner and full logs.
- Added live server logs in start.bat and preserved startup-error.log.
- Added Forge dependency diagnostics and non-fatal dropped-mod reporting where unresolved dependencies make a mod incompatible.
