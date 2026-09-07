"""StyleSense AI — Rule Engine API Router.

Exposes endpoints to validate candidate outfits against deterministic rules
(budget, completeness, occasion/climate compatibility, unique roles).
Specified in static_implementation.md Section 4.
"""

from typing import List, Dict, Any
from fastapi import APIRouter
from app.schemas import (
    OutfitValidationRequest,
    RuleEnvelopeResponse,
    RuleResult as RuleResultSchema,
    RuleInfo,
)
from app.services.rule_engine import (
    check_outfit,
    REQUIRED_ROLES,
    ALLOWED_ROLES,
)

router = APIRouter(prefix="/rules", tags=["Rule Engine"])

@router.post(
    "/validate-outfit",
    response_model=RuleEnvelopeResponse,
    summary="Validate an outfit against all deterministic hard rules",
)
def validate_outfit_endpoint(payload: OutfitValidationRequest):
    """Evaluates an outfit against budget, completeness, occasion/climate, and role uniqueness.

    Returns whether the look passed and lists any specific violation reasons.
    """
    total_price = sum(item.price for item in payload.items)

    envelope = check_outfit(
        items=payload.items,
        budget=payload.budget,
        occasion=payload.occasion,
        climate=payload.climate,
        total_price=total_price,
    )

    return RuleEnvelopeResponse(
        passed=envelope.passed,
        violations=envelope.violations,
        details=[
            RuleResultSchema(
                name=d.name,
                passed=d.passed,
                reason=d.reason,
            )
            for d in envelope.details
        ],
    )

@router.get(
    "/list",
    response_model=List[RuleInfo],
    summary="List all active deterministic rules",
)
def list_rules_endpoint():
    """Introspects the rules and required roles enforced by the Rule Engine."""
    return [
        RuleInfo(
            name="budget_check",
            description="Ensures outfit total purchase price does not exceed requested budget (wardrobe reuses count as ₹0).",
        ),
        RuleInfo(
            name="completeness_check",
            description="Ensures outfit contains all necessary roles for a full look (top, bottom, and shoes).",
            required_roles=sorted(list(REQUIRED_ROLES)),
        ),
        RuleInfo(
            name="occasion_climate_check",
            description="Ensures at least one piece aligns with the requested occasion and weather/season.",
        ),
        RuleInfo(
            name="unique_roles_check",
            description="Enforces role uniqueness to eliminate duplicate item roles (e.g. two pairs of shoes or two bottoms).",
        ),
    ]
