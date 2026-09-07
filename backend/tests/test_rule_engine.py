"""StyleSense AI — Rule Engine Unit Tests.

Verifies pure functions for budget, completeness, occasion/climate compatibility,
and unique roles with passing, failing, and edge cases.
Specified in static_implementation.md Section 4.3.
"""

import pytest
from app.services.rule_engine import (
    check_budget,
    check_completeness,
    check_occasion_climate,
    check_unique_roles,
    check_outfit,
)

class MockItem:
    def __init__(
        self,
        role: str,
        price: int = 1000,
        occasion_tags=None,
        season_tags=None,
        style_tags=None,
    ):
        self.role = role
        self.price = price
        self.occasion_tags = occasion_tags or ["casual"]
        self.season_tags = season_tags or ["summer"]
        self.style_tags = style_tags or ["minimalist"]

def test_budget_check_pass():
    res = check_budget(outfit_total_price=3500, budget=4000)
    assert res.passed is True
    assert res.reason is None

def test_budget_check_exact():
    res = check_budget(outfit_total_price=4000, budget=4000)
    assert res.passed is True

def test_budget_check_fail():
    res = check_budget(outfit_total_price=4500, budget=4000)
    assert res.passed is False
    assert res.reason is not None and "Budget exceeded" in res.reason

def test_budget_check_zero_budget():
    assert check_budget(outfit_total_price=0, budget=0).passed is True
    assert check_budget(outfit_total_price=500, budget=0).passed is False

def test_completeness_check_pass():
    items = [
        MockItem(role="top"),
        MockItem(role="bottom"),
        MockItem(role="shoes"),
    ]
    res = check_completeness(items)
    assert res.passed is True

def test_completeness_check_with_optional_roles():
    items = [
        MockItem(role="top"),
        MockItem(role="bottom"),
        MockItem(role="shoes"),
        MockItem(role="accessory"),
        MockItem(role="outerwear"),
    ]
    res = check_completeness(items)
    assert res.passed is True

def test_completeness_check_fail_missing_shoes():
    items = [
        MockItem(role="top"),
        MockItem(role="bottom"),
    ]
    res = check_completeness(items)
    assert res.passed is False
    assert res.reason is not None and "missing required roles" in res.reason
    assert "shoes" in res.reason

def test_completeness_check_fail_empty():
    res = check_completeness([])
    assert res.passed is False
    assert res.reason is not None and "Empty outfit" in res.reason

def test_occasion_climate_check_pass():
    items = [
        MockItem(role="top", occasion_tags=["formal"], season_tags=["winter"]),
        MockItem(role="bottom", occasion_tags=["formal"], season_tags=["winter"]),
        MockItem(role="shoes", occasion_tags=["formal"], season_tags=["winter"]),
    ]
    res = check_occasion_climate(items, occasion="formal", climate="winter")
    assert res.passed is True

def test_occasion_climate_check_fail_occasion():
    items = [
        MockItem(role="top", occasion_tags=["party"], season_tags=["summer"]),
        MockItem(role="bottom", occasion_tags=["party"], season_tags=["summer"]),
        MockItem(role="shoes", occasion_tags=["party"], season_tags=["summer"]),
    ]
    res = check_occasion_climate(items, occasion="sports", climate="summer")
    assert res.passed is False
    assert res.reason is not None and "Occasion mismatch" in res.reason

def test_occasion_climate_check_fail_climate():
    items = [
        MockItem(role="top", occasion_tags=["formal"], season_tags=["summer"]),
        MockItem(role="bottom", occasion_tags=["formal"], season_tags=["summer"]),
        MockItem(role="shoes", occasion_tags=["formal"], season_tags=["summer"]),
    ]
    res = check_occasion_climate(items, occasion="formal", climate="winter")
    assert res.passed is False
    assert res.reason is not None and "Climate mismatch" in res.reason

def test_unique_roles_check_pass():
    items = [
        MockItem(role="top"),
        MockItem(role="bottom"),
        MockItem(role="shoes"),
        MockItem(role="accessory"),
    ]
    res = check_unique_roles(items)
    assert res.passed is True

def test_unique_roles_check_fail_duplicate():
    items = [
        MockItem(role="top"),
        MockItem(role="bottom"),
        MockItem(role="shoes"),
        MockItem(role="shoes"),
    ]
    res = check_unique_roles(items)
    assert res.passed is False
    assert res.reason is not None and "Duplicate roles found" in res.reason
    assert "shoes" in res.reason

def test_check_outfit_valid():
    items = [
        MockItem(role="top", price=1200, occasion_tags=["casual"]),
        MockItem(role="bottom", price=1500, occasion_tags=["casual"]),
        MockItem(role="shoes", price=1200, occasion_tags=["casual"]),
    ]
    env = check_outfit(items=items, budget=5000, occasion="casual", total_price=3900)
    assert env.passed is True
    assert len(env.violations) == 0

def test_check_outfit_multiple_violations():

    items = [
        MockItem(role="top", price=3000),
        MockItem(role="bottom", price=3000),
    ]
    env = check_outfit(items=items, budget=3000, occasion="casual", total_price=6000)
    assert env.passed is False
    assert len(env.violations) >= 2
