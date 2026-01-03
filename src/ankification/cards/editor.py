"""Card editing logic."""

from ..storage.database import Database
from .models import BasicCard, Card, ClozeCard


class CardEditor:
    """Handles manual card editing."""

    def __init__(self, database: Database, keep_history: bool = True) -> None:
        """Initialize card editor.

        Args:
            database: Database instance
            keep_history: Whether to keep edit history
        """
        self.database = database
        self.keep_history = keep_history

    async def edit_basic_card(
        self, card_id: str, front: str | None = None, back: str | None = None
    ) -> Card:
        """Edit a basic card.

        Args:
            card_id: Card ID
            front: New front text (None to keep unchanged)
            back: New back text (None to keep unchanged)

        Returns:
            Updated card

        Raises:
            ValueError: If card not found or not a basic card
        """
        card = await self.database.get_card(card_id)
        if not card:
            raise ValueError(f"Card not found: {card_id}")

        if not isinstance(card, BasicCard):
            raise ValueError(f"Card {card_id} is not a basic card")

        # Store old version
        old_content = card.to_json()

        # Update fields
        if front is not None:
            card.front = front.strip()
        if back is not None:
            card.back = back.strip()

        card.mark_modified()

        # Save updated card
        await self.database.save_card(card)

        # Record edit history
        if self.keep_history:
            await self.database.record_edit(
                card_id=card_id,
                old_content=old_content,
                new_content=card.to_json(),
                edit_type="manual",
                feedback=None,
            )

        return card

    async def edit_cloze_card(self, card_id: str, text: str) -> Card:
        """Edit a cloze card.

        Args:
            card_id: Card ID
            text: New cloze text

        Returns:
            Updated card

        Raises:
            ValueError: If card not found or not a cloze card
        """
        card = await self.database.get_card(card_id)
        if not card:
            raise ValueError(f"Card not found: {card_id}")

        if not isinstance(card, ClozeCard):
            raise ValueError(f"Card {card_id} is not a cloze card")

        # Store old version
        old_content = card.to_json()

        # Update text
        card.text = text.strip()
        card.mark_modified()

        # Save updated card
        await self.database.save_card(card)

        # Record edit history
        if self.keep_history:
            await self.database.record_edit(
                card_id=card_id,
                old_content=old_content,
                new_content=card.to_json(),
                edit_type="manual",
                feedback=None,
            )

        return card

    async def update_tags(self, card_id: str, tags: list[str]) -> Card:
        """Update card tags.

        Args:
            card_id: Card ID
            tags: New list of tags

        Returns:
            Updated card

        Raises:
            ValueError: If card not found
        """
        card = await self.database.get_card(card_id)
        if not card:
            raise ValueError(f"Card not found: {card_id}")

        # Update tags
        card.tags = [tag.strip() for tag in tags]
        card.mark_modified()

        # Save updated card
        await self.database.save_card(card)

        return card

    async def add_tag(self, card_id: str, tag: str) -> Card:
        """Add a tag to a card.

        Args:
            card_id: Card ID
            tag: Tag to add

        Returns:
            Updated card

        Raises:
            ValueError: If card not found
        """
        card = await self.database.get_card(card_id)
        if not card:
            raise ValueError(f"Card not found: {card_id}")

        tag = tag.strip()
        if tag and tag not in card.tags:
            card.tags.append(tag)
            card.mark_modified()
            await self.database.save_card(card)

        return card

    async def remove_tag(self, card_id: str, tag: str) -> Card:
        """Remove a tag from a card.

        Args:
            card_id: Card ID
            tag: Tag to remove

        Returns:
            Updated card

        Raises:
            ValueError: If card not found
        """
        card = await self.database.get_card(card_id)
        if not card:
            raise ValueError(f"Card not found: {card_id}")

        tag = tag.strip()
        if tag in card.tags:
            card.tags.remove(tag)
            card.mark_modified()
            await self.database.save_card(card)

        return card
