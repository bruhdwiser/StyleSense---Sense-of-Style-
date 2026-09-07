"""StyleSense AI — Feedback Engine API Router.

Exposes endpoints to ingest asynchronous interaction events (click, save, like, dismiss, rating)
that update StyleDNA weights in real-time.
Specified in static_implementation.md Section 6.
"""

from typing import Optional
from fastapi import APIRouter, Depends, status, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    EventBatchRequest,
    EventBatchResponse,
    EventItem,
)
from app.services.feedback import (
    ingest_event_batch,
    get_session_events,
)
from app.workers.tasks import process_single_event_sync

router = APIRouter(tags=["Feedback Engine"])

@router.post(
    "/events",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EventBatchResponse,
    summary="Asynchronously ingest user interaction events",
)
def ingest_events_endpoint(
    payload: EventBatchRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Primary event ingestion endpoint.

    Persists raw interaction events idempotently and returns 202 Accepted immediately.
    Weight updates happen in the background worker pipeline.
    """
    response.status_code = status.HTTP_202_ACCEPTED

    events_data = [e.model_dump() for e in payload.events]
    accepted_count = ingest_event_batch(
        session_id=payload.session_id,
        events=events_data,
        user_id=payload.user_id,
        db=db,
        async_mode=True,
    )

    return EventBatchResponse(
        accepted=accepted_count,
        message="Events successfully queued for async StyleDNA processing",
    )

@router.get(
    "/events",
    summary="Query logged events for a session",
)
def get_events_endpoint(
    session_id: str = Query(..., description="Session ID to inspect events for"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Inspects recent interaction events recorded for a session."""
    events = get_session_events(session_id=session_id, db=db, limit=limit)
    return {"session_id": session_id, "events": events, "count": len(events)}

@router.post(
    "/feedback/process-sync",
    summary="Synchronously process an event (for offline loops or testing)",
)
def process_sync_endpoint(payload: EventItem):
    """Processes a single event synchronously, updating StyleDNA and writing analytics record."""
    result = process_single_event_sync(payload.model_dump())
    return result
