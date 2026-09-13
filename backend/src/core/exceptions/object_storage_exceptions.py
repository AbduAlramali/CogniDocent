# ---------------------------------------------------------------------------
# custom exception types
# ---------------------------------------------------------------------------
class ObjectRepositoryError(Exception):
    """Base class for all repository‑related errors."""


class ObjectNotFoundError(ObjectRepositoryError):
    """Raised when a requested object does not exist in the bucket."""


class ObjectUploadError(ObjectRepositoryError):
    """Raised when an upload or presign‑for‑upload operation fails."""


class ObjectDownloadError(ObjectRepositoryError):
    """Raised when a download or presign‑for‑download operation fails."""
