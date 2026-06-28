"""One-off recovery: restore pending cards dropped by the old regenerate behavior.

Rebuilds the current round as carried(prev) + the new cards the regenerate added, where
carried = pending + accepted + edited (discards dropped). Run once:
  uv run scripts/restore_regen.py
"""

import fire  # type: ignore[import-untyped]

from ankify.models import ReviewAction
from ankify.server.session import SessionStore


def main(session_path: str = ".cards/varian_session.json") -> None:
    store = SessionStore(session_path)
    session = store.load()
    if len(session.rounds) < 2:
        print("nothing to restore (need >= 2 rounds)")
        return

    prev, cur = session.rounds[-2], session.rounds[-1]
    prev_ids = {c.id for c in prev.cards}
    new_cards = [c for c in cur.cards if c.id not in prev_ids]

    carried = []
    for card in prev.cards:
        decision = session.decisions.get(card.id)
        if decision is None or decision.action is ReviewAction.ACCEPT:
            carried.append(card)
        elif decision.action is ReviewAction.EDIT:
            carried.append(decision.edited_card or card)
        # DISCARD: dropped

    cur.cards = carried + new_cards
    store.save(session)
    print(
        f"restored: current round now has {len(cur.cards)} cards "
        f"({len(carried)} carried + {len(new_cards)} new); pending={session.pending_count()}"
    )


if __name__ == "__main__":
    fire.Fire(main)
