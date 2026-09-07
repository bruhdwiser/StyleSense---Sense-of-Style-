# StyleSense AI — Technical Architecture

Companion to `plan.md` and `spec.md`.

## Stack

- **Frontend:** React + Vite + TypeScript + Tailwind CSS
- **Backend:** FastAPI + Python 3.10+
- **Database:** Postgres with pgvector extension
- **ORM:** SQLAlchemy 2.0 + Alembic
- **Auth:** JWT access/refresh tokens, bcrypt password hashing
- **Image/Object storage:** Local filesystem or S3-compatible object storage
- **Background workers:** Celery + Redis for ingestion, image processing, embedding generation, model retraining
- **Hosting:** Frontend and API deployed separately; workers run as independent processes

## Repo structure

```
frontend/
  src/
    components/
    pages/
    services/
    App.tsx
    main.tsx

backend/
  app/
    api/                  # FastAPI routers
    models/               # SQLAlchemy ORM models
    schemas/              # Pydantic request/response schemas
    services/             # Business logic: StyleDNA, ranking, analyzers, evaluator
    repositories/         # Data access layer
    workers/              # Celery tasks: ingestion, image processing, embeddings, retraining
    main.py               # FastAPI entrypoint
    config.py             # Settings / env config
  alembic/                # DB migrations
  tests/                  # Backend tests
  requirements.txt

data/
  raw/                    # Downloaded Kaggle files, never edited
  staging/                # Cleaned source-specific records
  processed/              # Normalized catalog and training sets

scripts/
  ingest/                 # Data ingestion scripts
  evaluate/               # Evaluation and training-curve scripts

infra/
  docker-compose.yml      # Postgres, Redis, API, workers, frontend

docs/                     # Architecture notes, runbooks
```

## Data model

Tables mirror the domain models in `spec.md`, implemented with SQLAlchemy:

- `users` — id, email, password_hash, created_at
- `profiles` — user_id, age_range, gender, height, weight, budget, preferred_brands[], aesthetics[], favorite_colors[], skin_tone, body_type, preferred_fit, fashion_goals[]
- `style_dna` — user_id, version, dominant_aesthetics[], color_palette[], preferred_silhouettes[], fit_preferences[], weights (JSON: tag → weight), updated_at
- `products` — id, name, image_url, price, brand, category, color_tags[], style_tags[], occasion_tags[], season_tags[], retailer_url, embedding (pgvector)
- `outfits` — id, user_id, occasion, budget, climate, total_price, created_at
- `outfit_items` — id, outfit_id, product_id (or wardrobe_item_id), role (top/bottom/shoes/accessory/outerwear)
- `wardrobe_items` — id, user_id, category, color, style_tags[], season, image_url, created_at
- `wishlist_items` — id, user_id, product_id or outfit_id, saved_at
- `interactions` — id, user_id, target_type (product/outfit), target_id, action (save/like/dismiss/open), created_at

pgvector is used for `products.embedding` to support visual similarity search and trend-aware candidate retrieval.

## Deployment architecture

```
Browser (mobile/desktop)
        |
        v
React frontend (Vite build)
        |
        v
FastAPI app (API routes)
        |
        +--> JWT auth (bcrypt, access + refresh tokens)
        +--> SQLAlchemy --> Postgres + pgvector
        +--> Object storage (user/product images)
        |
        v
Celery workers (Redis broker)
        |
        +--> Ingestion tasks (Myntra, PolyVore, skin-tone datasets)
        +--> Image processing (resize, thumbnail, feature extraction)
        +--> Embedding generation (product catalog)
        +--> Retraining tasks (StyleDNA weights, evaluator calibration)
```

This is a production-grade separation: the API stays responsive because long-running work happens in workers. The repo structure, data pipeline, and worker topology are all designed to grow beyond the MVP.

## Environment variables

```
DATABASE_URL=
REDIS_URL=
JWT_SECRET=
JWT_REFRESH_SECRET=
OBJECT_STORE_BUCKET=            # optional, for S3-compatible storage
OPENAI_API_KEY=                  # optional, for LLM-as-judge evaluator
```

## Local run

```bash
# Start dependencies
docker compose up -d postgres redis

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Workers (separate terminal)
celery -A app.workers worker --loglevel=info

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Upgrade path

- Add real CV models for body/outfit analysis without changing API contracts.
- Extend ingestion workers to new retailer APIs or social trend sources.
- Scale workers horizontally as interaction volume grows.
- Move from in-process recommendation scoring to a dedicated ranking service only if latency or traffic requires it.
