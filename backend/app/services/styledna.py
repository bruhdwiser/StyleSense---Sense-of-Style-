"""StyleSense AI — StyleDNA Engine.

Calculates and updates per-user taste profiles as live tag-weight maps.
Implements event feedback nudges, weight clipping, dominant tag caching,
and plain-language persona summary generation.
Specified in static_implementation.md Section 3.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.models import StyleDNA, Profile, Product, Outfit
from app.models.tag_vocabulary import ALL_VOCABULARY_TAGS

EVENT_WEIGHT_DELTAS: Dict[str, float] = {
    "like": 0.1,
    "save": 0.1,
    "dismiss": -0.1,
    "rating_high": 0.1,
    "rating_low": -0.1,
    "rating_mid": 0.0,
    "click": 0.02,
    "impression": 0.0,
    "wardrobe_add": 0.05,
}

WEIGHT_MIN: float = 0.0
WEIGHT_MAX: float = 3.0
DEFAULT_SEED_WEIGHT: float = 1.0

def _get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

def generate_persona_summary(dominant_tags: List[str], weights: Dict[str, float]) -> str:
    """Generates an intuitive, user-friendly persona summary string from top tags."""
    if not dominant_tags:
        return "Your style profile is still developing. Start exploring and liking looks to shape your StyleDNA!"

    top_3 = dominant_tags[:3]
    top_str = ", ".join(top_3)

    return f"You lean toward {top_str} aesthetics with a curated eye for balanced, versatile essentials."

def compute_style_dna(
    profile: Any,
    db: Optional[Session] = None,
) -> StyleDNA:
    """Computes and seeds a StyleDNA record from a user profile.

    Seeds 1.0 for each selected aesthetic, color, fit, and silhouette tag.
    """
    weights: Dict[str, float] = {}

    aesthetics = getattr(profile, "aesthetics", []) or []
    for tag in aesthetics:
        clean_tag = str(tag).lower().strip()
        weights[clean_tag] = DEFAULT_SEED_WEIGHT

    colors = getattr(profile, "favorite_colors", []) or []
    for tag in colors:
        clean_tag = str(tag).lower().strip()
        weights[clean_tag] = DEFAULT_SEED_WEIGHT

    preferred_fit = getattr(profile, "preferred_fit", None)
    if preferred_fit:
        clean_fit = str(preferred_fit).lower().strip()
        weights[clean_fit] = DEFAULT_SEED_WEIGHT

    body_type = getattr(profile, "body_type", None)
    if body_type:
        clean_body = str(body_type).lower().strip()
        weights[clean_body] = DEFAULT_SEED_WEIGHT

    sorted_tags = sorted(weights.keys(), key=lambda t: weights[t], reverse=True)
    dominant_tags = sorted_tags[:5]
    summary_text = generate_persona_summary(dominant_tags, weights)

    user_id = getattr(profile, "user_id", None) or getattr(profile, "id", "demo_user")

    style_dna = StyleDNA(
        user_id=user_id,
        version=1,
        weights=weights,
        dominant_tags=dominant_tags,
        dominant_aesthetics=[t for t in dominant_tags if t in aesthetics],
        color_palette=[t for t in dominant_tags if t in colors],
        summary=summary_text,
        updated_at=_get_utc_now(),
    )

    if db is not None:

        existing = db.query(StyleDNA).filter(StyleDNA.user_id == user_id).first()
        if existing:
            existing.version += 1
            existing.weights = weights
            existing.dominant_tags = dominant_tags
            existing.summary = summary_text
            existing.updated_at = _get_utc_now()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            db.add(style_dna)
            db.commit()
            db.refresh(style_dna)

    return style_dna

def get_delta_for_event(event_type: str, payload: Optional[Dict[str, Any]] = None) -> float:
    """Determines weight delta according to event type and payload (e.g. ratings)."""
    clean_type = event_type.lower().strip()

    if clean_type == "rating":
        rating_val = 3
        if payload and "rating" in payload:
            try:
                rating_val = int(payload["rating"])
            except (ValueError, TypeError):
                rating_val = 3

        if rating_val >= 4:
            return EVENT_WEIGHT_DELTAS["rating_high"]
        elif rating_val <= 2:
            return EVENT_WEIGHT_DELTAS["rating_low"]
        else:
            return EVENT_WEIGHT_DELTAS["rating_mid"]

    return EVENT_WEIGHT_DELTAS.get(clean_type, 0.0)

def apply_event_feedback(
    user_id: str,
    event_type: str,
    target_tags: List[str],
    payload: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
    style_dna_instance: Optional[StyleDNA] = None,
) -> StyleDNA:
    """Applies weight deltas to target tags, clips weights to [0.0, 3.0],

    bumps version, refreshes dominant tags and summary, and persists atomically.
    """
    delta = get_delta_for_event(event_type, payload)

    dna = style_dna_instance
    if dna is None and db is not None:
        dna = db.query(StyleDNA).filter(StyleDNA.user_id == user_id).first()

    if dna is None:

        dna = StyleDNA(
            user_id=user_id,
            version=1,
            weights={},
            dominant_tags=[],
            summary="",
            updated_at=_get_utc_now(),
        )
        if db is not None:
            db.add(dna)

    current_weights: Dict[str, float] = dict(dna.weights or {})

    if delta != 0.0 and target_tags:
        for tag in target_tags:
            clean_tag = str(tag).lower().strip()
            if not clean_tag:
                continue
            old_w = current_weights.get(clean_tag, DEFAULT_SEED_WEIGHT)
            new_w = round(max(WEIGHT_MIN, min(WEIGHT_MAX, old_w + delta)), 4)
            current_weights[clean_tag] = new_w

    dna.weights = current_weights
    dna.version = (dna.version or 0) + 1

    sorted_tags = sorted(current_weights.keys(), key=lambda t: current_weights[t], reverse=True)
    dna.dominant_tags = sorted_tags[:5]
    dna.summary = generate_persona_summary(dna.dominant_tags, current_weights)
    dna.updated_at = _get_utc_now()

    if db is not None:
        db.commit()
        db.refresh(dna)

    return dna

def get_style_dna_summary(user_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
    """Retrieves top tags, persona summary, and weights for the user."""
    dna = None
    if db is not None:
        dna = db.query(StyleDNA).filter(StyleDNA.user_id == user_id).first()

    if dna is None:
        return {
            "user_id": user_id,
            "version": 0,
            "dominant_tags": [],
            "summary": "No StyleDNA profile found. Complete onboarding to generate your profile.",
            "weights": {},
            "updated_at": _get_utc_now().isoformat(),
        }

    return {
        "user_id": dna.user_id,
        "version": dna.version,
        "dominant_tags": dna.dominant_tags or [],
        "summary": dna.summary or "",
        "weights": dna.weights or {},
        "updated_at": dna.updated_at.isoformat() if dna.updated_at else _get_utc_now().isoformat(),
    }
