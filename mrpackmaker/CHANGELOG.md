# Changelog

## 1.7.2.4

Final prompt-pipeline regression fix for the 1.7.2.x line.

### Fixed

- Boss constraints are now generated from a single alias-aware signal matcher,
  covering `boss`, `bosses`, and Dutch `bazen` without relying on a separate
  normalized intent list.
- The exact contract `prefer content with bosses when compatible` is now
  protected by a dedicated regression test using the failing horror prompt.
- Content constraints for monsters, zombies, automation, quests, immersion and
  psychological horror use the same deterministic path.
- Backend and frontend metadata bumped to 1.7.2.4.

### Verification

The existing 1.7.2.x prompt tests remain unchanged. This release fixes the
production contract rather than weakening assertions.

## 1.7.2.3

Restored content-priority propagation for boss and other gameplay intent.

## 1.7.2.2

Restored the canonical duplicate-detection prompt constraint.

## 1.7.2.1

Fixed explicit-model local AI compatibility and ambiguous Minecraft-version
prompt output.
