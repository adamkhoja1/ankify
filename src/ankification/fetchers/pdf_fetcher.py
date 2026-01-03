"""PDF content fetcher."""

from pathlib import Path

from pypdf import PdfReader

from .base import BaseFetcher


class PDFFetcher(BaseFetcher):
    """Fetcher for PDF documents."""

    async def fetch(self, source: str) -> str:
        """Extract text from PDF.

        Args:
            source: PDF file path

        Returns:
            Extracted text content

        Raises:
            ValueError: If file doesn't exist or is not a PDF
            RuntimeError: If PDF cannot be read
        """
        path = Path(source).expanduser()

        if not path.exists():
            raise ValueError(f"File not found: {source}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {source}")

        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Not a PDF file: {source}")

        try:
            reader = PdfReader(str(path))
            text_parts = []

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            if not text_parts:
                raise ValueError(f"No text content extracted from PDF: {source}")

            full_text = "\n\n".join(text_parts)
            return full_text.strip()

        except Exception as e:
            raise RuntimeError(f"Failed to read PDF {source}: {e}") from e

    def can_handle(self, source: str) -> bool:
        """Check if source is a PDF file.

        Args:
            source: Source to check

        Returns:
            True if source is a PDF file
        """
        try:
            path = Path(source).expanduser()
            return (
                path.suffix.lower() == ".pdf"
                and not source.startswith("http://")
                and not source.startswith("https://")
            )
        except Exception:
            return False

    @property
    def name(self) -> str:
        """Get fetcher name."""
        return "pdf"
