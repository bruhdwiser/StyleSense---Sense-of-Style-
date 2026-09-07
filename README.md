# StyleSense AI — Hyper-Personalized AI Stylist & Recommendation Engine

StyleSense AI is an explainable fashion styling application combining deterministic rule-engine constraints, dynamic taste-graph learning (StyleDNA), wardrobe-aware outfit generation (₹0 cost for owned garments), and heuristic body/outfit analyzers.

---

## Architecture Diagram

```
+-------------------------------------------------------------------------+
|                  React Frontend (Vite, TypeScript)                      |
|  - Adaptive Theme (Dark Obsidian & Studio Light)                        |
|  - StyleDNA Quiz & Visual Taste Graph Radar                             |
|  - Outfit Builder (Occasion, Budget Slider, Climate)                    |
|  - Digital Wardrobe Manager & Wishlist Tracker                          |
|  - Heuristic Body & Outfit Analyzers                                    |
|  - Interactive AI Lab & Rule Inspector                                  |
+------------------------------------+------------------------------------+
                                      |
                           REST API JSON over HTTP
                                      |
+------------------------------------+------------------------------------+
|                      FastAPI Backend Server                            |
+------------------------------------+------------------------------------+
|                                    |
|  +---------------------------+     |     +---------------------------+
|  |     StyleDNA Engine       |     |     |    Deterministic Floor    |
|  | - Preference Weight Map   |     |     | - Budget Cap Validator    |
|  | - +0.1 Like/Save Nudge    |<----+---->| - Completeness Check      |
|  | - -0.1 Dismiss Floor (0.0)|     |     | - Occasion/Season Match   |
|  | - Plain-Language Persona  |     |     | - Unique Role Enforcement |
|  +---------------------------+     |     +---------------------------+
|                                    |
|  +---------------------------+     |     +---------------------------+
|  |   Recommendation Engine   |     |     |    Heuristic Analyzers    |
|  | - Multi-Candidate Search  |     |     | - Body Frame Fit Advice   |
|  | - StyleDNA Overlap Score  |<----+---->| - Outfit Harmony Check    |
|  | - Static Trend Bonus      |     |     | - Explicit Estimate Badge |
|  | - Wardrobe Reuse (+0.5)   |     |     +---------------------------+
|  | - Template Explainability |     |
|  +---------------------------+     |     +---------------------------+
|                                    |     |   Static Seed Datasets    |
|                                    +---->| - 36 Curated Products(INR)|
|                                          | - Trend Matrix (2026)     |
|                                          | - Default Demo Persona    |
|                                          +---------------------------+
+------------------------------------+------------------------------------+
                                      |
                                      v
                              Postgres + pgvector
                              Users, products, interactions,
                              outfits, wardrobe, wishlist
                                      |
                                      v
                              Background workers
                              Ingestion, image processing,
                              embeddings, retraining
                                      |
                                      v
                              Object storage
                              User images and product images
+-------------------------------------------------------------------------+
```

---

## Installation & Setup

### 1. Backend Setup (FastAPI)

Ensure Python 3.10+ is installed:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Start Postgres + Redis with Docker:

```bash
docker compose up -d
```

Run database migrations:

```bash
alembic upgrade head
```

Run FastAPI backend server:

```bash
uvicorn app.main:app --reload
```

The backend server starts at `http://127.0.0.1:8000`.

### 2. Workers Setup (Celery)

In a separate terminal:

```bash
cd backend
celery -A app.workers worker --loglevel=info
```

### 3. Frontend Setup (React + Vite)

Ensure Node.js 18+ is installed:

```bash
cd frontend
npm install
npm run dev
```

The frontend application opens at `http://localhost:3000`.

---

## REST API Route Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status and catalog product count |
| `GET` | `/api/products` | Complete list of curated fashion items in INR (₹) |
| `POST` | `/api/profile` | Saves user preferences & computes normalized StyleDNA |
| `GET` | `/api/styledna` | Fetches active StyleDNA tag weights & summary |
| `POST` | `/api/recommendations` | Assembles 3 distinct, ranked, rule-passing outfits |
| `POST` | `/api/interactions` | Records like/save/dismiss and nudges tag weights |
| `GET` | `/api/wardrobe` | Lists items in user digital closet |
| `POST` | `/api/wardrobe` | Adds owned item into digital wardrobe |
| `DELETE` | `/api/wardrobe/{id}` | Deletes item from digital wardrobe |
| `GET` | `/api/wishlist` | Lists saved outfits and products |
| `POST` | `/api/wishlist` | Saves look to wishlist |
| `DELETE` | `/api/wishlist/{id}` | Removes look from wishlist |
| `POST` | `/api/analyze/body` | Returns heuristic silhouette & fit advice |
| `POST` | `/api/analyze/outfit` | Evaluates garment harmony, completeness, and occasion |
| `GET` | `/api/ai-lab/eval` | Evaluates rule unit tests & training curve for inspector |

---

## Real vs. Mocked Architecture Breakdown

| Feature Area | Current Implementation (MVP Baseline) | Production Roadmap Upgrade |
|---|---|---|
| **Product Catalog** | 36 curated items in INR with tags (`backend/app/models/product.py`) | Kaggle fashion datasets or live retailer APIs |
| **Trend Scoring** | Static seasonal trend weights (`backend/app/models/trends.py`) | Real-time trend scraping and social signal ingestion |
| **Recommendation Engine** | Deterministic rule floor + multi-attribute weighted scoring | Vector embeddings (pgvector) + learned ranker model |
| **StyleDNA Feedback** | Real-time tag-weight adjustment (+0.1 / -0.1 floor 0) | Contextual multi-armed bandit / neural collaborative filter |
| **Body Analyzer** | Rule-based geometric silhouette guidance | Pose-landmark 3D computer vision model |
| **Outfit Analyzer** | Multi-select garment palette and completeness rules | Computer vision object detection and segmentation |
| **Database** | Postgres + pgvector via SQLAlchemy/Alembic | Managed Postgres with read replicas |

---

## Future Kaggle Dataset Migration Path

When migrating to a full Kaggle fashion dataset:

1. Place the raw CSV or JSON dataset into `data/raw/`.
2. Run a normalization script in `scripts/ingest/` to map columns into the `Product` schema.
3. Store normalized records in `data/staging/` and then `data/processed/`.
4. Load processed catalog into Postgres via a background worker or migration script.
5. **Zero Frontend/API Changes**: The API returns identical JSON structures (`id`, `name`, `brand`, `price`, `category`, `image_url`), so the frontend UI, recommendation engine, and rule validator work seamlessly without modification.

---

## 60-Second Review Demo Script

1. **0:00 - 0:10 (Landing & Problem)**:
   - "StyleSense AI is an explainable personal stylist. Rather than giving black-box recommendations, it enforces strict budget rules and integrates clothes you already own."
2. **0:10 - 0:25 (StyleDNA Quiz & Dashboard)**:
   - Navigate to **Take StyleDNA Quiz**.
   - Select Minimalist & Streetwear, Black/Beige/Navy colors, Relaxed fit, and a ₹4,000 budget cap.
   - Click **Save & Compute StyleDNA** to view the personalized Taste Graph and summary.
3. **0:25 - 0:40 (Outfit Builder & Explainability)**:
   - Click **Build Outfit** for a *Smart Casual Evening* with a ₹4,000 budget.
   - Point out how the top 3 looks stay within budget, showcase owned items at ₹0 cost, and display clear stylist rationale badges.
   - Click **Like** or **Save** on Look #1 to demonstrate real-time weight updates.
4. **0:40 - 0:50 (Wardrobe Integration)**:
   - Open **Wardrobe**, click **Add Clothing Item** (e.g. "Matte Black Turtleneck", Top, Black).
   - Return to **Build Outfit** and regenerate: observe how the new piece is automatically integrated with savings.
5. **0:50 - 1:00 (AI Lab & Rule Inspector)**:
   - Open the **AI Lab** tab to show the live rule verification matrix (100% budget, completeness, and role enforcement) and simulated reinforcement learning training curve.
