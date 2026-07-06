"""Markdown-first ingestion: get a source into clean markdown before generating cards.

The canonical path (documented in the skill) is the `to-md` skill for PDF/DOCX/EPUB/URL,
or pandoc on LaTeX source (e.g. arXiv) when that beats PDF extraction. These helpers cover
the library/eval path: already-markdown files, a best-effort URL scrape, and the
arXiv-LaTeX -> pandoc route. Binary formats raise with a pointer to `to-md`.
"""

from __future__ import annotations

import gzip
import io
import logging
import shutil
import subprocess
import tarfile
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from .models import Source

logger = logging.getLogger(__name__)

_MARKDOWN_SUFFIXES = {".md", ".markdown", ".txt", ".text"}
_BINARY_SUFFIXES = {".pdf", ".docx", ".epub", ".pptx"}


def from_text(title: str, text: str, kind: str = "markdown", uri: str = "") -> Source:
    return Source(title=title, kind=kind, markdown=text, uri=uri)


def from_file(path: str | Path) -> Source:
    """Load an already-markdown/text file. Binary formats are rejected with guidance."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in _BINARY_SUFFIXES:
        raise ValueError(
            f"{path.name} is a binary format; convert it to markdown first with the "
            "`to-md` skill, then pass the .md file here."
        )
    if suffix not in _MARKDOWN_SUFFIXES:
        logger.warning("treating %s as plain text", path.name)
    return Source(title=path.stem, kind="markdown", markdown=path.read_text(), uri=str(path))


def _extract_readable(html: str) -> tuple[str, str]:
    """Return (title, readable text) from raw HTML, dropping boilerplate tags."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    title = soup.title.get_text().strip() if soup.title else ""
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    return title, text


def url_to_markdown(url: str, title: str = "") -> Source:
    """Fetch a web page and extract readable text (best-effort; prefer `to-md`)."""
    resp = httpx.get(url, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    page_title, text = _extract_readable(resp.text)
    return Source(title=title or page_title or url, kind="url", markdown=text, uri=url)


def _tex_from_eprint(data: bytes, arxiv_id: str) -> bytes:
    """Extract the main .tex (contains \\documentclass) from an arXiv e-print blob.

    E-prints are a tarball for multi-file submissions, a bare gzipped .tex for single-file
    ones, or a PDF when no source is available.
    """
    try:
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            for member in tar.getmembers():
                if not member.name.endswith(".tex"):
                    continue
                extracted = tar.extractfile(member)
                if extracted is not None:
                    content = extracted.read()
                    if b"\\documentclass" in content:
                        return content
    except tarfile.ReadError:
        try:
            single = gzip.decompress(data)
        except OSError:
            single = data
        if b"\\documentclass" in single:
            return single
    raise RuntimeError(
        f"no main .tex (\\documentclass) found in arXiv:{arxiv_id} e-print; if the paper "
        "is PDF-only, convert the PDF with `to-md` instead."
    )


def arxiv_to_markdown(arxiv_id: str) -> Source:
    """Download an arXiv paper's LaTeX e-print and convert it to markdown via pandoc.

    Requires pandoc on PATH. Handles tarball and single-file (gzipped) e-prints; fails
    with a clear error if pandoc is missing or the e-print has no LaTeX source.
    """
    if shutil.which("pandoc") is None:
        raise RuntimeError("pandoc is not installed; `brew install pandoc` or use `to-md`.")
    resp = httpx.get(f"https://arxiv.org/e-print/{arxiv_id}", timeout=60.0, follow_redirects=True)
    resp.raise_for_status()
    tex_bytes = _tex_from_eprint(resp.content, arxiv_id)

    proc = subprocess.run(
        ["pandoc", "-f", "latex", "-t", "gfm", "--wrap=none"],
        input=tex_bytes,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pandoc failed on arXiv:{arxiv_id}: {proc.stderr.decode()[:500]}")
    return Source(
        title=f"arXiv:{arxiv_id}",
        kind="arxiv",
        markdown=proc.stdout.decode(),
        uri=f"https://arxiv.org/abs/{arxiv_id}",
    )
