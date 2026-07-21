"""Backward-compatible LM Studio client.

New application code uses :func:`create_ai_provider`; this class remains for
existing scripts and integrations and intentionally delegates to the common
OpenAI-compatible provider.
"""

from app.config import config
from app.services.ai_provider import OpenAICompatibleProvider


class LMStudioClient(OpenAICompatibleProvider):
    def __init__(self) -> None:
        super().__init__(config.ai)
