# StyleSense AI — Recommendation Engine Workflow (Dataset → Engine → Agent → Reward Model → Human Review)

This file governs how the **AI core** of StyleSense AI gets built: the recommendation engine, the rules it must obey, the agent that proposes outfits, and the reviewer that grades those outfits and pushes the agent to improve. It sits alongside `plan.md` (overall sprint plan), `spec.md` (data model/API), and `arch.md` (stack/schema).

**Read `concepts.md` first if you don't have an AI/ML background.** Every term used below (rule engine, agent, reward model, reward/penalty) is explained there in plain language with analogies.

## Agent instruction — keep the explainer file alive

Before starting each block below, append a section to `concepts.md` explaining, in plain beginner-friendly language with a simple analogy, what you're about to build and why it exists in this pipeline. Do this *before or alongside* implementation, not as an afterthought once the whole project is done. Use the template at the bottom of `concepts.md`. This is not optional — the person you're building this for is learning AI concepts through this project.

## Honesty check — what this workflow actually is

We are **not** training a neural network from scratch or running a full RL algorithm (e.g., PPO) — that requires far more data and compute than a student project has access to. What we're building is the same *pattern* at a scale that's actually achievable:

- A deterministic **rule engine** as ground truth (hard pass/fail).
- An **agent** (starts as a rule-based scorer, same as the StyleDNA/ranking logic from `spec.md`) that proposes candidate outfits.
- An **evaluator** that grades those candidates — partly with hard rule checks, partly with an LLM-as-judge call for softer qualities like style coherence. This stands in for a trained "reward model."
- A **feedback loop** that adjusts the agent's scoring weights based on the evaluator's grades — a simplified, weight-space version of reinforcement learning, not full RL.
- **Human review** that periodically checks whether the evaluator's judgment matches a real person's — this is the actual RLHF idea (a human calibrates the reviewer, not just the agent).

This is a real, defensible engineering pattern (portfolio-worthy on its own), just scoped to what's buildable without a research lab. `concepts.md` flags exactly where the "real" version would go further, if you want to extend this later.

---

## Block A — Dataset foundation

**Goal:** produce the data everything downstream depends on — the product catalog, and a set of labeled "example episodes" the agent can be evaluated against.

- [ ] Build the seeded product catalog (`data/processed/products.json`, 150–300 items) per `spec.md`, tagged by category/color/style/occasion/season/price.
- [ ] Generate a set of **synthetic episodes**: each episode = a fake user profile (budget, aesthetic, occasion, climate) + several candidate outfits, some deliberately rule-compliant and "good," some deliberately rule-violating or mismatched. Use the rule engine (Block B) itself to auto-generate and auto-label the violating ones — you don't need human labelers to get started.
- [ ] Optionally hand-rate a small batch (20–30 episodes) yourself for aesthetic quality, to sanity-check the evaluator later against real human judgment.

**Deliverable:** `data/processed/products.json`, `data/processed/trends.json`, and an `data/processed/episodes.json` of profile+candidate-outfit examples with rule-compliance labels.

## Block B — Rule engine (the referee)

**Goal:** encode every hard business rule from the PRD as code that can check *any* candidate outfit, regardless of who or what produced it.

- [ ] Budget rule: total price ≤ requested budget.
- [ ] Completeness rule: a "complete look" has top + bottom + shoes, accessory and outerwear optional.
- [ ] Occasion/climate rule: item tags must intersect the requested occasion/climate tags.
- [ ] One-role-per-item rule: no duplicate roles in a single outfit.
- [ ] Output shape: `check_outfit(outfit, request) → { pass: bool, violations: list[str] }`.

**Deliverable:** `backend/app/services/rule_engine.py`, unit-tested against both valid and intentionally-broken example outfits.

**Definition of done:** every rule has at least one passing and one failing test case.

## Block C — Baseline agent (rule-aware recommender)

**Goal:** the first version of the thing that actually proposes outfits — this is the ranking logic from `spec.md`, but built to generate *multiple* candidates so there's something for the evaluator to compare.

- [ ] Implement `compute_style_dna(profile)` (as in `spec.md`) producing tag → weight map.
- [ ] Implement `generate_candidates(request, style_dna, catalog) → list[Outfit]` — produce 5–8 candidate outfits per request (not just the final 3 shown to the user), so the evaluator in Block D has real variation to grade.
- [ ] Run every candidate through Block B's rule engine before it's even scored — reject hard failures immediately.

**Deliverable:** given any request, the agent produces multiple rule-checked candidate outfits with a raw StyleDNA score each.

## Block D — Evaluator / reward model (the AI reviewer)

**Goal:** grade each surviving candidate on both rule-compliance and subjective quality, producing a single reward score.

- [ ] Deterministic layer: reuse Block B's `check_outfit` — any violation caps the reward near zero regardless of anything else.
- [ ] Quality layer: for candidates that pass, call an LLM-as-judge with a fixed rubric prompt — score color harmony, occasion-fit, and explanation clarity 0–10 each, return JSON + a one-line reason. This is your stand-in for a trained reward model; document in `concepts.md` why an LLM judge is a reasonable substitute at this scale.
- [ ] Combine: `reward = passed ? weighted_average(quality_scores) : penalty (e.g. -1)`.
- [ ] Log every `(outfit, reward, violations, judge_reasoning)` tuple — this log is what Block E trains on.

**Deliverable:** `backend/app/services/evaluator.py` — `evaluate_outfit(outfit, request) → { reward, violations, judge_reasoning }`.

## Block E — Reward & penalty training loop

**Goal:** use the evaluator's scores to actually improve the agent's future recommendations, closing the loop.

- [ ] Offline pass: run every episode from Block A's dataset through Block C (generate candidates) → Block D (evaluate) → collect rewards.
- [ ] Weight update rule (simplified policy update, no deep learning required): for each tag present in a candidate, `weight[tag] += learning_rate * reward`. High-reward outfits pull their tags' weights up; rule-violating or low-quality outfits pull them down. Clip weights to a sane range (e.g., 0–3) so nothing runs away.
- [ ] Re-run the offline pass for a few rounds and confirm average reward across the episode set trends upward — this is your "training curve," plot it even as a simple line chart.
- [ ] Online pass (after deployment): every real `Interaction` (save/like/dismiss) is itself a reward signal — feed it into the same weight-update function, same as `spec.md`'s original StyleDNA nudge, but now unified with the offline training signal.

**Deliverable:** `backend/app/services/train_loop.py` (`run_training_round(episodes)`), plus a simple `training_log.json` showing reward improving across rounds.

**Definition of done:** average reward across the synthetic episode set is measurably higher after 3–5 training rounds than at round 0.

## Block F — Human-in-the-loop calibration

**Goal:** make sure the evaluator itself is trustworthy — an automated judge that nobody checks can drift into rewarding the wrong things (this is the actual point of RLHF: humans calibrate the reviewer, not just the agent).

- [ ] Sample ~20 evaluated outfits (mix of high- and low-reward).
- [ ] You (or a few test users) rate them blind, without seeing the evaluator's score.
- [ ] Compare human ratings to evaluator rewards. Where they disagree often, refine the judge's rubric prompt in Block D — this is prompt iteration, not code changes, and is the cheap/fast version of "retraining the reward model."
- [ ] Repeat once after your first refinement to confirm agreement improved.

**Deliverable:** a short `calibration-notes.md` (or a section in `concepts.md`) documenting the disagreement rate before/after rubric refinement.

## Block G — Integration, monitoring, continuous learning

**Goal:** wire the tuned agent into the actual product and keep the loop running on real usage.

- [ ] Plug the Block C/D/E pipeline into `POST /api/recommendations` from `spec.md` — the API returns the top 3 candidates by final reward, with the judge's reasoning feeding the user-facing explanation text.
- [ ] Log every production recommendation + its reward + the user's eventual action into `interactions` (already in the schema).
- [ ] Add a manually-triggerable "retrain" Celery task that reruns Block E's loop over accumulated real interactions — schedule it as a cron/beat job later; a manual trigger is fine for a demo.

**Deliverable:** live recommendations are produced by the trained/tuned agent, not the untouched Block C baseline, and every real interaction becomes future training data.

---

## Block sequencing summary

```
A. Dataset  →  B. Rule engine  →  C. Baseline agent  →  D. Evaluator/reward model
                                                               │
                                                               ▼
                                           E. Reward/penalty training loop
                                                               │
                                                               ▼
                                           F. Human calibration of the evaluator
                                                               │
                                                               ▼
                                           G. Integration + continuous learning
```

Each block's `concepts.md` entry should be written before that block's code — treat the explanation as part of the deliverable, not documentation bolted on afterward.
