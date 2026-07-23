# Changelog

## 1.7.2.3

Prompt-pipeline regression hotfix.

### Fixed

- Restored content-priority propagation from detected intent into generation
  constraints.
- Prompts mentioning bosses now emit `prefer content with bosses when compatible`.
- Monsters, zombies, automation, questing, immersion and psychological intent
  now map to explicit, testable selection constraints instead of being reduced
  to unstructured tags.
- Added regression coverage for Dutch horror prompts and content priorities.
- Bumped backend and frontend metadata to 1.7.2.3.

### Verification

The existing sparse horror prompt regression now receives all expected
constraints: minimum mod count, duplicate detection and boss-content priority.

## 1.7.2.2

Restored the canonical duplicate-detection prompt constraint.

## 1.7.2.1

Fixed explicit-model local AI compatibility and ambiguous Minecraft-version
prompt output.
