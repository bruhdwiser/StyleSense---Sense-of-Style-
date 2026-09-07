"""StyleSense AI — Product Catalogue API Router.

Exposes endpoints to search, filter, and inspect products from the ingested catalog.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Product
from app.schemas import ProductResponse, ProductListResponse

router = APIRouter(tags=["Product Catalogue"])

@router.get(
    "/products",
    response_model=ProductListResponse,
    summary="List and filter catalog products",
)
def list_products_endpoint(
    category: Optional[str] = Query(None, description="top, bottom, shoes, accessory, outerwear"),
    min_price: Optional[int] = Query(None, ge=0),
    max_price: Optional[int] = Query(None, ge=0),
    occasion: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Product)

    if category:
        query = query.filter(Product.category == category.lower().strip())
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if gender:
        query = query.filter(Product.gender.ilike(gender))
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    total = query.count()
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()

    return ProductListResponse(
        products=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        limit=limit,
    )

@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Get single product details by ID",
)
def get_product_endpoint(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(product)

@router.get(
    "/catalog/stats",
    summary="Get catalogue summary statistics",
)
def get_catalog_stats_endpoint(db: Session = Depends(get_db)):
    total_count = db.query(Product).count()

    categories = (
        db.query(Product.category, func.count(Product.id))
        .group_by(Product.category)
        .all()
    )

    avg_price = db.query(func.avg(Product.price)).scalar() or 0

    return {
        "total_products": total_count,
        "categories": {cat: count for cat, count in categories},
        "average_price": round(float(avg_price), 2),
    }
