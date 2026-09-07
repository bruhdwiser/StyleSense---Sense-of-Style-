# StyleSense AI — Production Plan: StyleDNA, Rule, Recommendation & Feedback Engines

## Goals

Build a production-grade, event-driven fashion recommendation system with:
- **StyleDNA engine**: per-user taste profile as a live tag-weight map
- **Rule engine**: deterministic hard constraints for budget, completeness, occasion, and role uniqueness
- **Recommendation engine**: candidate generation + scoring + explanation
- **Feedback engine**: async event ingestion that updates StyleDNA and recommendation signal in real time

All four engines must work with the current `Static_Seedings/` catalog and be ready for the future Catalogue engine normalization pipeline.

---

## 1. Event Schema (Feedback Engine Foundation)

All user interactions are emitted as events from the frontend and persisted before any business logic runs.

**Table: `interaction_events`**

| Column | Type | Purpose |
|---|---|---|
| `id` | UUID | Primary key |
| `user_id` | FK → users | Owner of the event |
| `session_id` | string | Frontend session for deduplication |
| `event_type` | enum | `impression`, `click`, `save`, `like`, `dismiss`, `rating`, `wardrobe_add` |
| `target_type` | enum | `product`, `outfit` |
| `target_id` | string | Product or outfit ID |
| `payload` | JSONB | `{rating, dwell_time_ms, position, request_context}` |
| `idempotency_key` | string | `sha256(user_id + session_id + event_type + target_id + created_at)` |
| `created_at` | datetime | Event timestamp |

**Event → weight delta mapping:**

| Event type | Weight delta | Notes |
|---|---|---|
| `like` / `save` | +0.1 | Explicit positive signal |
| `dismiss` | -0.1 | Explicit negative signal |
| `rating` (4–5) | +0.1 | High rating |
| `rating` (1–2) | -0.1 | Low rating |
| `rating` (3) | 0 | Neutral |
| `click` | +0.02 | Weak positive signal |
| `impression` | 0 | Logged but no weight change |
| `wardrobe_add` | +0.05 | Ownership is a strong positive |

---

## 2. Data Flow

```
Frontend
  │
  ▼
POST /api/events  ──►  interaction_events table (idempotent insert)
  │
  ▼
Celery worker: process_event
  │
  ├─► Update StyleDNA weights (immediate per-event)
  │
  └─► Write Interaction record (for analytics/offline training)
        │
        ▼
  StyleDNA weights updated in Postgres
  │
  ▼
Next recommendation request reads updated weights
```

**Key constraint:** The API must return 202 Accepted immediately after persisting the event. Weight updates happen in the worker, not in the request path.

---

## 3. StyleDNA Engine

**Location:** `backend/app/services/styledna.py`

### 3.1 Core Data Model

```python
style_dna:
  user_id: FK
  version: int            # increments on every weight change
  weights: JSONB          # {tag: float}
  dominant_tags: string[] # cached top 5 tags for fast reads
  summary: text           # plain-language persona string
  updated_at: datetime
```

### 3.2 Functions

- **`compute_style_dna(profile: Profile) -> StyleDNA`**
  - Input: user profile (aesthetics, colors, fit, body type, goals)
  - Seed weights: `1.0` for each selected aesthetic, color, and fit tag
  - Generate plain-language summary from top 3–5 tags
  - Persist and return StyleDNA record

- **`apply_event_feedback(user_id: str, event: InteractionEvent) -> None`**
  - Look up active StyleDNA for user
  - For each tag on the event target, apply delta from the mapping above
  - Clip all weights to `[0.0, 3.0]`
  - Bump `version` and update `dominant_tags` + `summary`
  - Persist atomically

- **`get_style_dna_summary(user_id: str) -> dict`**
  - Return top tags + plain-language summary for the frontend

### 3.3 Tag Vocabulary

Define a controlled vocabulary for tags in `backend/app/models/tag_vocabulary.py`:
- Aesthetics: `minimalist`, `streetwear`, `formal`, `casual`, `bohemian`, `athleisure`, `ethnic`
- Colors: `black`, `white`, `navy`, `grey`, `beige`, `brown`, `red`, `blue`, `green`, `pink`, `purple`
- Silhouettes: `slim`, `regular`, `relaxed`, `oversized`, `fitted`
- Fits: `slim_fit`, `regular_fit`, `relaxed_fit`, `loose_fit`
- Seasons: `summer`, `winter`, `monsoon`, `spring`, `fall`
- Occasions: `casual`, `formal`, `party`, `sports`, `ethnic`, `workwear`

The Catalogue engine will extend this vocabulary; for now, static seedings are mapped via lookup tables.

---

## 4. Rule Engine

**Location:** `backend/app/services/rule_engine.py`

Pure functions. No side effects. Unit-testable in isolation.

### 4.1 Rules

```python
def check_budget(outfit_total_price: int, budget: int) -> RuleResult:
    return pass if total <= budget else fail("Budget exceeded")

def check_completeness(items: list[OutfitItem]) -> RuleResult:
    required_roles = {"top", "bottom", "shoes"}
    present_roles = {item.role for item in items}
    missing = required_roles - present_roles
    return pass if not missing else fail(f"Missing: {missing}")

def check_occasion_climate(items: list[OutfitItem], request: Request) -> RuleResult:
    # At least one item must match requested occasion/season tags
    ...

def check_unique_roles(items: list[OutfitItem]) -> RuleResult:
    roles = [item.role for item in items]
    return pass if len(roles) == len(set(roles)) else fail("Duplicate roles")
```

### 4.2 Composite Check

```python
def check_outfit(outfit: Outfit, request: Request) -> Envelope:
    results = [
        check_budget(outfit.total_price, request.budget),
        check_completeness(outfit.items),
        check_occasion_climate(outfit.items, request),
        check_unique_roles(outfit.items),
    ]
    violations = [r.reason for r in results if not r.pass]
    return Envelope(pass=len(violations) == 0, violations=violations)
```

### 4.3 Testing

- Every rule must have ≥1 passing and ≥1 failing test case
- Edge cases: zero budget, empty item list, duplicate roles, missing required tags

---

## 5. Recommendation Engine

**Location:** `backend/app/services/recommendation.py`

### 5.1 Pipeline

```
Request(occasion, budget, climate, aesthetic)
  │
  ▼
Candidate Generation
  │  - Query products matching occasion/season/budget
  │  - Generate 5–8 complete looks (top + bottom + shoes + accessory + optional outerwear)
  │  - Prefer wardrobe reuse (owned items cost ₹0 and get +0.5 score bonus)
  │
  ▼
Rule Engine Filter
  │  - Reject any candidate failing check_outfit()
  │
  ▼
Scoring
  │  score = (
  │    Σ(StyleDNA.weights[tag] for tag in product.style_tags ∩ request_tags)
  │    + trend_bonus (static lookup)
  │    + wardrobe_reuse_bonus (+0.5 per owned item used)
  │    + pgvector_similarity_bonus (0.0–0.3, only when embeddings exist)
  │  )
  │
  ▼
Ranking & Selection
  │  - Sort by score descending
  │  - Take top 3 distinct looks
  │
  ▼
Explanation Generation
  │  - Template: "Recommended because it matches your {top_tag}, fits your {occasion} budget,
  │    and {reuses_item / follows_trend_note}."
  │
  ▼
Response
     - 3 Outfit objects with items, prices, explanations, and retailer links
```

### 5.2 Candidate Generation Strategy

- **Wardrobe-first**: For each role, check if the user owns a matching wardrobe item. If yes, lock it in and search for the remaining roles.
- **Diversity**: Ensure the 3 final outfits differ in at least 2 roles or dominant color palette.
- **Price balancing**: If one outfit is well under budget, allow a slightly higher-scoring item in another role.

### 5.3 pgvector Integration (Future-Proofed)

- `products.embedding` column exists in schema but is nullable.
- When embeddings are present (generated by Catalogue engine or image worker), add a `0.0–0.3` similarity bonus to the score.
- When embeddings are absent, the bonus is `0.0` and the engine falls back to pure tag-overlap scoring.
- No code changes needed in the frontend or API layer.

---

## 6. Feedback Engine

**Location:** `backend/app/services/feedback.py` + `backend/app/workers/tasks.py`

### 6.1 API Layer

**Endpoint:** `POST /api/events`

Request body:
```json
{
  "session_id": "abc123",
  "events": [
    {
      "event_type": "click",
      "target_type": "product",
      "target_id": "prod_42",
      "payload": {"position": 2, "dwell_time_ms": 3000}
    }
  ]
}
```

Response: `202 Accepted` with `{accepted: int}` — never blocks on worker execution.

### 6.2 Worker Pipeline

```python
@celery.task(bind=True, max_retries=3)
def process_event(self, event_payload: dict):
    # 1. Idempotency check
    if exists_interaction_event(idempotency_key=event_payload["idempotency_key"]):
        return

    # 2. Persist raw event
    save_interaction_event(event_payload)

    # 3. Apply StyleDNA weight update (immediate per-event)
    apply_event_feedback(event_payload["user_id"], event_payload)

    # 4. Write Interaction record for analytics
    save_interaction(event_payload)
```

### 6.3 Idempotency & Ordering

- **Idempotency**: Reject duplicate `idempotency_key` values. Frontend generates the key.
- **Ordering**: Events within a session are processed in `created_at` order. If a worker crashes mid-batch, unacked events are requeued by Celery + Redis.
- **At-least-once delivery**: The idempotency key makes processing safe.

### 6.4 Dual Improvement Signal

The feedback engine improves both engines simultaneously:

| Engine | Improvement Mechanism |
|---|---|
| **StyleDNA** | Immediate weight nudges per event. Next request uses updated weights. |
| **Recommendation** | 1) Real-time: updated StyleDNA changes ranking. 2) Offline: all events logged for future batch retraining of trend weights or candidate-generation heuristics. |

---

## 7. Static Seeding → Catalogue Engine Handoff

### 7.1 Ingestion Scripts

**Location:** `scripts/ingest/`

- `ingest_styles_csv.py`: Parse `Static_Seedings/styles.csv` → normalized `Product` records
  - Map `articleType` → `category`
  - Map `baseColour` → `color_tags`
  - Map `usage` → `occasion_tags`
  - Map `season` → `season_tags`
  - Extract style tags from `productDisplayName` using keyword rules
  - Assign placeholder `price` based on category (e.g., shirts = ₹800–₹2000, shoes = ₹1500–₹4000)
  - Set `retailer_url` to Myntra product page or placeholder

- `ingest_product_images.py`: Scan `Static_Seedings/Products/*` → copy to object storage, generate thumbnails, update `Product.image_url`

- `ingest_body_measurements.py`: Load CSV into `body_measurements` table for analyzer heuristics

- `ingest_skin_tone_images.py`: Copy skin-tone folders to object storage, create `SkinToneReference` records

### 7.2 Catalogue Engine Contract (Future)

The future Catalogue engine must produce the same normalized schema:

```python
class NormalizedProduct(BaseModel):
    id: str
    name: str
    brand: str
    price: int
    category: str           # top, bottom, shoes, accessory, outerwear
    color_tags: list[str]
    style_tags: list[str]
    occasion_tags: list[str]
    season_tags: list[str]
    gender: str
    image_url: str
    retailer_url: str
    embedding: list[float] | None  # pgvector, optional
```

**Handoff rule:** When the Catalogue engine is ready, it writes to `data/processed/products.json`. The existing ingestion scripts are replaced by a single call to the Catalogue engine output. No downstream engine (StyleDNA, Rule, Recommendation, Feedback) needs to change.

---

## 8. Implementation Order

### Phase 1 — Data Layer & Ingestion
1. Write ingestion scripts for `Static_Seedings/styles.csv` and `Products/` images
2. Load normalized catalog into Postgres
3. Verify product count and tag coverage

### Phase 2 — StyleDNA & Rule Engines
4. Implement `compute_style_dna()` and `apply_event_feedback()`
5. Implement rule engine with unit tests
6. Seed a demo user + profile + StyleDNA

### Phase 3 — Recommendation Engine
7. Implement candidate generation with wardrobe-first strategy
8. Implement scoring with StyleDNA overlap + trend bonus + wardrobe reuse
9. Implement explanation template
10. Return top 3 outfits with explanations

### Phase 4 — Feedback Engine
11. Create `interaction_events` table and API endpoint
12. Implement Celery worker for async event processing
13. Wire frontend event emission (clicks, impressions, saves, likes, dismiss, ratings)
14. Verify StyleDNA weights update after interactions

### Phase 5 — Integration & Validation
15. End-to-end smoke test: signup → onboarding → build outfit → interact → request again → weights changed
16. Load test: 100 concurrent event submissions
17. Document handoff point for Catalogue engine

---

## 9. Validation & Smoke Tests

| Test | Expected Result |
|---|---|
| Signup + onboarding | User created, StyleDNA computed, summary returned |
| Build outfit (budget ₹4000) | 3 outfits returned, all pass rule engine, total ≤ ₹4000 |
| Like an outfit | StyleDNA weights for that outfit's tags increase by +0.1 |
| Dismiss an outfit | StyleDNA weights for that outfit's tags decrease by -0.1 |
| Wardrobe item added | Next recommendation reuses it and shows ₹0 cost |
| 100 concurrent events | All persisted, no lost updates, no duplicate weight changes |
| Frontend event emission | Every click/impression/save/like/dismiss/rating reaches `/api/events` |

---

## 10. Out of Scope

- Real pose-landmark body analysis or garment-detection CV models
- Live trend ingestion from external sources
- Payment/checkout flows
- Multi-tenant or organization features
- A/B testing framework for StyleDNA algorithm variants

These are natural next-phase items after the MVP.
