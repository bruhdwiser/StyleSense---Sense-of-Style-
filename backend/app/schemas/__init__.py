"""StyleSense AI — Pydantic Schemas for Request & Response Validation."""

from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class ProfileBase(BaseModel):
    age_range: Optional[str] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    budget: Optional[int] = None
    preferred_brands: List[str] = Field(default_factory=list)
    aesthetics: List[str] = Field(default_factory=list)
    favorite_colors: List[str] = Field(default_factory=list)
    skin_tone: Optional[str] = None
    body_type: Optional[str] = None
    preferred_fit: Optional[str] = None
    fashion_goals: List[str] = Field(default_factory=list)

class ProfileCreate(ProfileBase):
    user_id: str

class ProfileResponse(ProfileBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class StyleDNASummary(BaseModel):
    user_id: str
    version: int
    dominant_tags: List[str]
    summary: str
    weights: Dict[str, float]
    updated_at: datetime

class StyleDNAComputeRequest(BaseModel):
    user_id: str
    aesthetics: List[str] = Field(default_factory=list)
    favorite_colors: List[str] = Field(default_factory=list)
    preferred_fit: Optional[str] = None
    body_type: Optional[str] = None
    budget: Optional[int] = None

class OutfitItemInput(BaseModel):
    role: str
    price: int = 0
    name: Optional[str] = None
    product_id: Optional[str] = None
    wardrobe_item_id: Optional[str] = None
    style_tags: List[str] = Field(default_factory=list)
    occasion_tags: List[str] = Field(default_factory=list)
    season_tags: List[str] = Field(default_factory=list)

class OutfitValidationRequest(BaseModel):
    items: List[OutfitItemInput]
    budget: int
    occasion: str
    climate: Optional[str] = None

class RuleResult(BaseModel):
    name: str
    passed: bool
    reason: Optional[str] = None

class RuleEnvelopeResponse(BaseModel):
    passed: bool
    violations: List[str] = Field(default_factory=list)
    details: List[RuleResult] = Field(default_factory=list)

class RuleInfo(BaseModel):
    name: str
    description: str
    required_roles: Optional[List[str]] = None

class RecommendationRequest(BaseModel):
    occasion: str
    budget: int
    climate: Optional[str] = None
    aesthetic: Optional[str] = None
    user_id: Optional[str] = None
    gender: Optional[str] = None
    include_wardrobe: bool = True

class RecommendedItem(BaseModel):
    id: str
    name: str
    category: str
    role: str
    price: int
    brand: Optional[str] = None
    image_url: Optional[str] = None
    retailer_url: Optional[str] = None
    color_tags: List[str] = Field(default_factory=list)
    style_tags: List[str] = Field(default_factory=list)
    is_wardrobe_item: bool = False

class OutfitRecommendation(BaseModel):
    id: str
    occasion: str
    total_price: int
    budget: int
    score: float
    explanation: str
    violations: List[str] = Field(default_factory=list)
    items: List[RecommendedItem]

class RecommendationResponse(BaseModel):
    outfits: List[OutfitRecommendation]
    count: int

class EventItem(BaseModel):
    event_type: str
    target_type: str
    target_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    user_id: Optional[str] = None

class EventBatchRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    events: List[EventItem]

class EventBatchResponse(BaseModel):
    accepted: int
    message: str

class ProductResponse(BaseModel):
    id: str
    name: str
    brand: Optional[str] = None
    price: int
    category: str
    color_tags: List[str] = Field(default_factory=list)
    style_tags: List[str] = Field(default_factory=list)
    occasion_tags: List[str] = Field(default_factory=list)
    season_tags: List[str] = Field(default_factory=list)
    gender: Optional[str] = None
    image_url: Optional[str] = None
    retailer_url: Optional[str] = None

    model_config = {"from_attributes": True}

class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total: int
    page: int
    limit: int
