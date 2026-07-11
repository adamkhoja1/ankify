# ruff: noqa: E501
"""Judge existing flashcards with the rubric and render an HTML report.

Loads Varian chapter TSVs, judges each card (probes + ungrounded tier, grounded on the
chapter text for faithfulness), and writes an HTML report grouping cards by score with the
judge's reasoning. GPT-5.5 high. Threaded so the per-card 6-call judging isn't serial.

Usage: uv run scripts/judge_cards_html.py --vault <econ-study-dir> --chapters 01,02,03
"""

from __future__ import annotations

import html
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fire  # type: ignore[import-untyped]

from ankify.llm import LLM, CostTracker
from ankify.models import Card, CardType, Verdict
from ankify.rubric import Judge

CH_MD = {
    "01": "01-the-market.md",
    "02": "02-budget-constraint.md",
    "03": "03-preferences.md",
}
TIER_RANK = {"T3": 3, "T2": 2, "T1": 1, "T0": 0}


def load_cards(chapters: list[str], tsv_dir: Path) -> list[tuple[str, Card]]:
    items: list[tuple[str, Card]] = []
    for ch in chapters:
        tsv = tsv_dir / f"varian_ch{ch}_flashcards.tsv"
        for line in tsv.read_text().splitlines()[1:]:  # skip header
            parts = line.split("\t")
            if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
                continue
            tags = parts[2].split() if len(parts) > 2 else []
            items.append((ch, Card(type=CardType.BASIC, front=parts[0], back=parts[1], tags=tags)))
    return items


def _card_html(ch: str, card: Card, v: Verdict) -> str:
    failed = [p for p in v.probes if p.failed]
    passed = [p for p in v.probes if not p.failed]
    probe_rows = "".join(
        f'<li class="fail"><b>{p.probe.value}</b>: {html.escape(p.reason)}</li>' for p in failed
    ) or '<li class="ok">no probe failures</li>'
    passed_str = ", ".join(p.probe.value for p in passed) or "—"
    return f"""
    <div class="card tier-{v.tier.value}">
      <div class="chead">
        <span class="badge t{v.tier.value}">{v.tier.value}</span>
        <span class="ch">ch{ch}</span>
        {'<span class="clean">clean</span>' if v.clean else ''}
      </div>
      <div class="q">{html.escape(card.front)}</div>
      <div class="a">{html.escape(card.back)}</div>
      <div class="why"><b>Judge:</b> {html.escape(v.reason)}</div>
      <ul class="probes">{probe_rows}</ul>
      <div class="passed">passed probes: {passed_str}</div>
    </div>"""


def render(results: list[tuple[str, Card, Verdict]], tracker: CostTracker) -> str:
    results.sort(key=lambda r: (-TIER_RANK[r[2].tier.value], r[0]))
    n = len(results)
    usable = sum(1 for _, _, v in results if v.usable)
    clean = sum(1 for _, _, v in results if v.clean)
    tiers: dict[str, int] = {}
    probe_fail: dict[str, int] = {}
    for _, _, v in results:
        tiers[v.tier.value] = tiers.get(v.tier.value, 0) + 1
        for p in v.failed_probes:
            probe_fail[p.value] = probe_fail.get(p.value, 0) + 1
    high = [r for r in results if r[2].usable]
    low = [r for r in results if not r[2].usable]
    def cards_html(rs: list[tuple[str, Card, Verdict]]) -> str:
        return "".join(_card_html(ch, c, v) for ch, c, v in rs)

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Varian cards — rubric report</title>
<style>
 body{{font:15px/1.55 ui-sans-serif,system-ui,sans-serif;background:#f3f1ec;color:#21201c;margin:0;padding:2rem 1rem 4rem}}
 .wrap{{max-width:840px;margin:0 auto}}
 h1{{font-size:1.5rem}} h2{{margin-top:2rem;border-bottom:1px solid #ddd8cf;padding-bottom:.3rem}}
 .summary{{background:#fffdf8;border:1px solid #ddd8cf;border-radius:12px;padding:1rem 1.25rem;margin:1rem 0}}
 .summary code{{background:#efe;padding:.05rem .3rem;border-radius:4px}}
 .card{{background:#fffdf8;border:1px solid #ddd8cf;border-left-width:5px;border-radius:10px;padding:1rem 1.1rem;margin:.8rem 0}}
 .tier-T3{{border-left-color:#2f7d54}} .tier-T2{{border-left-color:#6a9a3a}}
 .tier-T1{{border-left-color:#c98a2b}} .tier-T0{{border-left-color:#b04a3a}}
 .chead{{display:flex;gap:.5rem;align-items:center;font-size:.75rem;margin-bottom:.5rem}}
 .badge{{font-family:ui-monospace,monospace;font-weight:700;padding:.1rem .45rem;border-radius:6px;color:#fff}}
 .tT3{{background:#2f7d54}} .tT2{{background:#6a9a3a}} .tT1{{background:#c98a2b}} .tT0{{background:#b04a3a}}
 .ch{{color:#8a857c}} .clean{{color:#2f7d54;font-weight:600}}
 .q{{font-size:1.1rem;font-weight:600}} .a{{color:#444;margin:.25rem 0 .6rem}}
 .why{{font-size:.9rem;background:#faf8f2;border-radius:8px;padding:.5rem .6rem}}
 ul.probes{{margin:.5rem 0;padding-left:1.1rem;font-size:.88rem}}
 li.fail{{color:#9a3b2c}} li.ok{{color:#2f7d54;list-style:none;margin-left:-1.1rem}}
 .passed{{font-size:.78rem;color:#8a857c}}
</style></head><body><div class="wrap">
<h1>Varian existing cards — rubric report</h1>
<div class="summary">
 <b>{n} cards judged.</b> Usable (T2+T3): <code>{usable}/{n} = {usable/n:.0%}</code> ·
 clean (usable + no probe failures): <code>{clean}/{n} = {clean/n:.0%}</code><br>
 tier distribution: {dict(sorted(tiers.items()))}<br>
 probe failures: {dict(sorted(probe_fail.items()))}<br>
 <small>{tracker.summary()} · GPT-5.5 high · grounded on chapter text</small>
</div>
<h2>Needs work — T0/T1 ({len(low)})</h2>{cards_html(low)}
<h2>Usable — T2/T3 ({len(high)})</h2>{cards_html(high)}
</div></body></html>"""


def main(
    vault: str,
    chapters: str = "01,02,03",
    out: str = "eval_runs/varian_existing_cards.html",
    budget: float = 14.0,
    workers: int = 8,
) -> None:
    vault_dir = Path(vault)
    md_dir = vault_dir / "varian_intermediate_microeconomics.md"
    tsv_dir = vault_dir / "anki_exports"
    chs = chapters.split(",")
    tracker = CostTracker(budget_usd=budget)
    judge = Judge(LLM(tracker=tracker))
    src = {ch: (md_dir / CH_MD[ch]).read_text() for ch in chs}
    items = load_cards(chs, tsv_dir)
    print(f"judging {len(items)} cards across chapters {chs}…")

    def work(item: tuple[str, Card]) -> tuple[str, Card, Verdict]:
        ch, card = item
        return ch, card, judge.judge(card, source_description=src[ch])

    results: list[tuple[str, Card, Verdict]] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, r in enumerate(ex.map(work, items), 1):
            results.append(r)
            print(f"  [{i}/{len(items)}] ch{r[0]} -> {r[2].tier.value}")

    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(results, tracker))
    print(f"\nwrote {out_path.resolve()}\n{tracker.summary()}")


if __name__ == "__main__":
    fire.Fire(main)
