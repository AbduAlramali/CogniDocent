class CacheClientError(Exception):
    """Base exception for all Cache Client errors."""

    pass


class CacheConnectionError(CacheClientError):
    """Raised when a connection to the cache server fails or is refused."""

    pass


class CacheTimeoutError(CacheClientError):
    """Raised when a cache operation takes too long to complete."""

    pass


class CacheAuthenticationError(CacheClientError):
    """Raised when cache server authentication fails."""

    pass


class CacheDecodeError(CacheClientError):
    """Raised when the cached data cannot be decoded into the expected format."""

    pass


class CacheEncodeError(CacheClientError):
    """Raised when data cannot be serialized/encoded before saving to the cache."""

    pass
