"""StyleSense AI — Recommendation Engine API Router.

Exposes endpoints to generate ranked, explained, budget-respecting outfit recommendations.
Specified in static_implementation.md Section 5.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    OutfitRecommendation,
    RecommendedItem,
)
from app.services.recommendation import (
    recommend_outfits,
    generate_candidates,
)

router = APIRouter(prefix="/recommendations", tags=["Recommendation Engine"])

@router.post(
    "",
    response_model=RecommendationResponse,
    summary="Generate ranked, rule-checked outfit recommendations",
)
def get_recommendations_endpoint(
    payload: RecommendationRequest,
    db: Session = Depends(get_db),
):
    """Generates top 3 distinct complete looks maximizing StyleDNA score subject to budget constraints."""
    outfits = recommend_outfits(
        occasion=payload.occasion,
        budget=payload.budget,
        climate=payload.climate,
        aesthetic=payload.aesthetic,
        user_id=payload.user_id,
        gender=payload.gender,
        include_wardrobe=payload.include_wardrobe,
        k=3,
        db=db,
    )

    outfit_schemas = [
        OutfitRecommendation(
            id=o.id,
            occasion=o.occasion,
            total_price=o.total_price,
            budget=o.budget,
            score=o.score,
            explanation=o.explanation,
            violations=o.violations,
            items=[
                RecommendedItem(
                    id=it.id,
                    name=it.name,
                    category=it.category,
                    role=it.role,
                    price=it.price,
                    brand=it.brand,
                    image_url=it.image_url,
                    retailer_url=it.retailer_url,
                    color_tags=it.color_tags,
                    style_tags=it.style_tags,
                    is_wardrobe_item=it.is_wardrobe_item,
                )
                for it in o.items
            ],
        )
        for o in outfits
    ]

    return RecommendationResponse(outfits=outfit_schemas, count=len(outfit_schemas))

@router.post(
    "/candidates",
    summary="Inspect raw 5-8 candidates before filtering/ranking",
)
def get_raw_candidates_endpoint(
    payload: RecommendationRequest,
    db: Session = Depends(get_db),
):
    """Returns unranked candidate looks generated before rule rejection and scoring.

    Useful for AI-evaluator grading and offline training episode generation.
    """
    candidates = generate_candidates(
        occasion=payload.occasion,
        budget=payload.budget,
        climate=payload.climate,
        aesthetic=payload.aesthetic,
        user_id=payload.user_id,
        gender=payload.gender,
        include_wardrobe=payload.include_wardrobe,
        db=db,
    )

    return {
        "candidates": [c.to_dict() for c in candidates],
        "count": len(candidates),
    }
