"""Build a demo review session showcasing Anki LaTeX, images, and cloze rendering.

Run: uv run scripts/make_demo_session.py   then serve it on a separate port.
Images reference SVGs in .cards/media/ (served at /media by the app).
"""

from ankification.models import Card, CardSet, CardType, Source
from ankification.server.session import ReviewSession, SessionStore

CARDS = [
    Card(
        type=CardType.BASIC,
        front="In a two-good model with prices \\(p_1, p_2\\) and income \\(m\\), "
        "state the budget constraint.",
        back="\\(p_1 x_1 + p_2 x_2 = m\\)",
        tags=["demo", "latex"],
    ),
    Card(
        type=CardType.BASIC,
        front="Write the Slutsky decomposition of the total effect of a change in "
        "\\(p_1\\) on the demand for good 1.",
        back="\\[\\frac{\\partial x_1}{\\partial p_1}="
        "\\underbrace{\\left.\\frac{\\partial x_1}{\\partial p_1}\\right|_{\\text{comp}}}"
        "_{\\text{substitution}}-\\,x_1\\,"
        "\\underbrace{\\frac{\\partial x_1}{\\partial m}}_{\\text{income}}\\]",
        tags=["demo", "latex"],
    ),
    Card(
        type=CardType.CLOZE,
        cloze_text="With \\(x_1\\) on the horizontal axis, the slope of the budget line "
        "is {{c1::\\(-p_1/p_2\\)}}.",
        tags=["demo", "cloze", "latex"],
    ),
    Card(
        type=CardType.CLOZE,
        cloze_text="A variable whose value is determined by forces inside the model is "
        "{{c1::endogenous}}.",
        tags=["demo", "cloze"],
    ),
    Card(
        type=CardType.BASIC,
        front='What does the shaded region represent, and what is its boundary?'
        '<br><img src="budget_line.svg">',
        back="The shaded region is the <b>budget set</b> (all affordable bundles); its "
        "boundary is the budget line \\(p_1 x_1 + p_2 x_2 = m\\).",
        tags=["demo", "image"],
    ),
    Card(
        type=CardType.BASIC,
        front="At the marked bundle, what condition characterizes the consumer's optimal "
        'choice?<br><img src="optimal_choice.svg">',
        back="The indifference curve is tangent to the budget line, so "
        "\\(MRS = -p_1/p_2\\).",
        tags=["demo", "image", "latex"],
    ),
    Card(
        type=CardType.BASIC,
        front='In this market, what pins down \\(p^*\\) and \\(q^*\\)?'
        '<br><img src="supply_demand.svg">',
        back="Equilibrium: the price at which quantity demanded equals quantity supplied "
        "— the intersection of supply (S) and demand (D).",
        tags=["demo", "image"],
    ),
    Card(
        type=CardType.BASIC,
        front="Both panels plot a transformation \\(v = f(u)\\) of utility. What property "
        "must \\(f\\) have for \\(v\\) to represent the SAME preferences as \\(u\\)?"
        '<br><img src="textbook_figure.jpeg">',
        back="\\(f\\) must be a positive monotonic transformation (strictly increasing). "
        "Then \\(v = f(u)\\) orders all bundles exactly as \\(u\\) does, so it represents "
        "the same preferences. <i>(Varian ch. 4 — a real textbook JPEG figure.)</i>",
        tags=["demo", "image", "latex", "textbook"],
    ),
]


def main() -> None:
    source = Source(title="Anki rendering demo (LaTeX · images · cloze)", kind="markdown")
    session = ReviewSession(
        source=source,
        notes="Demo of LaTeX, image, and cloze rendering.",
        deck="Ankify Demo",
        rounds=[CardSet(source=source, cards=CARDS, round=0)],
    )
    SessionStore(".cards/demo_session.json").save(session)
    print(f"wrote {len(CARDS)} demo cards -> .cards/demo_session.json")


if __name__ == "__main__":
    main()
