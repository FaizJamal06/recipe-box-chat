# Key decisions

Each with the reason in 2–3 lines. D1–D8 are from the PRD (§9); the rest were made while building.

## Data and storage

**D1. SQLite + FTS5, not a vector DB.** The task is graded on exact filtering and aggregation over the full set. SQL
gives reproducible counts with the query shown, and it needs no infrastructure: one file, built inside the Docker image.

**D2. The LLM plans; it never answers.** Gemini turns a message into a JSON plan with fixed enums; typed executors
(search, match, stats, substitute) compute every fact. No LLM-written SQL: typed ops are safer and testable.

**D3. No embeddings in the shipped version.** Top-k similarity can't answer "how many" or "all recipes without
dairy", and embeddings handle negation badly. BM25 covers the required queries; vectors stay an optional M7 retriever.

**D4. Identity vs contains-tags.** Matching needs "is this line garlic?" (canonical + family); allergen safety needs
"could this line contain dairy?" (tags with levels). One notion can't serve both precisely.

**D5. Parse once at ingest.** Every ingredient line is parsed into quantity, unit, canonical, family and tags when the
DB is built. Runtime never re-parses, so answers are fast and reproducible (the build fingerprint proves it).

**D6. Strict and broad counts, side by side.** "Contains garlic" is ambiguous (garlic powder?). Instead of choosing, every
count reports both, with the definition in the Calculation tab. The oracle recomputes both in pure Python.

## Safety

**D7. Unknown is not safe.** A recipe passes "no dairy" silently only if every line is verified. Unverified recipes are
shown after the verified ones with ⚠ naming the line, or excluded in strict mode. ~30% carry a ⚠: the price of not guessing.

**D8. may_contain for label-dependent products.** Chocolate, margarine, cake mix and wonton wrappers vary by brand, so
they warn instead of passing or failing. Strict mode excludes them.

**D9. Never silently relax a hard constraint.** Zero matches gives "no recipe satisfies…" plus flagged alternatives
that each name the constraint they break. Search relaxation (M6) changes only the search words, and says which.

**D10. The LLM audits the lexicon offline, never decides at runtime.** Gemini compared 3,000 canonicals and 150
recipes with the rules; I fixed real misses and kept the rule where the LLM was wrong (whiskey is gluten-free).

## Conversation

**D11. Rule parser first, LLM second.** High-confidence patterns (a have-list, "the second one", "also no garlic")
skip the LLM: faster, free, deterministic. Any LLM failure falls back to the same parser, and the UI marks it.

**D12. Person vs request constraints.** Allergies, presets and strict mode are about the person and persist. Dish,
step limit, have-list and must-include are about one request: a new dish or task clears them, says so, and offers a
"Restore previous filters" chip.

**D13. Ask instead of guess.** A contradiction ("vegan chicken curry") or an unparseable message while the LLM is down
gets one short question with chips. Leftover words become a dish only if they name a food.

**D14. Templates for facts; the LLM only rewords.** The voice reply may only use numbers and ids from the computed
facts (validated); otherwise the template is shown alone. The exact numbers stay one click away.

**D15. At most 2 LLM calls per turn, 6 s each.** A slow free-tier answer is worse than the rule parser. The step
rewrite for substitutions gets 12 s, because the user asked for it and a deterministic fallback exists.

## Matching and substitution

**D16. A weighted, displayed score.** `2·matched − 1·extra − 0.1·steps − 0.5·short` beats a lexicographic sort,
which lets a 4-match/15-extra recipe beat a 3-match/2-extra one. The breakdown is shown in developer view.

**D17. Evidence tiers for substitution.** L1 (same dish phrase), L2 (similar ingredient sets), L3 (same context): "what do
recipes *without* X use instead?" Raw rates, no smoothing; lift only when there is enough data to compute it.

**D18. Strong needs real support.** ≥ 3 supporting L1 recipes (or an explicit "eggless …" variant + 2), and never for
a staple. Weak evidence still adapts, but the result is labelled "Weak evidence: based on n recipes".

**D19. Widen, don't give up.** If the specific phrase ("tomato cream sauce") has no Strong or Moderate candidate, L1
widens step by step ("cream sauce" → "pasta"), and the reply says which phrase it used.

**D20. "Omit it" is a candidate for optional items.** For salt, pepper, garnishes, herbs and nuts on top, leaving it
out is often the best answer. It is graded by how many same-dish recipes go without it, like any other candidate.

**D21. A final safety gate on the adapted recipe.** The adapted ingredient list is re-checked against every
restriction. If a line still fails (Parmesan in a "dairy-free" pasta), the result says "not safe", never dairy-free.

## Presentation and delivery

**D22. Clean by default, internals one click away.** Developer view (off by default) shows SQL, planner and timings,
the trace and raw filters. The normal view speaks plain English; the Calculation tab still explains every number.

**D23. Docker builds the DB.** The image downloads the data and builds `recipes.db` in a builder stage; only the DB and
code ship. Railway's free tier (0.5 GB RAM) fits: peak RSS 331 MB at build, runtime reads through SQLite.

**D24. A programmatic eval.** Every case asserts on the API JSON, re-checked with independent SQL and the pure-Python
oracle; nothing is judged by eye or by an LLM. A replay mode uses only cached LLM answers, so it costs no quota.
