"""LLM refinement API routes."""

from fastapi import APIRouter, Depends, HTTPException

from ...cards.models import BasicCard, ClozeCard
from ...config import Config
from ...llm.manager import LLMManager
from ...storage.database import Database
from ..dependencies import get_config, get_db
from ..models.api import CardResponse, RefineRequest

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.post("/refine", response_model=CardResponse)
async def refine_card(
    request: RefineRequest,
    db: Database = Depends(get_db),
    config: Config = Depends(get_config),
) -> CardResponse:
    """Refine a card using LLM feedback.

    Args:
        request: Card ID and feedback
        db: Database connection
        config: Application config

    Returns:
        Refined card

    Raises:
        HTTPException: If card not found or refinement fails
    """
    # Get the card
    card = await db.get_card(request.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Get LLM provider
    llm_manager = LLMManager(config)
    provider = llm_manager.get_provider("openai")  # Default to openai for refinement

    try:
        # Store original content for history
        old_content = card.to_json()

        # Refine the card
        refined = await provider.refine_card(card=card, feedback=request.feedback)

        # Update card with refined content
        if isinstance(card, BasicCard) and isinstance(refined, BasicCard):
            card.front = refined.front
            card.back = refined.back
        elif isinstance(card, ClozeCard) and isinstance(refined, ClozeCard):
            card.text = refined.text

        # Save refined card
        await db.save_card(card)

        # Record edit in history
        await db.record_edit(
            card_id=card.id,
            old_content=old_content,
            new_content=card.to_json(),
            edit_type="llm_refine",
            feedback=request.feedback,
        )

        return CardResponse.from_card(card)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Refinement failed: {str(e)}"
        ) from e
