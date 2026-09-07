# StyleSense AI — MVP Functional & Technical Spec

Companion to `plan.md` (execution order) and `arch.md` (stack/schema/deployment).

## In scope

- Account creation, login, profile management
- Style-preference onboarding → StyleDNA profile (rule-based, not ML-trained)
- Outfit request flow → ranked, explained outfit recommendations from a seeded product catalog
- Save / like / dismiss feedback loop that nudges StyleDNA
- Digital wardrobe (manual entry) feeding into recommendations
- Wishlist for products and outfits
- Body analyzer & outfit analyzer screens with **heuristic-based, clearly-labeled-as-estimate** output (not real computer vision)
- Responsive, accessible UI (mobile-first)
- Public deployment

## Out of scope for this build

Real retailer catalog sync, live trend ingestion, real CV models, vector embeddings, payments/checkout. See `plan.md`'s cut list.

## User flows

1. **Onboarding:** Landing → Sign up → Consent → Preference quiz → StyleDNA summary.
2. **Outfit request:** Home → "Build an outfit" → occasion/budget/climate/aesthetic form → 3 recommended looks → explanation → save/like/dismiss/open.
3. **Wardrobe:** Add owned items → items factor into future outfit recommendations (bonus score for reusing owned pieces).
4. **Wishlist:** Save any product or outfit from anywhere; revisit/remove later.
5. **Body analyzer:** Upload photo (optional) → estimate-labeled fit/silhouette guidance.
6. **Outfit analyzer:** Upload current outfit photo → estimate-labeled style/fit/occasion feedback.

## Data model

See `arch.md` for the full SQLAlchemy schema. Summary:

- `User` — id, email, password_hash, created_at
- `Profile` — user_id, age_range, gender, height, weight, budget, preferred_brands[], aesthetics[], favorite_colors[], skin_tone, body_type, preferred_fit, fashion_goals[]
- `StyleDNA` — user_id, version, dominant_aesthetics[], color_palette[], preferred_silhouettes[], fit_preferences[], weights (JSON: tag → weight)
- `Product` — id, name, image_url, price, brand, category, color_tags[], style_tags[], occasion_tags[], season_tags[], retailer_url, embedding (pgvector)
- `Outfit` — id, user_id, occasion, budget, climate, total_price, created_at
- `OutfitItem` — outfit_id, product_id (or wardrobe_item_id), role (top/bottom/shoes/accessory/outerwear)
- `WardrobeItem` — user_id, category, color, style_tags[], season, image_url
- `WishlistItem` — user_id, product_id or outfit_id, saved_at
- `Interaction` — user_id, target_type (product/outfit), target_id, action (save/like/dismiss/open), created_at

## StyleDNA algorithm (rule-based, no ML training)

On profile save/update, compute weights as a JSON map from tag → score:

1. Seed weights directly from selected aesthetics, colors, and fit preferences (score `1.0` each).
2. On every `Interaction`: `like` / `save` / `open` → `+0.1` to the weight of every tag on the target item; `dismiss` → `-0.1` (floor at `0`).
3. StyleDNA summary UI shows the top 3–5 tags by weight, phrased in plain language (e.g., "You lean toward relaxed, neutral-toned streetwear").

## Ranking algorithm (recommendation engine)

For a given outfit request (occasion, budget, climate, aesthetic):

1. Hard filter: candidate `Product`s must fit the remaining budget after assembling a look; `occasion_tags` / `season_tags` must roughly match the requested occasion/climate.
2. Score = `Σ(StyleDNA.weights[tag] for tag in product.style_tags ∩ profile tags)` + trend bonus (static lookup by category/color) + wardrobe-reuse bonus (`+0.5` if an owned wardrobe item can fill a role instead of a purchased product) + pgvector similarity bonus (if embeddings are available).
3. Assemble 3 alternative complete looks (top + bottom + shoes + accessory + optional outerwear) maximizing score subject to the budget constraint.
4. Generate explanation text using this template: `"Recommended because it matches your {top matching tag}, fits your {occasion} budget, and {wardrobe-reuse or trend note if applicable}."`

## API endpoints

- `POST /api/auth/signup`, `/api/auth/login`
- `GET/PUT /api/profile`
- `GET /api/styledna`
- `POST /api/recommendations` — body: `{occasion, budget, climate, aesthetic}` → returns 3 `Outfit` objects with items + explanations
- `POST /api/interactions` — body: `{target_type, target_id, action}`
- `GET/POST/DELETE /api/wardrobe`
- `GET/POST/DELETE /api/wishlist`
- `POST /api/analyze/body`, `POST /api/analyze/outfit` — accept image, return heuristic estimate JSON (see "Mocked components" below)
- `GET /api/ai-lab/eval` — Evaluates rule unit tests & training curve for inspector

## Mocked components — label clearly in UI and in demo narration

- **Body analyzer:** does not run pose-landmark detection. Returns fit guidance derived from `Profile.body_type` (plus a light randomization seed from the uploaded photo's aspect ratio, so results feel responsive without claiming real CV). UI copy: *"Estimated guidance based on your profile — full photo-based analysis is on the roadmap."*
- **Outfit analyzer:** does not run garment detection. The user manually tags the categories present in their photo (quick multi-select); scoring runs against those tags. Same explicit caveat in the UI.
- **Trend intelligence:** static seed file, not live-ingested.
- **Product catalog:** seed dataset only (see `arch.md`), not a live retailer sync.

## Definition of done / smoke test checklist

- [ ] New user can sign up, onboard, and see a StyleDNA summary
- [ ] Outfit request returns 3 distinct, explained, budget-respecting looks
- [ ] Save/like/dismiss visibly changes future recommendation scores
- [ ] Wardrobe item reduces price or adds a reuse note on a subsequent recommendation
- [ ] Wishlist add/remove works
- [ ] Body/outfit analyzer screens return labeled-as-estimate results without erroring
- [ ] App is usable on a 375px-wide viewport
- [ ] Deployed URL is publicly reachable and completes the full flow
