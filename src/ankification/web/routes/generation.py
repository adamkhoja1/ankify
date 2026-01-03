"""Card generation API routes with WebSocket support."""

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ...cards.generator import CardGenerator
from ...config import Config
from ...fetchers.manager import FetcherManager
from ...llm.manager import LLMManager
from ...storage.database import Database
from ..dependencies import get_config
from ..models.api import GenerateRequest
from ..websocket.manager import manager as ws_manager

router = APIRouter(prefix="/api/generate", tags=["generation"])

# Store active generation jobs
generation_jobs: dict[str, dict[str, Any]] = {}


@router.post("")
async def start_generation(
    request: GenerateRequest,
    config: Config = Depends(get_config),
) -> dict[str, str]:
    """Start an asynchronous card generation job.

    Args:
        request: Generation parameters
        config: Application config

    Returns:
        Job ID for tracking progress
    """
    job_id = str(uuid.uuid4())

    # Store job info
    generation_jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "progress": 0,
        "total": len(request.sources),
        "cards": [],
        "error": None,
    }

    # Start generation in background - it will manage its own db connection
    asyncio.create_task(
        _generate_cards_async(job_id, request, config)
    )

    return {
        "job_id": job_id,
        "message": "Generation started",
        "ws_url": f"/ws/generate/{job_id}",
    }


@router.get("/{job_id}")
async def get_generation_status(job_id: str) -> dict[str, Any]:
    """Get the status of a generation job.

    Args:
        job_id: Job ID

    Returns:
        Job status and progress
    """
    if job_id not in generation_jobs:
        return {"error": "Job not found"}

    return generation_jobs[job_id]


@router.websocket("/ws/{job_id}")
async def generation_websocket(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint for real-time generation progress.

    Args:
        websocket: WebSocket connection
        job_id: Generation job ID
    """
    await ws_manager.connect(websocket, job_id)

    try:
        # Send initial status
        if job_id in generation_jobs:
            await ws_manager.send_message(generation_jobs[job_id], job_id)

        # Keep connection alive and send updates
        while True:
            # Wait for messages (ping/pong to keep alive)
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except TimeoutError:
                # Send current status
                if job_id in generation_jobs:
                    await ws_manager.send_message(generation_jobs[job_id], job_id)

                # Check if job is complete
                if (
                    job_id in generation_jobs
                    and generation_jobs[job_id]["status"] in ["complete", "error"]
                ):
                    break

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, job_id)
    except Exception:
        ws_manager.disconnect(websocket, job_id)


async def _generate_cards_async(
    job_id: str, request: GenerateRequest, config: Config
) -> None:
    """Background task to generate cards.

    Args:
        job_id: Job ID for tracking
        request: Generation parameters
        config: Application config
    """
    try:
        # Update status to generating
        generation_jobs[job_id]["status"] = "generating"
        await ws_manager.send_message(generation_jobs[job_id], job_id)

        # Create our own database connection for the background task
        db = Database(config.storage.database_path)
        await db.connect()

        try:
            # Create generator
            fetcher_manager = FetcherManager()
            llm_manager = LLMManager(config)
            generator = CardGenerator(config, db, fetcher_manager, llm_manager)

            # Create session
            session_id = await db.create_session(
                sources=request.sources,
                provider=request.provider,
                card_types=[ct.value for ct in request.card_types],
                count_guidance=request.count_guidance,
            )

            generation_jobs[job_id]["session_id"] = session_id

            # Process each source
            all_cards = []
            for i, source in enumerate(request.sources):
                # Update progress
                generation_jobs[job_id]["progress"] = i
                total = len(request.sources)
                generation_jobs[job_id]["message"] = f"Processing source {i + 1}/{total}: {source}"
                await ws_manager.send_message(generation_jobs[job_id], job_id)

                try:
                    # Generate cards from this source
                    cards = await generator.generate_from_source(
                        source=source,
                        provider=request.provider,
                        card_types=[ct.value for ct in request.card_types],
                        count_guidance=request.count_guidance,
                    )

                    # Add tags
                    for card in cards:
                        card.tags.extend(request.tags)

                    # Save cards
                    for card in cards:
                        await db.save_card(card)
                        await db.add_card_to_session(session_id, card.id)

                    all_cards.extend(cards)

                    # Update job with new cards
                    from ..models.api import CardResponse

                    generation_jobs[job_id]["cards"] = [
                        CardResponse.from_card(c).model_dump() for c in all_cards
                    ]
                    await ws_manager.send_message(generation_jobs[job_id], job_id)

                except Exception as e:
                    # Log error but continue with other sources
                    generation_jobs[job_id]["message"] = f"Error processing {source}: {str(e)}"
                    await ws_manager.send_message(generation_jobs[job_id], job_id)

            # Complete session
            await db.complete_session(session_id)

            # Mark job as complete
            generation_jobs[job_id]["status"] = "complete"
            generation_jobs[job_id]["progress"] = len(request.sources)
            generation_jobs[job_id]["message"] = f"Generated {len(all_cards)} cards"
            await ws_manager.send_message(generation_jobs[job_id], job_id)

        finally:
            # Always close the database connection
            await db.close()

    except Exception as e:
        # Mark job as error
        generation_jobs[job_id]["status"] = "error"
        generation_jobs[job_id]["error"] = str(e)
        generation_jobs[job_id]["message"] = f"Generation failed: {str(e)}"
        await ws_manager.send_message(generation_jobs[job_id], job_id)
