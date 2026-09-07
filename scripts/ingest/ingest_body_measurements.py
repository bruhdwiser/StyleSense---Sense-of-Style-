"""StyleSense AI — Ingest Body Measurements Dataset.

Parses Static_Seedings/Body Measurements _ original_CSV.csv into structured
reference profiles used for body-type heuristics.
Specified in static_implementation.md Section 7.1.
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Any

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent

def ingest_body_measurements() -> List[Dict[str, Any]]:
    csv_path = PROJECT_ROOT / "Static_Seedings" / "Body Measurements _ original_CSV.csv"
    output_path = PROJECT_ROOT / "data" / "processed" / "body_measurements.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records: List[Dict[str, Any]] = []
    if not csv_path.exists():
        print(f"Warning: {csv_path} not found.")
        return records

    with open(csv_path, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):

            cleaned = {k.strip(): v.strip() for k, v in row.items() if k}
            cleaned["id"] = idx + 1
            records.append(cleaned)

    with open(output_path, mode="w", encoding="utf-8") as out:
        json.dump(records, out, indent=2)

    print(f"Ingested {len(records)} body measurement rows to {output_path}")
    return records

if __name__ == "__main__":
    ingest_body_measurements()
