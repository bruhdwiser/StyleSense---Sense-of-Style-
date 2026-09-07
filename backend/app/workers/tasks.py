"""StyleSense AI — Background Worker Tasks.

Asynchronous event processing via Celery with synchronous fallback.
Executes idempotency checks, event persistence, StyleDNA weight updates,
and analytics interaction recording.
Specified in static_implementation.md Section 6.2.
"""

import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from celery import Celery

from app.config import settings
from app.database import SessionLocal
from app.models import InteractionEvent, Interaction, Product, Outfit, StyleDNA
from app.services.styledna import apply_event_feedback

celery_app = Celery(
    "stylesense_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.CELERY_ALWAYS_EAGER,
    broker_connection_retry=False,
    broker_connection_retry_on_startup=False,
    broker_connection_timeout=1.0,
)

def compute_idempotency_key(
    user_id: str,
    session_id: str,
    event_type: str,
    target_id: str,
    timestamp_str: Optional[str] = None,
) -> str:
    """Generates sha256(user_id + session_id + event_type + target_id + timestamp)."""
    ts = timestamp_str or datetime.now(timezone.utc).isoformat()
    raw = f"{user_id}:{session_id}:{event_type}:{target_id}:{ts}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def process_single_event_sync(event_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Core synchronous logic to process a single event:

    1. Idempotency check
    2. Persist raw event
    3. Look up target tags
    4. Apply StyleDNA weight update
    5. Save Interaction record for analytics
    """
    db = SessionLocal()
    try:
        idempotency_key = event_payload.get("idempotency_key")
        user_id = event_payload.get("user_id", "demo_user")
        session_id = event_payload.get("session_id", "default_session")
        event_type = event_payload.get("event_type", "click")
        target_type = event_payload.get("target_type", "product")
        target_id = str(event_payload.get("target_id", ""))
        payload = event_payload.get("payload", {})

        if not idempotency_key:
            idempotency_key = compute_idempotency_key(user_id, session_id, event_type, target_id)

        existing = db.query(InteractionEvent).filter(
            InteractionEvent.idempotency_key == idempotency_key
        ).first()

        if existing and existing.processed:
            return {"status": "skipped", "reason": "duplicate_idempotency_key"}

        if not existing:

            event_record = InteractionEvent(
                user_id=user_id,
                session_id=session_id,
                event_type=event_type,
                target_type=target_type,
                target_id=target_id,
                payload=payload,
                idempotency_key=idempotency_key,
                processed=False,
            )
            db.add(event_record)
            db.commit()
            db.refresh(event_record)
        else:
            event_record = existing

        target_tags: List[str] = []
        if target_type == "product":
            product = db.query(Product).filter(Product.id == target_id).first()
            if product:
                target_tags = list(product.style_tags or []) + list(product.color_tags or []) + list(product.occasion_tags or [])
        elif target_type == "outfit":
            outfit = db.query(Outfit).filter(Outfit.id == target_id).first()
            if outfit:
                for item in outfit.items:
                    if item.product:
                        target_tags.extend(item.product.style_tags or [])
                        target_tags.extend(item.product.color_tags or [])
                target_tags = list(set(target_tags))

        updated_dna = apply_event_feedback(
            user_id=user_id,
            event_type=event_type,
            target_tags=target_tags,
            payload=payload,
            db=db,
        )

        interaction = Interaction(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            action=event_type,
            payload=payload,
        )
        db.add(interaction)

        event_record.processed = True
        db.commit()

        return {
            "status": "processed",
            "idempotency_key": idempotency_key,
            "user_id": user_id,
            "dna_version": updated_dna.version,
        }
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3)
def process_event_task(self, event_payload: Dict[str, Any]):
    """Celery async task wrapper with retry support."""
    try:
        return process_single_event_sync(event_payload)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
