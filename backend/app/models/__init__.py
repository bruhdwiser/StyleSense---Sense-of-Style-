"""StyleSense AI — SQLAlchemy ORM Domain Models.
Defines typed entities for users, taste profiles, catalog products, and events.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)

    profile: Mapped[Optional["Profile"]] = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    style_dna: Mapped[Optional["StyleDNA"]] = relationship("StyleDNA", back_populates="user", uselist=False, cascade="all, delete-orphan")
    outfits: Mapped[List["Outfit"]] = relationship("Outfit", back_populates="user", cascade="all, delete-orphan")
    wardrobe_items: Mapped[List["WardrobeItem"]] = relationship("WardrobeItem", back_populates="user", cascade="all, delete-orphan")
    wishlist_items: Mapped[List["WishlistItem"]] = relationship("WishlistItem", back_populates="user", cascade="all, delete-orphan")
    events: Mapped[List["InteractionEvent"]] = relationship("InteractionEvent", back_populates="user", cascade="all, delete-orphan")

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), unique=True, nullable=False)
    age_range: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    budget: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preferred_brands: Mapped[List[str]] = mapped_column(JSON, default=list)
    aesthetics: Mapped[List[str]] = mapped_column(JSON, default=list)
    favorite_colors: Mapped[List[str]] = mapped_column(JSON, default=list)
    skin_tone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    body_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    preferred_fit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    fashion_goals: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    user: Mapped["User"] = relationship("User", back_populates="profile")

class StyleDNA(Base):
    __tablename__ = "style_dna"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), unique=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    weights: Mapped[Dict[str, float]] = mapped_column(JSON, default=dict)
    dominant_tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    dominant_aesthetics: Mapped[List[str]] = mapped_column(JSON, default=list)
    color_palette: Mapped[List[str]] = mapped_column(JSON, default=list)
    preferred_silhouettes: Mapped[List[str]] = mapped_column(JSON, default=list)
    fit_preferences: Mapped[List[str]] = mapped_column(JSON, default=list)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    user: Mapped["User"] = relationship("User", back_populates="style_dna")

class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    brand: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    color_tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    style_tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    occasion_tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    season_tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    gender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    retailer_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)

    outfit_items: Mapped[List["OutfitItem"]] = relationship("OutfitItem", back_populates="product")

class Outfit(Base):
    __tablename__ = "outfits"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    occasion: Mapped[str] = mapped_column(String, nullable=False)
    budget: Mapped[int] = mapped_column(Integer, nullable=False)
    climate: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    total_price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="outfits")
    items: Mapped[List["OutfitItem"]] = relationship("OutfitItem", back_populates="outfit", cascade="all, delete-orphan")

class OutfitItem(Base):
    __tablename__ = "outfit_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    outfit_id: Mapped[str] = mapped_column(String, ForeignKey("outfits.id"), nullable=False)
    product_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("products.id"), nullable=True)
    wardrobe_item_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("wardrobe_items.id"), nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=False)

    outfit: Mapped["Outfit"] = relationship("Outfit", back_populates="items")
    product: Mapped[Optional["Product"]] = relationship("Product", back_populates="outfit_items")
    wardrobe_item: Mapped[Optional["WardrobeItem"]] = relationship("WardrobeItem")

class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    color: Mapped[str] = mapped_column(String, nullable=False)
    style_tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    season: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)

    user: Mapped["User"] = relationship("User", back_populates="wardrobe_items")

class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)

    user: Mapped["User"] = relationship("User", back_populates="wishlist_items")

class InteractionEvent(Base):
    __tablename__ = "interaction_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)

    user: Mapped["User"] = relationship("User", back_populates="events")

class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)
