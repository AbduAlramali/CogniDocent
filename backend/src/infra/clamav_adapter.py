from src.core.interfaces.iantivirus_service import IAntivirusService
from src.core.exceptions.antivirus_exceptions import AntivirusError
import clamd
from typing import BinaryIO
from pathlib import Path


class ClamAVAdapter(IAntivirusService):
    """
    Infrastructure Adapter for ClamAV.
    Connects to the ClamAV daemon running in a Docker container.
    """

    def __init__(self, client):
        self._client = client

    def scan_file(self, file_source: str | Path | BinaryIO) -> bool:
        """
        Scans a file. Supports local paths (if shared volume) or streaming (BinaryIO).
        """
        try:
            # 1. Handle File-like objects (e.g., streaming from MinIO)
            if hasattr(file_source, "read"):
                # .instream() sends the file content over the socket to ClamAV
                result = self._client.instream(file_source)

            # 2. Handle Local Paths
            else:
                return self.scan_file_by_path(file_source)

            # ClamAV returns a dict: {'stream': ('OK', None)} or {'path': ('FOUND', 'VirusName')}
            status_info = list(result.values())[0]
            status = status_info[0]  # 'OK' or 'FOUND'

            if status == "OK":
                return True

            # If 'FOUND', it's a virus
            return False

        except (clamd.ConnectionError, clamd.BufferTooLongError) as e:
            raise AntivirusError(f"ClamAV service communication error: {str(e)}")
        except Exception as e:
            raise AntivirusError(f"Unexpected error during scan: {str(e)}")

    def scan_file_by_path(self, file_path: str | Path) -> bool:
        """Scans a file by its local path by streaming it to the ClamAV daemon."""
        try:
            file_path_str = str(file_path)
            if not Path(file_path_str).exists():
                raise AntivirusError(f"File not found: {file_path_str}")

            with open(file_path_str, "rb") as f:
                return self.scan_file(f)
        except AntivirusError:
            raise
        except Exception as e:
            raise AntivirusError(f"Unexpected error during scan: {str(e)}")

    def get_version(self) -> str:
        """Check if ClamAV is alive and return its version."""
        try:
            return self._client.version()
        except Exception as e:
            raise AntivirusError(f"Could not retrieve ClamAV version: {str(e)}")
