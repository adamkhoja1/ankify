"""Edit existing Varian cards to use proper Anki LaTeX (MathJax \\(...\\) delimiters).

Converts the plain-text math in the budget-constraint cards to Anki MathJax. Decisions are
keyed by card id, so they're preserved. Run: uv run scripts/latexify_varian.py
"""

import re

from ankification.server.session import SessionStore

# Ordered longest/most-specific first so we don't partially rewrite inside a bigger match.
REPLACEMENTS = [
    (r"Delta x2 / Delta x1 = -p1/p2", r"\\(\\Delta x_2/\\Delta x_1 = -p_1/p_2\\)"),
    (r"p1 x1 \+ p2 x2 <= m", r"\\(p_1 x_1 + p_2 x_2 \\le m\\)"),
    (r"p1 x1 \+ p2 x2 = m/t", r"\\(p_1 x_1 + p_2 x_2 = m/t\\)"),
    (r"p1 x1 \+ p2 x2 = m", r"\\(p_1 x_1 + p_2 x_2 = m\\)"),
    (r"\(1 \+ tau\)p1", r"\\((1+\\tau)p_1\\)"),
    (r"\(1 - sigma\)p1", r"\\((1-\\sigma)p_1\\)"),
    (r"-p1/p2", r"\\(-p_1/p_2\\)"),
    (r"\bp1/p2\b", r"\\(p_1/p_2\\)"),
    (r"\bm/p1\b", r"\\(m/p_1\\)"),
    (r"\bm/p2\b", r"\\(m/p_2\\)"),
    (r"\bp1 \+ t\b", r"\\(p_1 + t\\)"),
    (r"\bp1 - s\b", r"\\(p_1 - s\\)"),
    (r"\(p1, p2\)", r"(\\(p_1\\), \\(p_2\\))"),
    (r"\(x1, x2\)", r"(\\(x_1\\), \\(x_2\\))"),
]


def latexify(text: str) -> str:
    for pattern, repl in REPLACEMENTS:
        text = re.sub(pattern, repl, text)
    return text


def main() -> None:
    store = SessionStore(".cards/varian_session.json")
    session = store.load()
    changed = 0
    for card in session.current_cards():
        before = (card.front, card.back)
        card.front = latexify(card.front)
        card.back = latexify(card.back)
        if (card.front, card.back) != before:
            changed += 1
    store.save(session)
    print(f"LaTeX-ified {changed} Varian cards in place")


if __name__ == "__main__":
    main()
