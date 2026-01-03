"""Session management API routes."""


from fastapi import APIRouter, Depends, HTTPException

from ...cards.models import CardStatus
from ...storage.database import Database
from ..dependencies import get_db
from ..models.api import CardResponse, SessionResponse

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionResponse])
async def list_sessions(db: Database = Depends(get_db)) -> list[SessionResponse]:
    """List all generation sessions.

    Args:
        db: Database connection

    Returns:
        List of sessions with statistics
    """
    sessions = await db.get_sessions()
    response = []

    for session in sessions:
        cards = await db.get_cards_by_session(session["id"])

        # Calculate statistics
        accepted = sum(1 for c in cards if c.status == CardStatus.ACCEPTED)
        rejected = sum(1 for c in cards if c.status == CardStatus.REJECTED)
        pending = sum(1 for c in cards if c.status == CardStatus.DRAFT)

        response.append(
            SessionResponse(
                id=session["id"],
                sources=session["sources"].split(","),
                provider=session["provider"],
                card_types=session["card_types"].split(","),
                count_guidance=session["count_guidance"],
                created_at=session["created_at"],
                completed_at=session["completed_at"],
                card_count=len(cards),
                accepted_count=accepted,
                rejected_count=rejected,
                pending_count=pending,
            )
        )

    return response


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: Database = Depends(get_db)) -> SessionResponse:
    """Get a single session by ID.

    Args:
        session_id: Session ID
        db: Database connection

    Returns:
        Session data with statistics

    Raises:
        HTTPException: If session not found
    """
    sessions = await db.get_sessions()
    session = next((s for s in sessions if s["id"] == session_id), None)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    cards = await db.get_cards_by_session(session_id)

    # Calculate statistics
    accepted = sum(1 for c in cards if c.status == CardStatus.ACCEPTED)
    rejected = sum(1 for c in cards if c.status == CardStatus.REJECTED)
    pending = sum(1 for c in cards if c.status == CardStatus.DRAFT)

    return SessionResponse(
        id=session["id"],
        sources=session["sources"].split(","),
        provider=session["provider"],
        card_types=session["card_types"].split(","),
        count_guidance=session["count_guidance"],
        created_at=session["created_at"],
        completed_at=session["completed_at"],
        card_count=len(cards),
        accepted_count=accepted,
        rejected_count=rejected,
        pending_count=pending,
    )


@router.get("/{session_id}/cards", response_model=list[CardResponse])
async def get_session_cards(
    session_id: str, db: Database = Depends(get_db)
) -> list[CardResponse]:
    """Get all cards for a session.

    Args:
        session_id: Session ID
        db: Database connection

    Returns:
        List of cards in the session

    Raises:
        HTTPException: If session not found
    """
    cards = await db.get_cards_by_session(session_id)
    if not cards:
        # Check if session exists
        sessions = await db.get_sessions()
        if not any(s["id"] == session_id for s in sessions):
            raise HTTPException(status_code=404, detail="Session not found")

    return [CardResponse.from_card(card) for card in cards]


@router.delete("/{session_id}")
async def delete_session(session_id: str, db: Database = Depends(get_db)) -> dict[str, str]:
    """Delete a session and all its cards.

    Args:
        session_id: Session ID
        db: Database connection

    Returns:
        Success message

    Raises:
        HTTPException: If session not found
    """
    # First check if session exists
    sessions = await db.get_sessions()
    if not any(s["id"] == session_id for s in sessions):
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete all cards in the session
    cards = await db.get_cards_by_session(session_id)
    for card in cards:
        await db.delete_card(card.id)

    # Delete the session (we'll need to add this method)
    await db.delete_session(session_id)

    return {"message": "Session deleted successfully"}
