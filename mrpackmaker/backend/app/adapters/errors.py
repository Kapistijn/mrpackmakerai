from __future__ import annotations


class ProviderError(RuntimeError):
    """Base error raised at an adapter boundary."""


class RateLimitError(ProviderError):
    """The upstream provider rejected the request due to rate limiting."""


class AuthenticationError(ProviderError):
    """The configured provider credentials were rejected."""


class InvalidResponseError(ProviderError):
    """The legacy client returned data that cannot form a domain object."""


class ProviderUnavailableError(ProviderError):
    """The provider is not configured or is otherwise unavailable."""
