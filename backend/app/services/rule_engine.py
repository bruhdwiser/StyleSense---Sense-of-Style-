"""StyleSense AI — Rule Engine.

Pure, deterministic functions with no side-effects that enforce business constraints
for outfit completeness, budget, occasion/climate compatibility, and role uniqueness.
Specified in static_implementation.md Section 4.
"""

from typing import List, Set, Dict, Any, Optional
from dataclasses import dataclass, field

REQUIRED_ROLES: Set[str] = {"top", "bottom", "shoes"}
ALLOWED_ROLES: Set[str] = {"top", "bottom", "shoes", "accessory", "outerwear"}

@dataclass
class RuleResult:
    name: str
    passed: bool
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "reason": self.reason,
        }

@dataclass
class RuleEnvelope:
    passed: bool
    violations: List[str] = field(default_factory=list)
    details: List[RuleResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": self.violations,
            "details": [d.to_dict() for d in self.details],
        }

def _get_item_role(item: Any) -> str:
    """Helper to extract role from dict, Pydantic model, or ORM model."""
    if isinstance(item, dict):
        return str(item.get("role", "")).lower()
    return str(getattr(item, "role", "")).lower()

def _get_item_price(item: Any) -> int:
    """Helper to extract price from dict, Pydantic model, or ORM model."""
    if isinstance(item, dict):
        return int(item.get("price", 0))

    if hasattr(item, "price"):
        return int(item.price)
    if hasattr(item, "product") and item.product is not None:
        return int(getattr(item.product, "price", 0))
    return 0

def _get_item_tags(item: Any, tag_field: str) -> List[str]:
    """Helper to extract tags (e.g. occasion_tags, season_tags, style_tags)."""
    if isinstance(item, dict):
        return [str(t).lower() for t in item.get(tag_field, [])]
    if hasattr(item, tag_field) and getattr(item, tag_field) is not None:
        return [str(t).lower() for t in getattr(item, tag_field)]
    if hasattr(item, "product") and item.product is not None:
        return [str(t).lower() for t in getattr(item.product, tag_field, [])]
    return []

def check_budget(outfit_total_price: int, budget: int) -> RuleResult:
    """Hard check: outfit total price must not exceed requested budget.

    Budget of 0 fails unless total_price is 0 (all wardrobe reuses).
    """
    if budget < 0:
        return RuleResult(
            name="budget_check",
            passed=False,
            reason=f"Invalid budget: ₹{budget} cannot be negative",
        )
    if outfit_total_price <= budget:
        return RuleResult(
            name="budget_check",
            passed=True,
            reason=None,
        )
    return RuleResult(
        name="budget_check",
        passed=False,
        reason=f"Budget exceeded: total cost ₹{outfit_total_price} exceeds budget of ₹{budget}",
    )

def check_completeness(items: List[Any]) -> RuleResult:
    """Hard check: a complete look must have top, bottom, and shoes.

    Accessory and outerwear are optional additions.
    """
    if not items:
        return RuleResult(
            name="completeness_check",
            passed=False,
            reason="Empty outfit: outfit contains no items",
        )

    present_roles = {_get_item_role(item) for item in items}
    missing = REQUIRED_ROLES - present_roles

    if not missing:
        return RuleResult(
            name="completeness_check",
            passed=True,
            reason=None,
        )

    missing_list = sorted(list(missing))
    return RuleResult(
        name="completeness_check",
        passed=False,
        reason=f"Incomplete outfit: missing required roles: {', '.join(missing_list)}",
    )

def check_occasion_climate(
    items: List[Any],
    occasion: Optional[str] = None,
    climate: Optional[str] = None,
) -> RuleResult:
    """Hard check: at least one item must be compatible with occasion and climate.

    If occasion or climate are not specified or generic, passes.
    """
    if not items:
        return RuleResult(
            name="occasion_climate_check",
            passed=False,
            reason="No items to evaluate for occasion or climate",
        )

    occasion_clean = occasion.lower().strip() if occasion else None
    climate_clean = climate.lower().strip() if climate else None

    if occasion_clean and occasion_clean != "all":

        occasion_matches = any(
            occasion_clean in _get_item_tags(item, "occasion_tags")
            or "casual" in _get_item_tags(item, "occasion_tags")
            or not _get_item_tags(item, "occasion_tags")
            for item in items
        )
        if not occasion_matches:
            return RuleResult(
                name="occasion_climate_check",
                passed=False,
                reason=f"Occasion mismatch: no items match requested occasion '{occasion}'",
            )

    if climate_clean and climate_clean != "all":
        climate_matches = any(
            climate_clean in _get_item_tags(item, "season_tags")
            or "all" in _get_item_tags(item, "season_tags")
            or not _get_item_tags(item, "season_tags")
            for item in items
        )
        if not climate_matches:
            return RuleResult(
                name="occasion_climate_check",
                passed=False,
                reason=f"Climate mismatch: no items match requested climate/season '{climate}'",
            )

    return RuleResult(
        name="occasion_climate_check",
        passed=True,
        reason=None,
    )

def check_unique_roles(items: List[Any]) -> RuleResult:
    """Hard check: each item in an outfit must fulfill a distinct role."""
    if not items:
        return RuleResult(
            name="unique_roles_check",
            passed=True,
            reason=None,
        )

    roles = [_get_item_role(item) for item in items if _get_item_role(item)]
    seen: Set[str] = set()
    duplicates: Set[str] = set()

    for r in roles:
        if r in seen:
            duplicates.add(r)
        seen.add(r)

    if duplicates:
        dup_list = sorted(list(duplicates))
        return RuleResult(
            name="unique_roles_check",
            passed=False,
            reason=f"Duplicate roles found: {', '.join(dup_list)}",
        )

    return RuleResult(
        name="unique_roles_check",
        passed=True,
        reason=None,
    )

def check_outfit(
    items: List[Any],
    budget: int,
    occasion: Optional[str] = None,
    climate: Optional[str] = None,
    total_price: Optional[int] = None,
) -> RuleEnvelope:
    """Composite verification envelope evaluating all hard rules."""
    if total_price is None:
        total_price = sum(_get_item_price(item) for item in items)

    results = [
        check_budget(total_price, budget),
        check_completeness(items),
        check_occasion_climate(items, occasion=occasion, climate=climate),
        check_unique_roles(items),
    ]

    violations = [r.reason for r in results if not r.passed and r.reason is not None]
    is_valid = len(violations) == 0

    return RuleEnvelope(
        passed=is_valid,
        violations=violations,
        details=results,
    )
