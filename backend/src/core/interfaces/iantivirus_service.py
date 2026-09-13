from abc import ABC, abstractmethod
from typing import BinaryIO
from pathlib import Path


class IAntivirusService(ABC):
    """
    The Antivirus Port (Interface).
    Defined in the Service/Core layer to decouple business logic
    from the specific scanning technology.
    """

    @abstractmethod
    def scan_file(self, file_source: str | Path | BinaryIO) -> bool:
        """
        Scans a file for viruses.

        Args:
            file_source: Path to the file or a file-like object.

        Returns:
            bool: True if the file is clean, False if infected.

        Raises:
            AntivirusError: If the scanning service is unavailable or fails.
        """
        pass

    @abstractmethod
    def scan_file_by_path(self, file_path: str | Path) -> bool:
        """Scans a file by its local path."""
        pass

    @abstractmethod
    def get_version(self) -> str:
        """Returns the current version of the virus definitions."""
        pass
