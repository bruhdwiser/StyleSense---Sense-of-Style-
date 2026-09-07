"""StyleSense AI — Feedback Engine Service & Ingestion Pipeline.
Handles event batching, deduplication, and async task delegation.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models import InteractionEvent
from app.workers.tasks import (
    process_event_task,
    process_single_event_sync,
    compute_idempotency_key,
)

def ingest_event_batch(
    session_id: str,
    events: List[Dict[str, Any]],
    user_id: Optional[str] = None,
    db: Optional[Session] = None,
    async_mode: bool = True,
) -> int:
    """Ingests a batch of user interaction events.

    Persists events, returns count accepted, and dispatches processing
    without blocking the caller.
    """
    accepted_count = 0
    effective_user_id = user_id or "demo_user"

    for event_data in events:
        event_dict = dict(event_data)
        event_dict["session_id"] = session_id
        event_dict["user_id"] = event_dict.get("user_id") or effective_user_id

        if not event_dict.get("idempotency_key"):
            event_dict["idempotency_key"] = compute_idempotency_key(
                user_id=event_dict["user_id"],
                session_id=session_id,
                event_type=event_dict.get("event_type", "click"),
                target_id=str(event_dict.get("target_id", "")),
            )

        if async_mode and not settings.CELERY_ALWAYS_EAGER:
            try:

                task_caller: Any = process_event_task
                task_caller.delay(event_dict)
            except Exception:

                process_single_event_sync(event_dict)
        else:
            process_single_event_sync(event_dict)

        accepted_count += 1

    return accepted_count

def get_session_events(
    session_id: str,
    db: Session,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Fetches recent events logged for a specific session."""
    records = (
        db.query(InteractionEvent)
        .filter(InteractionEvent.session_id == session_id)
        .order_by(InteractionEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "session_id": r.session_id,
            "user_id": r.user_id,
            "event_type": r.event_type,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "payload": r.payload,
            "processed": r.processed,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
