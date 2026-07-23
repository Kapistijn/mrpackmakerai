# Changelog

## 1.8.8

Pipeline integrity fixes for the 1.8.7 review blockers.

- Required and forbidden mod constraints now flow through requirements, search, scoring, dependency resolution and export errors.
- Creativity and discovery depth control catalog scope and query strategy.
- Central intent taxonomy is shared by intent analysis, scoring and self-check.
- Shader support emits real metadata assets, requires a resolved Iris/Oculus loader, and compatibility validates the loader and pack assets.
- Generation now fails on missing final intent requirements instead of merely logging them.
- Compatibility validates RAM/FPS/shader/override/pack_info configuration.
- Existing projects can load, edit, save and reload advanced configuration in Project Builder.
- Added 1.8.8 regression coverage for constraints, discovery, taxonomy, RAM profiles, scoring, defaults and dependency diagnostics.

## 1.8.7

Real intent analysis and a fully functional advanced configuration system. Every
advanced option now flows through the entire pipeline: Frontend -> API ->
Requirements -> Intent -> Scoring -> Generation -> .mrpack -> Compatibility. No
more options that are only stored.

## 1.7.3.2

Personalization and generation-quality hardening on top of 1.7.3.
