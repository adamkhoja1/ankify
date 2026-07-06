"""Offline tests for ingestion: file loading, HTML extraction, arXiv e-print unpacking."""

import gzip
import io
import tarfile
from pathlib import Path

import pytest

from ankify.ingest import _extract_readable, _tex_from_eprint, from_file

TEX = b"\\documentclass{article}\\begin{document}hi\\end{document}"


def _tarball(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_ingest_rejects_binary(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    with pytest.raises(ValueError, match="to-md"):
        from_file(pdf)


def test_ingest_reads_markdown(tmp_path: Path) -> None:
    md = tmp_path / "note.md"
    md.write_text("# Title\n\nbody")
    src = from_file(md)
    assert src.markdown.startswith("# Title") and src.kind == "markdown"


def test_extract_readable_strips_boilerplate_and_gets_title() -> None:
    title, text = _extract_readable(
        "<html><head><title>My Page</title><script>x()</script></head>"
        "<body><nav>menu</nav><p>real content</p></body></html>"
    )
    assert title == "My Page"
    assert "real content" in text and "menu" not in text and "x()" not in text


def test_extract_readable_handles_nested_and_missing_title() -> None:
    # <title> with element children makes soup.title.string None; get_text still works
    title, _ = _extract_readable("<title><span>Nested</span></title><p>body</p>")
    assert title == "Nested"
    title, _ = _extract_readable("<p>no title at all</p>")
    assert title == ""


def test_tex_from_eprint_tarball_picks_main_tex() -> None:
    data = _tarball({"refs.tex": b"just a bibliography", "main.tex": TEX})
    assert _tex_from_eprint(data, "1234.5678") == TEX


def test_tex_from_eprint_single_gzipped_file() -> None:
    assert _tex_from_eprint(gzip.compress(TEX), "1234.5678") == TEX


def test_tex_from_eprint_pdf_only_raises_with_guidance() -> None:
    with pytest.raises(RuntimeError, match="to-md"):
        _tex_from_eprint(b"%PDF-1.5 not latex", "1234.5678")


def test_tex_from_eprint_tarball_without_documentclass_raises() -> None:
    data = _tarball({"notes.tex": b"no documentclass here"})
    with pytest.raises(RuntimeError, match="documentclass"):
        _tex_from_eprint(data, "1234.5678")
