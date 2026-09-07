"""StyleSense AI — StyleDNA Engine Unit & Integration Tests.
Verifies seed computations, feedback nudges, clipping, and persona strings.
"""

import pytest
from app.services.styledna import (
    compute_style_dna,
    apply_event_feedback,
    get_style_dna_summary,
    WEIGHT_MIN,
    WEIGHT_MAX,
)
from app.models import StyleDNA

class MockProfile:
    def __init__(self):
        self.user_id = "user_test_123"
        self.aesthetics = ["minimalist", "streetwear"]
        self.favorite_colors = ["black", "navy"]
        self.preferred_fit = "relaxed_fit"
        self.body_type = "athletic"

def test_compute_style_dna():
    profile = MockProfile()
    dna = compute_style_dna(profile=profile)

    assert dna.user_id == "user_test_123"
    assert dna.version == 1

    assert dna.weights.get("minimalist") == 1.0
    assert dna.weights.get("streetwear") == 1.0
    assert dna.weights.get("black") == 1.0
    assert dna.weights.get("navy") == 1.0
    assert dna.weights.get("relaxed_fit") == 1.0
    assert len(dna.dominant_tags) <= 5
    assert dna.summary is not None and len(dna.summary) > 0

def test_apply_event_feedback_like_and_save():
    profile = MockProfile()
    dna = compute_style_dna(profile=profile)

    updated = apply_event_feedback(
        user_id="user_test_123",
        event_type="like",
        target_tags=["minimalist", "black"],
        style_dna_instance=dna,
    )

    assert updated.version == 2
    assert updated.weights["minimalist"] == 1.1
    assert updated.weights["black"] == 1.1

    updated2 = apply_event_feedback(
        user_id="user_test_123",
        event_type="save",
        target_tags=["minimalist"],
        style_dna_instance=updated,
    )

    assert updated2.version == 3
    assert updated2.weights["minimalist"] == 1.2

def test_apply_event_feedback_dismiss_and_floor():
    profile = MockProfile()
    dna = compute_style_dna(profile=profile)

    updated = apply_event_feedback(
        user_id="user_test_123",
        event_type="dismiss",
        target_tags=["streetwear"],
        style_dna_instance=dna,
    )

    assert updated.weights["streetwear"] == 0.9

    for _ in range(15):
        updated = apply_event_feedback(
            user_id="user_test_123",
            event_type="dismiss",
            target_tags=["streetwear"],
            style_dna_instance=updated,
        )

    assert updated.weights["streetwear"] == WEIGHT_MIN

def test_apply_event_feedback_clipping_ceiling():
    profile = MockProfile()
    dna = compute_style_dna(profile=profile)

    for _ in range(30):
        dna = apply_event_feedback(
            user_id="user_test_123",
            event_type="like",
            target_tags=["minimalist"],
            style_dna_instance=dna,
        )

    assert dna.weights["minimalist"] == WEIGHT_MAX

def test_apply_event_feedback_rating():
    profile = MockProfile()
    dna = compute_style_dna(profile=profile)

    updated = apply_event_feedback(
        user_id="user_test_123",
        event_type="rating",
        target_tags=["black"],
        payload={"rating": 5},
        style_dna_instance=dna,
    )
    assert updated.weights["black"] == 1.1

    updated2 = apply_event_feedback(
        user_id="user_test_123",
        event_type="rating",
        target_tags=["black"],
        payload={"rating": 1},
        style_dna_instance=updated,
    )
    assert updated2.weights["black"] == 1.0

def test_get_style_dna_summary_empty():
    summary = get_style_dna_summary(user_id="unknown_user")
    assert summary["version"] == 0
    assert summary["dominant_tags"] == []
