"""Feature flags for the additive adapter layer.

The legacy generation path remains the default. This module is intentionally
not imported by the orchestrator, so adding adapters cannot switch production
behavior by accident.
"""

legacy_generation = True


def new_adapters_enabled() -> bool:
    """Return whether an explicit caller opted into the new adapter path."""
    return not legacy_generation
