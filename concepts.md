# StyleSense AI — AI Concepts, Explained (No Background Assumed)

This file exists because you're building an AI product without an AI background yet. Every time the build touches a new AI concept, an explanation gets added here in plain language — this file should end up as a working glossary of *your own project*, not a generic AI textbook.

**Agent:** append to this file (using the template at the bottom) before or during each block of `workflow.md`, not after the project is finished.

---

## The big picture, in one paragraph

You're building a system that recommends outfits. Instead of just writing "if budget < X and color matches, show it" and calling it done, you're building a small feedback loop: a set of unbreakable rules (Block B), an agent that proposes outfits while trying to satisfy those rules and match a user's taste (Block C), a reviewer that grades how well it did (Block D), and a mechanism that nudges the agent to do better next time based on that grade (Block E), with a human occasionally checking that the reviewer itself is grading fairly (Block F). That whole loop — propose, grade, adjust, repeat — is the core idea behind how modern AI systems like Claude are refined, just at a scale you can actually build and understand.

## 1. Dataset — what it is and why it matters

A dataset is just "examples the system can learn from or be tested against." In this project that means: the product catalog (the items it can recommend) and a set of "episodes" — a fake user request plus several candidate outfits, some good, some deliberately bad. Why deliberately bad ones? Because you can't tell if a reviewer (Block D) is any good unless you already know some outfits *should* fail and some *should* pass — the bad examples are your answer key.

## 2. Rule engine vs. machine learning model — the key distinction

A **rule engine** is code you write by hand: "if total price > budget, reject." It's 100% predictable and 100% explainable, but it can only catch things you thought to write a rule for.

A **machine learning model** (or in our simplified case, a weighted scoring formula) *learns* patterns from data instead of being told them explicitly — it can pick up on things like "this user tends to like earthy tones even though they never said so," which no one wrote a rule for.

This project deliberately uses **both**: the rule engine is the non-negotiable floor (budget, completeness, occasion-fit), and the learned/weighted layer on top handles the fuzzier "does this match their taste" question. Never let the learned layer override a rule-engine failure — that's what keeps the system trustworthy even while it's still learning.

## 3. Agent — what "agent" means here

In AI, an "agent" is anything that takes in a situation and decides on an action. Here, the agent's "situation" is a user's outfit request (occasion, budget, climate, their StyleDNA), and its "action" is proposing a set of candidate outfits. It's not a chatbot or a separate AI model talking to you — it's the piece of code (`generateCandidates`) that makes proposals. Calling it an "agent" instead of "a function" is useful because you'll be evaluating and improving its *behavior over time*, the same way you'd evaluate a person's decisions rather than just checking their homework once.

## 4. Reward model / evaluator — the strict teacher

A **reward model** is a system whose only job is to look at something the agent produced and assign it a score — a number that says "how good was this." In full-scale AI systems (like RLHF used to train Claude), this is itself a trained neural network built from thousands of human comparisons ("output A is better than output B").

At project scale, we build a lighter but structurally identical thing: a mix of (a) the rule engine as a hard pass/fail, and (b) an LLM (Claude API) prompted with a fixed grading rubric to score the softer stuff — does this outfit look coherent, does the explanation make sense. This "AI judging AI" pattern is a real, used technique (sometimes called RLAIF — reinforcement learning from *AI* feedback, as opposed to RLHF's *human* feedback) and it's a reasonable stand-in when you don't have the resources to collect thousands of human ratings.

## 5. Reward, penalty, and the training loop

Think of it like a thermostat, not a punishment. Every time the agent proposes an outfit, the evaluator hands back a number: high reward if it followed the rules and looked good, a penalty (a low or negative number) if it broke a rule or looked mismatched. The training loop then nudges the *weights* behind the agent's decisions — tags that show up in high-reward outfits get slightly more influence next time, tags in penalized outfits get slightly less. Do this over many examples and the agent's proposals drift toward what actually scores well, without anyone hand-tuning every weight.

This is the same core idea as reinforcement learning (try something, get a signal for how good it was, adjust, repeat) — just without the heavier machinery (neural network policy, gradient descent over millions of parameters) that full RL uses. We're doing RL's *idea* with a simple weighted-average update instead of RL's *algorithm*.

## 6. Human-in-the-loop / RLHF — why a human still checks in

Here's the trap: if you let an AI reviewer grade an AI agent with no human ever checking the reviewer, the agent can learn to satisfy the reviewer specifically, rather than actually being good — a failure mode called "reward hacking." That's why Block F exists: periodically, a human rates a sample of outputs *without* seeing the AI reviewer's score, then you compare. If the human and the AI reviewer disagree a lot, you fix the reviewer's grading rubric — not the agent. This human-calibrates-the-reviewer step is literally what "RLHF" (Reinforcement Learning from Human Feedback) means in the models you've heard of — human judgment shapes the *reward signal*, not just the final output.

## 7. What this project is NOT (be clear-eyed about this)

- Not training a neural network from scratch — no gradient descent over model weights, no GPUs required.
- Not full reinforcement learning (no PPO/policy-gradient algorithm, no simulation environment).
- Not a trained reward model in the strict sense — the "reward model" here is a rule engine plus an LLM-as-judge prompt, not a network trained on human preference data.

If you want to go further later: the natural next step is collecting real human preference pairs (from real users comparing two outfits) and training an actual small reward-prediction model on them — at that point you'd be doing the real thing, just with real data you don't have yet at project start.

## 8. Quick glossary

| Term | Plain-language meaning |
|---|---|
| Dataset | Examples used to test or improve the system |
| Rule engine | Hand-written, deterministic pass/fail checks |
| Agent | The part of the system that proposes an action (here: an outfit) |
| Reward model / evaluator | The part that grades how good a proposal was |
| Reward | A high score for a good, rule-following proposal |
| Penalty | A low/negative score for a rule-breaking or poor proposal |
| Training loop | Repeatedly proposing → grading → adjusting weights based on the grade |
| RLHF | Using human judgments to shape/calibrate the reward signal |
| RLAIF | Same idea, but an AI model plays the role of the human judge |
| Reward hacking | When the agent learns to please the reviewer instead of actually being good — why human spot-checks matter |

---

## Template for new entries (agent: copy this per block)

```
## [Block letter] — [Concept name]

**What we built:** one or two sentences, concrete, no jargon.

**Why it exists:** what problem it solves in plain terms.

**Analogy:** a simple real-world comparison.

**Where to look in the code:** file/function name.
```

---

## Block A — Seed Catalog & Synthetic Episodes (Dataset Foundation)

**What we built:** A curated static catalog of 35+ fashion products in INR (₹) tagged with categories, colors, occasions, and seasons, paired with synthetic test episodes representing diverse user preferences and constraints.

**Why it exists:** AI recommendations and rule evaluations need structured data to match against. In an MVP sprint without external database latency or scraping overhead, this provides a reliable, reproducible foundation.

**Analogy:** The wardrobe rack and lookbook in a personal stylist's studio that they pick items from before serving a client.

**Where to look in the code:** `data/processed/products.json`, `data/processed/trends.json`, `backend/app/models/`.

---

## Block B — Deterministic Rule Engine (The Unbreakable Floor)

**What we built:** A pure logic validator that verifies hard constraints: total price ≤ budget, complete look (top + bottom + shoes), occasion/climate compatibility, and zero duplicate item roles.

**Why it exists:** AI recommendation models can make creative mistakes (e.g. recommending two pairs of shoes or exceeding the user's budget). The rule engine acts as an unyielding filter that rejects invalid outfits before scoring.

**Analogy:** A bouncer at a venue door checking tickets and dress codes before letting anyone into the party.

**Where to look in the code:** `backend/app/services/rule_engine.py` (`check_outfit`).

---

## Block C — StyleDNA & Multi-Candidate Generator (The Baseline Agent)

**What we built:** A taste-profiling engine that converts user preferences into normalized tag weights and an agent that explores the catalog to assemble 10–15 candidate outfits matching the request.

**Why it exists:** A single search query often yields too few or too repetitive looks. Generating multiple diverse candidate bundles gives the ranking and evaluation layers enough variety to select top looks.

**Analogy:** A personal shopper pulling 10 different combinations off the racks into a fitting room before presenting the best 3.

**Where to look in the code:** `backend/app/services/styledna.py`, `backend/app/services/recommendation.py` (`generate_candidates`).

---

## Block D — Evaluator & Multi-Attribute Reward Scorer (The Grader)

**What we built:** A scoring function that blends StyleDNA tag overlap, seasonal trend weights, color harmony, and a +0.5 wardrobe-reuse bonus (with ₹0 cost for owned items), penalizing rule violations down to zero.

**Why it exists:** To rank candidate outfits objectively, we need a composite reward signal that balances personal aesthetic taste with budget savings and current fashion trends.

**Analogy:** A fashion magazine editor scoring runway looks on a rubric of fit, color palette, trendiness, and practical value.

**Where to look in the code:** `backend/app/services/recommendation.py` (`score_outfit`), `backend/app/services/analyzers.py`.

---

## Block E — Dynamic Feedback & Weight Nudge Loop (Continuous Learning)

**What we built:** An interactive feedback mechanism where liking, saving, or opening an outfit increases the weights of its tags by +0.1, and dismissing an outfit decreases them by -0.1 (bounded at 0.0).

**Why it exists:** User taste evolves with interaction. Instead of keeping static profiles, this lightweight reinforcement loop continuously refines the user's StyleDNA with zero training cost.

**Analogy:** A Spotify or TikTok recommendation algorithm learning your taste each time you like or skip a song.

**Where to look in the code:** `backend/app/services/styledna.py` (`update_style_dna_interaction`), `backend/app/services/train_loop.py`.

---

## Block F — AI Lab & Human-in-the-Loop Inspector (Reviewer Calibration)

**What we built:** An interactive dashboard tab that exposes live rule verification passes/failures, reward component breakdowns, and a simulated offline training curve.

**Why it exists:** To prevent "black-box" confusion during demos, this allows judges and engineers to inspect why specific outfits were accepted, scored, or penalized.

**Analogy:** Opening the hood of a car to inspect the engine gauges, timing belts, and fuel mixture in real-time.

**Where to look in the code:** `backend/app/services/train_loop.py`, `frontend/src/pages/AILabPage.jsx`.

---

## Block G — Full Product Integration & Explainability (The Complete Experience)

**What we built:** Transparent recommendation cards with dynamic explanations citing top matched tags, budget compliance, wardrobe reuse savings, and direct demo marketplace links.

**Why it exists:** Users don't trust unexplained recommendations. Giving clear reasons ("Recommended because it matches your minimal aesthetic, stays within ₹4,000, and reuses your owned white t-shirt") builds confidence.

**Analogy:** A sommelier explaining why a specific wine was paired with your dinner based on your palate and the ingredients.

**Where to look in the code:** `backend/app/services/recommendation.py` (`generate_explanation`), `frontend/src/components/OutfitCard.jsx`.

