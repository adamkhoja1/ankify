"""One-off: convert existing 'edit' decisions to 'accept' (edited content applied in place).

Edits are no longer a distinct state — a saved edit is just an accept of the edited card.
This migrates an existing session. Run: uv run scripts/edits_to_accepts.py
"""

import fire  # type: ignore[import-untyped]

from ankification.models import ReviewAction, ReviewDecision
from ankification.server.session import SessionStore


def main(session_path: str = ".cards/varian_session.json") -> None:
    store = SessionStore(session_path)
    session = store.load()
    current = session.current
    converted = 0
    for card_id, decision in list(session.decisions.items()):
        if decision.action is not ReviewAction.EDIT:
            continue
        if decision.edited_card is not None and current is not None:
            updated = decision.edited_card.model_copy(update={"id": card_id})
            for i, card in enumerate(current.cards):
                if card.id == card_id:
                    current.cards[i] = updated
                    break
        session.decisions[card_id] = ReviewDecision(
            card_id=card_id, action=ReviewAction.ACCEPT, feedback=decision.feedback
        )
        converted += 1
    store.save(session)
    print(f"converted {converted} edit decisions to accept")


if __name__ == "__main__":
    fire.Fire(main)
