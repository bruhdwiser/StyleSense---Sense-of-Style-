# StyleSense AI — Build Plan

Companion to `spec.md` (scope/data model) and `arch.md` (stack/schema/deployment).

## Ground rules

- Work sequentially through the phases below.
- Commit after every completed task with a clear message.
- If a block is at risk of blowing its time box, use the fallback listed under it — never skip silently; leave a `# TODO` comment explaining what was cut and why.
- Keep the React frontend and FastAPI backend in the same repo, deployed separately. Reference `arch.md` for exact stack choices and `spec.md` for data shapes and algorithms.

---

## Phase 1 — Backend core & data layer (~1.5–2 h)

- [ ] Init backend FastAPI project structure per `arch.md`.
- [ ] Provision Postgres with pgvector and Redis; set `DATABASE_URL` and `REDIS_URL`.
- [ ] Define SQLAlchemy models per `arch.md` (`User`, `Profile`, `StyleDNA`, `Product`, `Outfit`, `OutfitItem`, `WardrobeItem`, `WishlistItem`, `Interaction`).
- [ ] Generate initial Alembic migration and apply it.
- [ ] Seed `products` from a normalized catalog (start with 150–300 curated items in `data/processed/products.json`).
- [ ] Set up JWT auth endpoints (`signup`, `login`, `refresh`). Test via curl/Postman before any UI exists.

**Definition of done:** API is live, DB is seeded, and a user can be created and authenticated.

**Fallback:** skip refresh tokens initially; use a single short-lived access token.

---

## Phase 2 — Frontend shell & onboarding (~1–1.5 h)

- [ ] Init React + Vite + TypeScript + Tailwind project in `frontend/`.
- [ ] Landing page (value prop + StyleDNA explainer).
- [ ] Signup/login pages wired to backend auth.
- [ ] Onboarding form: budget, preferred aesthetics, favorite colors, preferred fit, self-reported body type, fashion goals → writes to `Profile`.
- [ ] `computeStyleDNA(profile)` runs on profile save and stores result on `StyleDNA`.
- [ ] StyleDNA summary card UI + basic app shell/nav: Home, Build Outfit, Wardrobe, Wishlist, Profile.

**Definition of done:** a new user can sign up, complete onboarding, and see their StyleDNA summary.

**Fallback:** cut edit-profile; keep create-once onboarding only.

---

## Phase 3 — Recommendations & feedback loop (~1.5–2 h)

- [ ] Outfit request form: occasion, budget, climate, aesthetic constraints.
- [ ] `POST /api/recommendations` filters `Product` by budget/category/tags, scores by StyleDNA-tag overlap + occasion/climate match + static trend-weight bonus, assembles 3 complete looks.
- [ ] Explanation generator: template-based, cites the top 2–3 factors behind each recommendation.
- [ ] Results UI: outfit cards, price total, explanation panel, retailer-link buttons.
- [ ] Save / like / dismiss actions → write `Interaction`, nudge StyleDNA weights, confirm inline immediately.

**Definition of done:** a user can request an outfit and get back 3 explained, saveable recommendations.

**Fallback:** cut to 1 recommendation instead of 3 — but keep the explanation panel.

---

## Phase 4 — Wardrobe, wishlist, analyzers, polish (~1–1.5 h)

- [ ] Wardrobe CRUD: add item (name, category, color, season, optional photo), list/delete.
- [ ] Wardrobe-aware recommendation bonus: prefer combos reusing owned items when categories overlap.
- [ ] Wishlist save/remove for products and outfits.
- [ ] Body analyzer screen: photo upload UI + consent copy; result derived from self-reported body type (clearly labeled "estimate," not real CV).
- [ ] Outfit analyzer screen: photo upload UI; user manually tags visible garment categories, scoring runs against those tags.
- [ ] Loading/empty/error states; mobile responsive pass; basic keyboard nav + alt text.

**Definition of done:** every core PRD user flow is clickable end-to-end on mobile and desktop.

**Fallback:** cut the outfit analyzer before cutting wardrobe — wardrobe feeds the recommendation engine, the analyzer doesn't.

---

## Phase 5 — Workers, ingestion & deploy (~1–1.5 h)

- [ ] Celery + Redis wiring in `backend/app/workers/`.
- [ ] Ingestion worker: normalize Myntra/PolyVore/skin-tone datasets from `data/raw/` → `data/staging/` → `data/processed/` and load into Postgres.
- [ ] Image worker: generate thumbnails and store to object storage.
- [ ] Embedding worker: generate pgvector embeddings for product catalog.
- [ ] Retraining worker: expose a manual trigger to rerun the StyleDNA/evaluator training loop over accumulated interactions.
- [ ] `docker-compose.yml` to run postgres, redis, backend, frontend, and workers locally.
- [ ] Deploy frontend and API; smoke-test the full flow on the live URL.
- [ ] Write `README.md`: setup, run locally, deploy steps, and a short "what's real vs. mocked" section.

**Definition of done:** a stranger can open the live URL and complete the full flow without errors.

---

## Explicit cut list

- Live retailer scraping/catalog sync — use the seed dataset and ingestion scripts only.
- Real pose-landmark body analysis or garment-detection CV models.
- Live trend ingestion from external sources — use a static trend-weight JSON.
- Payment, checkout, or purchase flows (also a PRD non-goal).

These are natural next-phase items after the MVP.
