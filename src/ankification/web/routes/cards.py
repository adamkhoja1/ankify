"""Card management API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query

from ...cards.editor import CardEditor
from ...cards.models import Card, CardStatus, card_from_dict
from ...storage.database import Database
from ..dependencies import get_db
from ..models.api import CardFilters, CardResponse, CardUpdate, StatusUpdate

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.get("", response_model=list[CardResponse])
async def list_cards(
    status: CardStatus | None = Query(None),
    session_id: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Database = Depends(get_db),
) -> list[CardResponse]:
    """List cards with optional filtering.

    Args:
        status: Filter by card status
        session_id: Filter by session ID
        search: Search in card content
        limit: Maximum number of cards to return
        offset: Number of cards to skip
        db: Database connection

    Returns:
        List of cards matching filters
    """
    if session_id:
        cards = await db.get_cards_by_session(session_id)
    elif status:
        cards = await db.get_cards_by_status(status)
    else:
        # Get all cards - we'll need to add this method to Database
        cards = await db.get_all_cards()

    # Apply search filter if provided
    if search:
        search_lower = search.lower()
        cards = [
            c
            for c in cards
            if search_lower in c.to_dict().get("front", "").lower()
            or search_lower in c.to_dict().get("back", "").lower()
            or search_lower in c.to_dict().get("text", "").lower()
        ]

    # Apply pagination
    cards = cards[offset : offset + limit]

    return [CardResponse.from_card(card) for card in cards]


@router.get("/{card_id}", response_model=CardResponse)
async def get_card(card_id: str, db: Database = Depends(get_db)) -> CardResponse:
    """Get a single card by ID.

    Args:
        card_id: Card ID
        db: Database connection

    Returns:
        Card data

    Raises:
        HTTPException: If card not found
    """
    card = await db.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return CardResponse.from_card(card)


@router.put("/{card_id}", response_model=CardResponse)
async def update_card(
    card_id: str, update: CardUpdate, db: Database = Depends(get_db)
) -> CardResponse:
    """Update a card's content.

    Args:
        card_id: Card ID
        update: Fields to update
        db: Database connection

    Returns:
        Updated card data

    Raises:
        HTTPException: If card not found
    """
    card = await db.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    editor = CardEditor(db)

    # Update fields based on card type
    if hasattr(card, "front") and update.front is not None:
        card = await editor.edit_basic_card(
            card, front=update.front, back=update.back or card.back
        )
    elif hasattr(card, "text") and update.text is not None:
        card = await editor.edit_cloze_card(card, text=update.text)

    # Update tags if provided
    if update.tags is not None:
        card.tags = update.tags
        await db.save_card(card)

    return CardResponse.from_card(card)


@router.patch("/{card_id}/status", response_model=CardResponse)
async def update_card_status(
    card_id: str, status_update: StatusUpdate, db: Database = Depends(get_db)
) -> CardResponse:
    """Update a card's status (accept/reject).

    Args:
        card_id: Card ID
        status_update: New status
        db: Database connection

    Returns:
        Updated card data

    Raises:
        HTTPException: If card not found
    """
    card = await db.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    card.status = status_update.status
    await db.save_card(card)

    return CardResponse.from_card(card)


@router.delete("/{card_id}")
async def delete_card(card_id: str, db: Database = Depends(get_db)) -> dict:
    """Delete a card.

    Args:
        card_id: Card ID
        db: Database connection

    Returns:
        Success message

    Raises:
        HTTPException: If card not found
    """
    card = await db.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    await db.delete_card(card_id)
    return {"message": "Card deleted successfully"}
