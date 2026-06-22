"""Integration tests for .apkg export (real genanki + sqlite, no mocks)."""

import json
import sqlite3
import zipfile
from pathlib import Path

from ankification.export import to_apkg
from ankification.models import Card, CardType


def _cards() -> list[Card]:
    return [
        Card(type=CardType.BASIC, front="Q1", back="A1"),
        Card(type=CardType.CLOZE, cloze_text="The {{c1::slope}} of the budget line is negative."),
        Card(type=CardType.BASIC, front='See <img src="fig.svg">', back="A diagram."),
    ]


def _inspect(apkg: Path) -> tuple[list[str], list[str], dict]:
    """Return (zip names, note guids, media map) from a .apkg."""
    work = apkg.parent / f"{apkg.stem}_db.anki2"
    with zipfile.ZipFile(apkg) as zf:
        names = zf.namelist()
        media = json.loads(zf.read("media"))
        work.write_bytes(zf.read("collection.anki2"))
    con = sqlite3.connect(work)
    guids = [row[0] for row in con.execute("SELECT guid FROM notes ORDER BY guid")]
    con.close()
    work.unlink()
    return names, guids, media


def test_apkg_has_notes_and_bundles_media(tmp_path):
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "fig.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    out = tmp_path / "deck.apkg"

    to_apkg(_cards(), "My Deck", media_dir, out)

    assert out.exists()
    names, guids, media = _inspect(out)
    assert "collection.anki2" in names and "media" in names
    assert len(guids) == 3  # basic + cloze + image card -> 3 notes
    assert "fig.svg" in media.values()  # referenced image bundled


def test_apkg_guids_stable_across_runs(tmp_path):
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    cards = _cards()  # same card ids both runs
    a, b = tmp_path / "a.apkg", tmp_path / "b.apkg"

    to_apkg(cards, "D", media_dir, a)
    to_apkg(cards, "D", media_dir, b)

    _, guids_a, _ = _inspect(a)
    _, guids_b, _ = _inspect(b)
    assert guids_a == guids_b and len(guids_a) == 3  # idempotent: re-import updates, no dupes


def test_export_creates_parent_dir(tmp_path):
    out = tmp_path / "nested" / "exports" / "deck.apkg"
    to_apkg([Card(front="q", back="a")], "D", tmp_path / "media", out)
    assert out.exists()


def _deck_names(apkg: Path) -> set[str]:
    work = apkg.parent / "decks.anki2"
    with zipfile.ZipFile(apkg) as zf:
        work.write_bytes(zf.read("collection.anki2"))
    con = sqlite3.connect(work)
    decks = json.loads(con.execute("SELECT decks FROM col").fetchone()[0])
    con.close()
    work.unlink()
    return {d["name"] for d in decks.values()}


def test_apkg_groups_cards_into_subdecks(tmp_path):
    cards = [
        Card(front="q1", back="a1", subdeck="Ch01 - The Market"),
        Card(front="q2", back="a2", subdeck="Ch02 - Budget"),
        Card(front="q3", back="a3"),  # no subdeck -> deck root
    ]
    out = tmp_path / "varian.apkg"
    to_apkg(cards, "Varian", tmp_path / "media", out)

    names = _deck_names(out)
    assert "Varian::Ch01 - The Market" in names
    assert "Varian::Ch02 - Budget" in names
    assert "Varian" in names
