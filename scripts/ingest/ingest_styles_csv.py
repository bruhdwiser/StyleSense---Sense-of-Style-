"""StyleSense AI — Product Catalogue Ingestion.

Parses Static_Seedings/styles.csv and normalizes rows into Product records.
Maps categories, colors, occasions, seasons, and derives style tags.
Outputs normalized products to data/processed/products.json and optionally
populates the database.
Specified in static_implementation.md Section 7.1.
"""

import csv
import json
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.models.tag_vocabulary import (
    COLOR_SYNONYMS,
    SEASON_SYNONYMS,
    USAGE_SYNONYMS,
    AESTHETICS,
    SILHOUETTES,
)

PRICE_RANGES: Dict[str, tuple[int, int]] = {
    "top": (699, 2499),
    "bottom": (999, 2999),
    "shoes": (1499, 4999),
    "accessory": (499, 1999),
    "outerwear": (1999, 5999),
}

OUTERWEAR_TYPES: Set[str] = {
    "jackets", "sweaters", "sweatshirts", "blazers", "coats", "cardigan", "shrug", "waistcoat"
}

TOP_TYPES: Set[str] = {
    "shirts", "tshirts", "tops", "kurtas", "tunics", "vests", "camisoles", "kurtis", "dupattas"
}

BOTTOM_TYPES: Set[str] = {
    "jeans", "trousers", "track pants", "shorts", "skirts", "leggings", "capris", "jeggings", "salwar", "churidar"
}

FOOTWEAR_TYPES: Set[str] = {
    "casual shoes", "sports shoes", "formal shoes", "flats", "heels", "sandals", "flip flops", "sports sandals", "boots"
}

def map_category(master_category: str, sub_category: str, article_type: str) -> Optional[str]:
    """Maps CSV masterCategory/subCategory/articleType to one of our 5 canonical categories:

    top, bottom, shoes, accessory, outerwear.
    """
    article_lower = article_type.lower().strip()
    sub_lower = sub_category.lower().strip()
    master_lower = master_category.lower().strip()

    if article_lower in OUTERWEAR_TYPES or "jacket" in article_lower or "coat" in article_lower:
        return "outerwear"

    if article_lower in FOOTWEAR_TYPES or master_lower == "footwear":
        return "shoes"

    if article_lower in BOTTOM_TYPES or sub_lower == "bottomwear":
        return "bottom"

    if article_lower in TOP_TYPES or sub_lower == "topwear":
        return "top"

    if master_lower in {"accessories", "personal care"} or sub_lower in {"bags", "watches", "jewellery", "eyewear", "belts", "wallets", "ties", "scarves"}:
        return "accessory"

    if master_lower == "apparel":
        if "dress" in article_lower:
            return "top"
        return "top"

    return "accessory"

def map_colors(base_colour: str, display_name: str) -> List[str]:
    """Maps base color string and title to canonical color tags."""
    colors: List[str] = []
    base_lower = base_colour.lower().strip() if base_colour else ""

    if base_lower in COLOR_SYNONYMS:
        colors.append(COLOR_SYNONYMS[base_lower])
    elif base_lower:

        for syn, canon in COLOR_SYNONYMS.items():
            if syn in base_lower:
                colors.append(canon)
                break

    name_lower = display_name.lower()
    for col in ["black", "white", "navy", "grey", "beige", "brown", "red", "blue", "green", "pink", "purple"]:
        if col in name_lower and col not in colors:
            colors.append(col)

    return colors if colors else ["black"]

def map_occasions(usage: str, display_name: str) -> List[str]:
    """Maps usage string and title to canonical occasion tags."""
    occasions: List[str] = []
    usage_lower = usage.lower().strip() if usage else ""

    if usage_lower in USAGE_SYNONYMS:
        occasions.append(USAGE_SYNONYMS[usage_lower])

    name_lower = display_name.lower()
    if "party" in name_lower or "club" in name_lower:
        occasions.append("party")
    if "formal" in name_lower or "office" in name_lower or "business" in name_lower:
        occasions.append("formal")
        occasions.append("workwear")
    if "sports" in name_lower or "running" in name_lower or "gym" in name_lower:
        occasions.append("sports")
    if "ethnic" in name_lower or "festive" in name_lower or "traditional" in name_lower:
        occasions.append("ethnic")
    if "casual" in name_lower:
        occasions.append("casual")

    if not occasions:
        occasions.append("casual")

    return list(set(occasions))

def map_seasons(season: str) -> List[str]:
    """Maps season string to canonical season tags."""
    season_lower = season.lower().strip() if season else ""
    if season_lower in SEASON_SYNONYMS:
        return [SEASON_SYNONYMS[season_lower]]
    return ["summer", "fall", "spring"]

def extract_style_tags(display_name: str, article_type: str, category: str) -> List[str]:
    """Extracts aesthetic and silhouette style tags using keyword heuristics."""
    name_lower = display_name.lower()
    article_lower = article_type.lower()
    combined = f"{name_lower} {article_lower}"

    tags: Set[str] = set()

    if any(w in combined for w in ["minimal", "solid", "clean", "classic", "plain", "basic"]):
        tags.add("minimalist")
    if any(w in combined for w in ["street", "graphic", "printed", "hoodie", "sneaker", "cargo"]):
        tags.add("streetwear")
    if any(w in combined for w in ["formal", "oxford", "tuxedo", "suit", "blazer", "tailored"]):
        tags.add("formal")
    if any(w in combined for w in ["boho", "bohemian", "floral", "embroidered", "paisley", "ethnic", "kurta"]):
        tags.add("bohemian")
        tags.add("ethnic")
    if any(w in combined for w in ["sport", "track", "jogger", "running", "dry-fit", "athletic", "sweat"]):
        tags.add("athleisure")
    if any(w in combined for w in ["denim", "check", "stripe", "polo", "casual", "tee"]):
        tags.add("casual")

    if "slim" in combined:
        tags.add("slim")
    elif "oversized" in combined or "loose" in combined:
        tags.add("oversized")
        tags.add("relaxed")
    elif "relaxed" in combined:
        tags.add("relaxed")
    else:
        tags.add("regular")

    if not tags:
        tags.add("casual")
        tags.add("regular")

    return list(tags)

def extract_brand(display_name: str) -> str:
    """Extracts leading brand name from product display name."""
    parts = display_name.split()
    if len(parts) >= 2 and parts[1].lower() in {"men", "women", "boys", "girls", "unisex"}:
        return parts[0]
    if parts:
        return parts[0]
    return "StyleSense"

def generate_price(category: str, seed_id: int) -> int:
    """Deterministic, reproducible price generator based on item ID and category."""
    rng = random.Random(seed_id)
    min_p, max_p = PRICE_RANGES.get(category, (799, 2999))

    raw = rng.randint(min_p, max_p)
    return (raw // 100) * 100 + 99

def ingest_styles_csv(
    csv_path: Optional[Path] = None,
    output_json_path: Optional[Path] = None,
    limit: Optional[int] = None,
    populate_db: bool = False,
) -> List[Dict[str, Any]]:
    """Reads Static_Seedings/styles.csv, normalizes products, and writes products.json."""
    if csv_path is None:
        csv_path = PROJECT_ROOT / "Static_Seedings" / "styles.csv"
    if output_json_path is None:
        output_json_path = PROJECT_ROOT / "data" / "processed" / "products.json"

    output_json_path.parent.mkdir(parents=True, exist_ok=True)

    products: List[Dict[str, Any]] = []
    skipped_rows = 0

    print(f"Reading {csv_path} ...")
    with open(csv_path, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = row.get("id", "").strip()
            if not item_id:
                continue

            try:
                numeric_id = int(item_id)
            except ValueError:
                numeric_id = abs(hash(item_id)) % 100000

            master_cat = row.get("masterCategory", "")
            sub_cat = row.get("subCategory", "")
            article_type = row.get("articleType", "")
            gender = row.get("gender", "Unisex")
            base_color = row.get("baseColour", "")
            season = row.get("season", "")
            usage = row.get("usage", "")
            name = row.get("productDisplayName", "").strip()

            if not name:
                name = f"{gender} {article_type}".strip()

            category = map_category(master_cat, sub_cat, article_type)
            if not category:
                skipped_rows += 1
                continue

            color_tags = map_colors(base_color, name)
            occasion_tags = map_occasions(usage, name)
            season_tags = map_seasons(season)
            style_tags = extract_style_tags(name, article_type, category)
            brand = extract_brand(name)
            price = generate_price(category, numeric_id)
            retailer_url = f"https://www.myntra.com/{item_id}"
            image_url = f"/static/products/{item_id}.jpg"

            product_record = {
                "id": str(item_id),
                "name": name,
                "brand": brand,
                "price": price,
                "category": category,
                "color_tags": color_tags,
                "style_tags": style_tags,
                "occasion_tags": occasion_tags,
                "season_tags": season_tags,
                "gender": gender,
                "image_url": image_url,
                "retailer_url": retailer_url,
                "embedding": None,
            }
            products.append(product_record)

            if limit and len(products) >= limit:
                break

    print(f"Successfully processed {len(products)} products (skipped {skipped_rows} unmapped rows).")

    with open(output_json_path, mode="w", encoding="utf-8") as out:
        json.dump(products, out, indent=2)
    print(f"Saved normalized products to {output_json_path}")

    if populate_db:
        from app.database import SessionLocal, init_db
        from app.models import Product

        init_db()
        db = SessionLocal()
        try:
            print("Populating database with products...")
            existing_ids = {p[0] for p in db.query(Product.id).all()}
            new_objs = []
            for p in products:
                if p["id"] not in existing_ids:
                    new_objs.append(Product(**p))
            if new_objs:
                db.bulk_save_objects(new_objs)
                db.commit()
                print(f"Inserted {len(new_objs)} new products into database.")
            else:
                print("Database already contains these products.")
        finally:
            db.close()

    return products

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest styles.csv")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of products")
    parser.add_argument("--db", action="store_true", help="Populate database")
    args = parser.parse_args()

    ingest_styles_csv(limit=args.limit, populate_db=args.db)
