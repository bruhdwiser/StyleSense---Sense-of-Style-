"""StyleSense AI — Recommendation Engine Unit Tests.

Verifies candidate generation, wardrobe reuse, scoring heuristics,
and template explanation formatting.
Specified in static_implementation.md Section 5.
"""

import pytest
from app.database import SessionLocal, init_db
from app.models import Product, WardrobeItem, StyleDNA
from app.services.recommendation import (
    CandidateItem,
    CandidateOutfit,
    score_candidate,
    generate_explanation,
    recommend_outfits,
    WARDROBE_REUSE_BONUS,
)

@pytest.fixture(scope="module")
def db_session():
    init_db()
    db = SessionLocal()

    if db.query(Product).count() < 10:
        sample_prods = [
            Product(
                id="test_top_1",
                name="Minimalist Black T-Shirt",
                brand="Zara",
                price=999,
                category="top",
                color_tags=["black"],
                style_tags=["minimalist", "casual"],
                occasion_tags=["casual"],
                season_tags=["summer"],
            ),
            Product(
                id="test_bottom_1",
                name="Slim Fit Blue Jeans",
                brand="Levi's",
                price=1999,
                category="bottom",
                color_tags=["blue"],
                style_tags=["casual", "slim"],
                occasion_tags=["casual"],
                season_tags=["summer", "fall"],
            ),
            Product(
                id="test_shoes_1",
                name="Classic White Sneakers",
                brand="Puma",
                price=2499,
                category="shoes",
                color_tags=["white"],
                style_tags=["streetwear", "minimalist"],
                occasion_tags=["casual"],
                season_tags=["summer"],
            ),
            Product(
                id="test_acc_1",
                name="Leather Watch",
                brand="Fossil",
                price=1499,
                category="accessory",
                color_tags=["black"],
                style_tags=["minimalist"],
                occasion_tags=["casual"],
                season_tags=["summer"],
            ),
        ]
        db.bulk_save_objects(sample_prods)
        db.commit()

    yield db
    db.close()

def test_wardrobe_reuse_cost_and_bonus():

    regular_item = CandidateItem(
        id="prod_1",
        name="Purchased Jacket",
        category="top",
        role="top",
        price=2500,
        is_wardrobe_item=False,
    )
    assert regular_item.price == 2500

    wardrobe_item = CandidateItem(
        id="wardrobe_1",
        name="Owned Black Jeans",
        category="bottom",
        role="bottom",
        price=1800,
        is_wardrobe_item=True,
    )
    assert wardrobe_item.price == 0
    assert wardrobe_item.original_price == 1800

    outfit = CandidateOutfit(
        items=[regular_item, wardrobe_item],
        occasion="casual",
        budget=4000,
    )
    assert outfit.total_price == 2500

    score = score_candidate(
        candidate=outfit,
        style_dna=None,
        occasion="casual",
    )

    assert score >= WARDROBE_REUSE_BONUS

def test_score_candidate_with_styledna_weights():
    item = CandidateItem(
        id="prod_2",
        name="Streetwear Hoodie",
        category="top",
        role="top",
        price=1500,
        style_tags=["streetwear"],
        color_tags=["black"],
        occasion_tags=["casual"],
    )
    outfit = CandidateOutfit(items=[item], occasion="casual", budget=3000)

    mock_dna = StyleDNA(
        user_id="user_test",
        version=2,
        weights={"streetwear": 2.5, "black": 1.5},
        dominant_tags=["streetwear", "black"],
    )

    score_high = score_candidate(outfit, style_dna=mock_dna, occasion="casual")

    mock_dna_low = StyleDNA(
        user_id="user_test",
        version=2,
        weights={"streetwear": 0.2, "black": 0.2},
        dominant_tags=["streetwear"],
    )
    score_low = score_candidate(outfit, style_dna=mock_dna_low, occasion="casual")

    assert score_high > score_low

def test_generate_explanation_template():
    items = [
        CandidateItem(
            id="top_1",
            name="Black Shirt",
            category="top",
            role="top",
            price=1200,
            style_tags=["minimalist"],
        ),
        CandidateItem(
            id="bottom_1",
            name="Owned Chinos",
            category="bottom",
            role="bottom",
            price=1500,
            is_wardrobe_item=True,
        ),
    ]
    outfit = CandidateOutfit(items=items, occasion="party", budget=5000)
    mock_dna = StyleDNA(
        user_id="u1",
        version=1,
        dominant_tags=["minimalist"],
        weights={"minimalist": 1.5},
    )

    explanation = generate_explanation(outfit, mock_dna, "party")

    assert "Recommended because it matches your minimalist" in explanation
    assert "party budget" in explanation
    assert "smartly incorporates your owned Owned Chinos" in explanation

def test_recommend_outfits_pipeline(db_session):
    outfits = recommend_outfits(
        occasion="casual",
        budget=8000,
        climate="summer",
        k=3,
        db=db_session,
    )

    assert len(outfits) <= 3
    assert len(outfits) > 0
    for outfit in outfits:
        assert outfit.total_price <= 8000
        assert len(outfit.items) >= 3
        assert outfit.explanation != ""
        assert outfit.score > 0
