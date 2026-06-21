"""Markdown-first ingestion: get a source into clean markdown before generating cards.

The canonical path (documented in the skill) is the `to_md` skill for PDF/DOCX/EPUB/URL,
or pandoc on LaTeX source (e.g. arXiv) when that beats PDF extraction. These helpers cover
the library/eval path: already-markdown files, a best-effort URL scrape, and the
arXiv-LaTeX -> pandoc route. Binary formats raise with a pointer to `to_md`.
"""

from __future__ import annotations

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
            "`to_md` skill, then pass the .md file here."
        )
    if suffix not in _MARKDOWN_SUFFIXES:
        logger.warning("treating %s as plain text", path.name)
    return Source(title=path.stem, kind="markdown", markdown=path.read_text(), uri=str(path))


def url_to_markdown(url: str, title: str = "") -> Source:
    """Fetch a web page and extract readable text (best-effort; prefer `to_md`)."""
    resp = httpx.get(url, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    return Source(title=title or (soup.title.string if soup.title else url), kind="url",
                  markdown=text, uri=url)


def arxiv_to_markdown(arxiv_id: str) -> Source:
    """Download an arXiv paper's LaTeX e-print and convert it to markdown via pandoc.

    Requires pandoc on PATH. Picks the .tex file containing \\documentclass as the main
    file. Falls back with a clear error if pandoc is missing or no main .tex is found.
    """
    if shutil.which("pandoc") is None:
        raise RuntimeError("pandoc is not installed; `brew install pandoc` or use `to_md`.")
    resp = httpx.get(f"https://arxiv.org/e-print/{arxiv_id}", timeout=60.0, follow_redirects=True)
    resp.raise_for_status()

    with tarfile.open(fileobj=io.BytesIO(resp.content)) as tar:
        tex_members = [m for m in tar.getmembers() if m.name.endswith(".tex")]
        main = None
        for member in tex_members:
            extracted = tar.extractfile(member)
            if extracted and b"\\documentclass" in extracted.read():
                main = member
                break
        if main is None:
            raise RuntimeError(f"no main .tex (\\documentclass) found in arXiv:{arxiv_id}")
        source_tex = tar.extractfile(main)
        assert source_tex is not None
        tex_bytes = source_tex.read()

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
