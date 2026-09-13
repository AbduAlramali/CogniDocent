class ChatServiceError(Exception):
    """Base exception for all chat service operations."""

    pass


class FileHashMismatchError(ChatServiceError):
    """Raised when the computed SHA-256 hash of an uploaded file does not match the provided hash."""

    def __init__(self, filename: str, expected_hash: str, computed_hash: str):
        self.filename = filename
        self.expected_hash = expected_hash
        self.computed_hash = computed_hash
        super().__init__(
            f"File hash mismatch for '{filename}': expected '{expected_hash}', got '{computed_hash}'"
        )


class EmptyFileContentError(ChatServiceError):
    """Raised when uploaded file content is empty."""

    def __init__(self, filename: str):
        self.filename = filename
        super().__init__(f"Empty content received for file '{filename}'")


class InvalidEventDataError(ChatServiceError):
    """Raised when an event payload is invalid or missing required fields."""

    def __init__(self, message: str):
        super().__init__(message)

