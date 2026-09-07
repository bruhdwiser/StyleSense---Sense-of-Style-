"""StyleSense AI — StyleDNA Engine API Router.

Exposes endpoints to compute, retrieve, and inspect user taste profiles.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StyleDNA, Profile
from app.schemas import (
    StyleDNASummary,
    StyleDNAComputeRequest,
)
from app.services.styledna import (
    compute_style_dna,
    get_style_dna_summary,
)

router = APIRouter(prefix="/styledna", tags=["StyleDNA Engine"])

@router.get("/{user_id}", summary="Get full StyleDNA profile for a user")
def get_user_styledna(user_id: str, db: Session = Depends(get_db)):
    dna = db.query(StyleDNA).filter(StyleDNA.user_id == user_id).first()
    if not dna:
        raise HTTPException(status_code=404, detail="StyleDNA not found for this user")

    return {
        "id": dna.id,
        "user_id": dna.user_id,
        "version": dna.version,
        "weights": dna.weights,
        "dominant_tags": dna.dominant_tags,
        "summary": dna.summary,
        "updated_at": dna.updated_at.isoformat() if dna.updated_at else None,
    }

@router.get("/{user_id}/summary", summary="Get plain-language StyleDNA summary")
def get_user_styledna_summary(user_id: str, db: Session = Depends(get_db)):
    return get_style_dna_summary(user_id=user_id, db=db)

@router.post("/compute", summary="Compute or re-compute StyleDNA from preferences")
def compute_user_styledna(payload: StyleDNAComputeRequest, db: Session = Depends(get_db)):

    class TransientProfile:
        def __init__(self, req: StyleDNAComputeRequest):
            self.user_id = req.user_id
            self.aesthetics = req.aesthetics
            self.favorite_colors = req.favorite_colors
            self.preferred_fit = req.preferred_fit
            self.body_type = req.body_type

    profile_obj = TransientProfile(payload)
    dna = compute_style_dna(profile=profile_obj, db=db)

    return {
        "user_id": dna.user_id,
        "version": dna.version,
        "dominant_tags": dna.dominant_tags,
        "summary": dna.summary,
        "weights": dna.weights,
        "updated_at": dna.updated_at.isoformat() if dna.updated_at else None,
    }
