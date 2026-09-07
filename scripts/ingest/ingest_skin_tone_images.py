"""StyleSense AI — Ingest Skin Tone References.

Catalogs reference images from Static_Seedings skin tone directories.
Specified in static_implementation.md Section 7.1.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent

def ingest_skin_tones() -> Dict[str, List[str]]:
    seedings_dir = PROJECT_ROOT / "Static_Seedings"
    output_path = PROJECT_ROOT / "data" / "processed" / "skin_tone_references.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tone_folders = {
        "dark_complexion": "dark",
        "medium_dark_skintone": "medium_dark",
        "medium_light_skintone": "medium_light",
        "light_skintone": "light",
    }

    references: Dict[str, List[str]] = {}
    for folder_name, tone_key in tone_folders.items():
        folder_path = seedings_dir / folder_name
        references[tone_key] = []
        if folder_path.exists() and folder_path.is_dir():
            for img in folder_path.glob("*.*"):
                if img.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                    references[tone_key].append(img.name)

    with open(output_path, mode="w", encoding="utf-8") as out:
        json.dump(references, out, indent=2)

    total_refs = sum(len(v) for v in references.values())
    print(f"Indexed {total_refs} skin tone references across {len(references)} categories.")
    return references

if __name__ == "__main__":
    ingest_skin_tones()
