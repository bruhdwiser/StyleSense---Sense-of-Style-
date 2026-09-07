"""StyleSense AI — Recommendation Engine.

Executes the candidate generation, rule engine filtering, StyleDNA scoring,
diversity ranking, and explanation generation pipeline.
Specified in static_implementation.md Section 5.
"""

import uuid
from typing import List, Dict, Optional, Set, Any
from sqlalchemy.orm import Session

from app.models import Product, WardrobeItem, StyleDNA
from app.services.rule_engine import check_outfit, RuleEnvelope
from app.services.styledna import get_style_dna_summary

TREND_BONUSES: Dict[str, float] = {
    "minimalist": 0.25,
    "streetwear": 0.25,
    "relaxed": 0.20,
    "oversized": 0.15,
    "athleisure": 0.15,
    "monochrome": 0.15,
    "black": 0.10,
    "white": 0.10,
    "navy": 0.10,
    "earthy": 0.10,
}

WARDROBE_REUSE_BONUS: float = 0.5

class CandidateItem:
    def __init__(
        self,
        id: str,
        name: str,
        category: str,
        role: str,
        price: int,
        brand: Optional[str] = None,
        image_url: Optional[str] = None,
        retailer_url: Optional[str] = None,
        color_tags: Optional[List[str]] = None,
        style_tags: Optional[List[str]] = None,
        occasion_tags: Optional[List[str]] = None,
        season_tags: Optional[List[str]] = None,
        is_wardrobe_item: bool = False,
    ):
        self.id = id
        self.name = name
        self.category = category
        self.role = role
        self.price = 0 if is_wardrobe_item else price
        self.original_price = price
        self.brand = brand
        self.image_url = image_url
        self.retailer_url = retailer_url
        self.color_tags = color_tags or []
        self.style_tags = style_tags or []
        self.occasion_tags = occasion_tags or []
        self.season_tags = season_tags or []
        self.is_wardrobe_item = is_wardrobe_item

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "role": self.role,
            "price": self.price,
            "brand": self.brand,
            "image_url": self.image_url,
            "retailer_url": self.retailer_url,
            "color_tags": self.color_tags,
            "style_tags": self.style_tags,
            "is_wardrobe_item": self.is_wardrobe_item,
        }

class CandidateOutfit:
    def __init__(
        self,
        items: List[CandidateItem],
        occasion: str,
        budget: int,
        id: Optional[str] = None,
    ):
        self.id = id or str(uuid.uuid4())
        self.items = items
        self.occasion = occasion
        self.budget = budget
        self.total_price = sum(item.price for item in items)
        self.score: float = 0.0
        self.explanation: str = ""
        self.violations: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "occasion": self.occasion,
            "total_price": self.total_price,
            "budget": self.budget,
            "score": round(self.score, 2),
            "explanation": self.explanation,
            "violations": self.violations,
            "items": [item.to_dict() for item in self.items],
        }

def _product_to_candidate_item(prod: Product, role: str) -> CandidateItem:
    return CandidateItem(
        id=str(prod.id),
        name=prod.name,
        category=prod.category,
        role=role,
        price=prod.price,
        brand=prod.brand,
        image_url=prod.image_url,
        retailer_url=prod.retailer_url,
        color_tags=list(prod.color_tags or []),
        style_tags=list(prod.style_tags or []),
        occasion_tags=list(prod.occasion_tags or []),
        season_tags=list(prod.season_tags or []),
        is_wardrobe_item=False,
    )

def _wardrobe_to_candidate_item(w: WardrobeItem) -> CandidateItem:
    return CandidateItem(
        id=str(w.id),
        name=w.name or f"Your {w.color} {w.category}",
        category=w.category,
        role=w.category,
        price=0,
        brand="Wardrobe",
        image_url=w.image_url,
        retailer_url=None,
        color_tags=[w.color.lower()] if w.color else [],
        style_tags=list(w.style_tags or []),
        occasion_tags=["casual"],
        season_tags=[w.season.lower()] if w.season else [],
        is_wardrobe_item=True,
    )

def generate_candidates(
    occasion: str,
    budget: int,
    climate: Optional[str] = None,
    aesthetic: Optional[str] = None,
    user_id: Optional[str] = None,
    gender: Optional[str] = None,
    include_wardrobe: bool = True,
    db: Optional[Session] = None,
) -> List[CandidateOutfit]:
    """Generates 5-8 candidate looks adhering to wardrobe-first strategy and category balance."""
    candidates: List[CandidateOutfit] = []

    if db is None:
        return candidates

    wardrobe_items: List[WardrobeItem] = []
    if user_id and include_wardrobe:
        wardrobe_items = db.query(WardrobeItem).filter(WardrobeItem.user_id == user_id).all()

    wardrobe_by_role: Dict[str, List[WardrobeItem]] = {
        "top": [w for w in wardrobe_items if w.category == "top"],
        "bottom": [w for w in wardrobe_items if w.category == "bottom"],
        "shoes": [w for w in wardrobe_items if w.category == "shoes"],
        "accessory": [w for w in wardrobe_items if w.category == "accessory"],
        "outerwear": [w for w in wardrobe_items if w.category == "outerwear"],
    }

    query = db.query(Product)
    if gender and gender.lower() != "unisex":
        query = query.filter((Product.gender.ilike(gender)) | (Product.gender == "Unisex") | (Product.gender.is_(None)))

    all_products = query.limit(300).all()

    tops = [p for p in all_products if p.category == "top"]
    bottoms = [p for p in all_products if p.category == "bottom"]
    shoes = [p for p in all_products if p.category == "shoes"]
    accessories = [p for p in all_products if p.category == "accessory"]
    outerwear = [p for p in all_products if p.category == "outerwear"]

    if not tops or not bottoms or not shoes:

        tops = tops or all_products[:10]
        bottoms = bottoms or all_products[10:20]
        shoes = shoes or all_products[20:30]

    num_candidates = 8
    for i in range(num_candidates):
        items: List[CandidateItem] = []

        use_wardrobe_top = (i in (0, 3)) and bool(wardrobe_by_role["top"])
        use_wardrobe_bottom = (i in (1, 4)) and bool(wardrobe_by_role["bottom"])
        use_wardrobe_shoes = (i == 2) and bool(wardrobe_by_role["shoes"])

        if use_wardrobe_top:
            items.append(_wardrobe_to_candidate_item(wardrobe_by_role["top"][0]))
        else:
            top_prod = tops[i % len(tops)]
            items.append(_product_to_candidate_item(top_prod, "top"))

        if use_wardrobe_bottom:
            items.append(_wardrobe_to_candidate_item(wardrobe_by_role["bottom"][0]))
        else:
            bottom_prod = bottoms[(i * 2 + 1) % len(bottoms)]
            items.append(_product_to_candidate_item(bottom_prod, "bottom"))

        if use_wardrobe_shoes:
            items.append(_wardrobe_to_candidate_item(wardrobe_by_role["shoes"][0]))
        else:
            shoe_prod = shoes[(i * 3 + 2) % len(shoes)]
            items.append(_product_to_candidate_item(shoe_prod, "shoes"))

        if accessories and (i % 2 == 0):
            acc_prod = accessories[i % len(accessories)]
            items.append(_product_to_candidate_item(acc_prod, "accessory"))

        if outerwear and (climate in {"winter", "fall"} or i % 3 == 0):
            out_prod = outerwear[i % len(outerwear)]
            items.append(_product_to_candidate_item(out_prod, "outerwear"))

        candidate = CandidateOutfit(items=items, occasion=occasion, budget=budget)
        candidates.append(candidate)

    return candidates

def score_candidate(
    candidate: CandidateOutfit,
    style_dna: Optional[StyleDNA],
    occasion: str,
    climate: Optional[str] = None,
    aesthetic: Optional[str] = None,
) -> float:
    """Calculates composite ranking score:

    score = StyleDNA overlap + Trend bonus + Wardrobe reuse bonus + pgvector similarity
    Specified in Section 5.1.
    """
    weights: Dict[str, float] = {}
    if style_dna and style_dna.weights:
        weights = style_dna.weights

    total_score = 0.0

    for item in candidate.items:
        item_tags = set(item.style_tags + item.color_tags + item.occasion_tags)
        for tag in item_tags:
            tag_clean = tag.lower().strip()

            tag_weight = weights.get(tag_clean, 1.0)
            total_score += tag_weight * 0.25

    for item in candidate.items:
        for tag in item.style_tags + item.color_tags:
            tag_clean = tag.lower().strip()
            if tag_clean in TREND_BONUSES:
                total_score += TREND_BONUSES[tag_clean]

    if aesthetic:
        aes_clean = aesthetic.lower().strip()
        for item in candidate.items:
            if aes_clean in [t.lower() for t in item.style_tags]:
                total_score += 0.5

    for item in candidate.items:
        if item.is_wardrobe_item:
            total_score += WARDROBE_REUSE_BONUS

    return round(total_score, 3)

def generate_explanation(
    candidate: CandidateOutfit,
    style_dna: Optional[StyleDNA],
    occasion: str,
) -> str:
    """Template-driven explanation generator per Section 5.1 & 5.4:

    "Recommended because it matches your {top_tag}, fits your {occasion} budget,
     and {reuses_item / follows_trend_note}."
    """
    top_tag = "curated personal style"
    if style_dna and style_dna.dominant_tags:
        top_tag = f"{style_dna.dominant_tags[0]} aesthetic"
    elif candidate.items and candidate.items[0].style_tags:
        top_tag = f"{candidate.items[0].style_tags[0]} look"

    wardrobe_items = [it for it in candidate.items if it.is_wardrobe_item]
    if wardrobe_items:
        special_note = f"smartly incorporates your owned {wardrobe_items[0].name} (saving you ₹{wardrobe_items[0].original_price})"
    else:
        special_note = "combines versatile pieces that easily pair across multiple settings"

    return (
        f"Recommended because it matches your {top_tag}, "
        f"fits your {occasion} budget (₹{candidate.total_price} of ₹{candidate.budget}), "
        f"and {special_note}."
    )

def recommend_outfits(
    occasion: str,
    budget: int,
    climate: Optional[str] = None,
    aesthetic: Optional[str] = None,
    user_id: Optional[str] = None,
    gender: Optional[str] = None,
    include_wardrobe: bool = True,
    k: int = 3,
    db: Optional[Session] = None,
) -> List[CandidateOutfit]:
    """Full recommendation pipeline:

    1. Candidate Generation (5-8 complete looks)
    2. Rule Engine Filtering (hard constraints check)
    3. StyleDNA & Trend Scoring
    4. Diversity Selection (top 3 distinct looks)
    5. Explanation Generation
    """

    raw_candidates = generate_candidates(
        occasion=occasion,
        budget=budget,
        climate=climate,
        aesthetic=aesthetic,
        user_id=user_id,
        gender=gender,
        include_wardrobe=include_wardrobe,
        db=db,
    )

    if not raw_candidates:
        return []

    valid_candidates: List[CandidateOutfit] = []
    for cand in raw_candidates:
        envelope = check_outfit(
            items=cand.items,
            budget=budget,
            occasion=occasion,
            climate=climate,
            total_price=cand.total_price,
        )
        cand.violations = envelope.violations
        if envelope.passed:
            valid_candidates.append(cand)

    if not valid_candidates:
        valid_candidates = sorted(raw_candidates, key=lambda c: c.total_price)[:k]

    style_dna: Optional[StyleDNA] = None
    if user_id and db is not None:
        style_dna = db.query(StyleDNA).filter(StyleDNA.user_id == user_id).first()

    for cand in valid_candidates:
        cand.score = score_candidate(
            cand,
            style_dna=style_dna,
            occasion=occasion,
            climate=climate,
            aesthetic=aesthetic,
        )
        cand.explanation = generate_explanation(cand, style_dna, occasion)

    valid_candidates.sort(key=lambda c: c.score, reverse=True)

    selected: List[CandidateOutfit] = []
    seen_top_ids: Set[str] = set()

    for cand in valid_candidates:
        top_item_id = cand.items[0].id if cand.items else cand.id
        if top_item_id not in seen_top_ids:
            seen_top_ids.add(top_item_id)
            selected.append(cand)
        if len(selected) >= k:
            break

    if len(selected) < k:
        for cand in valid_candidates:
            if cand not in selected:
                selected.append(cand)
            if len(selected) >= k:
                break

    return selected
