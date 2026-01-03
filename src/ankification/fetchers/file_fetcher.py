"""Local file fetcher for text and markdown files."""

from pathlib import Path

from .base import BaseFetcher


class FileFetcher(BaseFetcher):
    """Fetcher for local text files (.txt, .md, etc.)."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".rst", ".log"}

    async def fetch(self, source: str) -> str:
        """Read and return file contents.

        Args:
            source: File path

        Returns:
            File contents

        Raises:
            ValueError: If file doesn't exist or has unsupported extension
            RuntimeError: If file cannot be read
        """
        path = Path(source).expanduser()

        if not path.exists():
            raise ValueError(f"File not found: {source}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {source}")

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {path.suffix}. "
                f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                content = path.read_text(encoding="latin-1")
            except Exception as e:
                raise RuntimeError(f"Failed to read file {source}: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to read file {source}: {e}") from e

        if not content.strip():
            raise ValueError(f"File is empty: {source}")

        return content.strip()

    def can_handle(self, source: str) -> bool:
        """Check if source is a supported file.

        Args:
            source: Source to check

        Returns:
            True if source is a file with supported extension
        """
        try:
            path = Path(source).expanduser()
            return (
                path.suffix.lower() in self.SUPPORTED_EXTENSIONS
                and not source.startswith("http://")
                and not source.startswith("https://")
            )
        except Exception:
            return False

    @property
    def name(self) -> str:
        """Get fetcher name."""
        return "file"
