# Interview notes

Talking points per milestone, then the likely live-coding requests with the exact place to change. Numbers are from
the current build (fingerprint `vocab_sha1 81ac30178734`).

## M0: data profile and deploy de-risk

1. Three sources: AllRecipes 39,802, Epicurious 25,323, Food Network 60,039 = 125,164 records; ids are source-prefixed.
2. I profiled before designing (`scripts/profile_data.py` → `docs/DATA_PROFILE.md`), never by opening the raw JSON.
3. "ADVERTISEMENT" sits in 400,811 AllRecipes lines, often glued to the end of a real line, so it is stripped first.
4. Food Network has 1,629 records with no ingredients and 52 with no title: that is most of the invalid records.
5. Valid = title + ≥ 1 real ingredient line + instructions → 122,933. Every count is out of valid recipes.
6. Steps differ by source: AllRecipes uses newlines, some Food Network recipes are one paragraph (counted as sentences).
7. Deploy first: a Dockerfile that downloads the zip plus `/api/health` on Railway, before any feature.
8. The free host has 0.5 GB RAM, which ruled out loading everything into memory or embedding 125k recipes.
9. `scripts/peek.py` prints truncated samples, so nobody (me or the agent) reads the 200 MB files.
10. The profile changed the PRD: the valid-record rule and the step rule were confirmed or amended from real data.

## M1: normalization and the DB build

1. `normalize.py` parses each line into quantity, unit, name, then a canonical (`2 cloves garlic, minced` → `garlic`).
2. Families group forms (`garlic`, `minced garlic`, `garlic clove`); a `broad` list adds processed forms (powder, salt).
3. Tags with levels: contains / may_contain / alt (only in an "or" option). Lexicons in `backend/app/lexicon/*.yaml`.
4. `except` lists stop false positives: "cream of tartar" is not dairy, "peanut butter" is not dairy.
5. Rare names (< 5 recipes) are remapped by a suffix fallback, but never count as verified for safety.
6. The build is one pass per source with batched inserts: ~6.5 min, peak RSS 331 MB, prints both.
7. A determinism check builds twice with different hash seeds and compares fingerprints.
8. A 30-recipe fixture (`backend/tests/fixtures/mini.json`) holds every tricky case: ads, headers, "or" lines, paragraphs.
9. Covering indexes + `recipe_canon` / `recipe_size` tables make substitution evidence fast and exact.
10. `ANALYZE` at the end once made a query slow (wrong plan): an index on `recipe_tags(recipe_id, tag)` fixed it, pinned by a test.

## M2: search, stats, rule parser, CLI

1. Search = FTS5 BM25 (title × 3) for ranking; every restriction is a SQL filter on the full set, never a post-filter.
2. Excluded ingredients use the broad definition plus a text-mention net ("no garlic" also drops garlic powder).
3. Stats are typed ops (count, percentage, rank, mean, median, top ingredients), not LLM-written SQL.
4. Every count is reported strict and broad, with the SQL and denominator (Calculation tab).
5. `eval/oracle.py` recomputes demo 2 (garlic + onion: 16,065 / 23,068) and demo 3 in pure Python from the raw JSON.
6. Ties are explicit: steps, then ingredients, then id, so rankings are reproducible.
7. The rule parser (`rules.py`) covers the demo phrasings without the LLM; the same plan shape as the LLM.
8. The CLI and the API share `Session.respond`, so what I test in the terminal is what the UI runs.
9. The dataset header (valid / total / invalid reasons) is read from the DB at startup, never hardcoded.
10. A spelling fix runs only when a query finds nothing ("chiken" → "chicken"), and the reply says so.

## M3: LLM planner, session state, matching, guard

1. Gemini returns a JSON plan validated against enums; invalid twice or slow (> 6 s) → the rule parser, flagged.
2. Responses are cached by (model, system, prompt, schema), so eval replays cost no quota.
3. Sticky state: restrictions persist across turns; "dairy is fine now" removes one; "the second one" resolves from shown results.
4. Presets (vegan, Jain, halal, nut allergy, …) are tag compositions in `lexicon/diets.yaml`, stated once in the reply.
5. Matching (T2) scores `2·matched − 1·extra − 0.1·steps − 0.5·short`; preferences change one weight.
6. Pantry staples (salt, pepper, water) are assumed and stated; "no staples" turns them off.
7. Quantities compare only within a unit family (volume or mass), never volume ↔ mass.
8. No match → "No recipe satisfies all hard constraints" + alternatives, each breaking one named constraint.
9. The guard answers unsupported fields (nutrition, cook time, servings, ratings) without the LLM.
10. Cuisine and category have no field: a labelled title-keyword proxy, with an honest count even when it is zero.

## M4: API and UI

1. FastAPI: chat, recipe by id, state PATCH (chip removal re-runs the task), reset, health; in-memory sessions.
2. Post-check: every recipe id in a reply must exist in the payload, otherwise it is stripped and logged.
3. The panel: Results (cards), Calculation (method, denominator, SQL), Evidence (per-recipe proof lines), Trace.
4. Constraint chips show the state; removing one PATCHes the session and re-runs the search.
5. Voice: a second LLM call rewords the answer; every number and id must be in the facts, or the template shows alone.
6. Unknown is not safe in the UI: unverified recipes sit after verified ones behind one ⚠ line, strict mode hides them.
7. The recipe drawer shows the original lines and steps, the parsed view and the tags.
8. `?q=...&q=...` replays a conversation on load: demos and screenshots use it.
9. The Docker image builds the UI in a node stage and the DB in a builder stage; the runtime image has neither raw data nor node.
10. One worker, one lock around the shared read-only SQLite connection (a `ponytail:` shortcut).

## M5: substitution

1. Pipeline: affected lines → role in this dish context → candidates → safety check → evidence → choice → adaptation.
2. Candidates: curated (`lexicon/candidates.yaml`), "use more" of an ingredient already there, your pick, data-discovered.
3. Evidence tiers: L1 (most specific title phrase with ≥ 10 recipes, ≥ 3 without the item), L2 (Jaccard ≥ 0.35), L3 (context).
4. Raw rates, no smoothing: add-one smoothing had turned 3/1411 vs 0/181 into a misleading lift.
5. Strong requires ≥ 3 L1 supporting recipes (or an explicit variant + 2), never a staple; Moderate ≥ 3 in L2; Weak = any.
6. Widening: no Strong/Moderate in "tomato cream sauce" → "cream sauce" → "pasta", and the reply says so (demo 8).
7. Ranking: never a conflicting candidate over a clean one, then strength, role coverage, support, lift.
8. The adapted recipe: deterministic ingredient diff, LLM step rewrite validated (no removed item, no new ingredient), fallback swap.
9. A final gate re-checks the adapted list: Parmesan left in a "dairy-free" pasta → "not safe", with a fix chip.
10. Defining ingredients (egg whites in a meringue) ask before adapting; Weak evidence adapts with a label.

## M6: speed, eval, live-testing fixes, polish

1. Eval: 35 cases, 66 turns, programmatic assertions (`eval/cases.yaml`, checks in `eval/checks.py`), replay and live.
2. Baseline: raw Gemini invented recipe ids (`epi:241470`; 5 of 5 for the pantry question) and said 45,210 garlic+onion recipes (true: 16,065).
3. Speed: covering indexes, `recipe_canon`, a startup warm-up of demos 7–9: substitution turns 0.3–0.7 s on the engine.
4. "Not vegan anymore, just no peanuts": removal phrasing drops presets; "just no X" replaces all restrictions.
5. Leftover words become a dish only if they name a food (vocab word or ≥ 10 titles); else the previous dish stays.
6. Diet words inside a dish ("vegetarian biryani", "veg", "eggless") become filters; "make it vegetarian" drops "chicken" and says so.
7. Zero results relax only the search words (synonyms, modifiers, head dish), and the reply names what was relaxed.
8. Person vs request constraints: a new dish clears the step limit and have-list, with a "Restore previous filters" chip.
9. "Omit it" for seasonings and optional items: "8 of 18 broiled chicken recipes have no salt", line removed, steps adjusted.
10. Developer view: the normal UI speaks plain English; SQL, planner, timings and the trace are one toggle away.

## Likely live-coding requests

| Request | Where | Notes |
|---|---|---|
| Change the match weights | `backend/app/match.py`: `WEIGHTS`, `PREF_WEIGHTS` | Shown in the Calculation tab automatically (`web.view` reads `res.weights`). |
| Add an allergen tag | `backend/app/lexicon/tags.yaml` (contains / may_contain / except), `planner.py` `TAGS`, `rules.py` `TAG_WORDS` | Tags are computed at ingest: rebuild the DB (`python -m backend.app.ingest`). Add a case to `tests/test_normalize.py`. |
| Add a diet preset | `backend/app/lexicon/diets.yaml` (`say`, `after_no`, `tags`, `note`) | No rebuild. The LLM schema enum includes presets, so cached planner answers miss once. |
| Change the step rule | `backend/app/ingest.py`: `steps()` and `count_sentences()` | Rebuild; `eval/oracle.py` recomputes steps independently and must agree. |
| Add a stats op | `backend/app/stats.py` (`execute` + a new function), `planner.py` `OPS`, a regex in `rules.rule_plan`, the reply in `web._stats` | Add an oracle check if it is a demo number. |
| Change strength thresholds | `backend/app/evidence.py`: `strength()`, `MIN_L1`, `MIN_WITHOUT` | Update `subview.METHOD` (the text the Calculation tab shows). |
| Add a candidate substitute | `backend/app/lexicon/candidates.yaml`: item → role → candidates; `estimate`, `prep`, `declared` | It must still pass `safety.verify_canonical` and earn its strength from the data. |
| Change the omit rule | `backend/app/omit.py`: `grade()` thresholds; `optional` list in `lexicon/roles.yaml`; `_SAYS` phrases | `subview.because` and `adapt.verified_lines` word the result. |
| Change the LLM model or timeouts | `.env` `GEMINI_MODEL` / `GEMINI_FALLBACK_MODEL`; `llm.py` `TIMEOUT_MS` (6 s), `voice.py` `TIMEOUT_MS` (4 s), `substitute.py` `ADAPT_MS` (12 s) | A new model misses the cache once (the key includes the model). |
| The developer-view toggle | `frontend/src/App.tsx` `useDevView`; `ChatPane.tsx` (`PlannerBadge`, `FallbackDot`, `Trace`, dev lines); `EvidencePanel.tsx` (`CalcBlock`, Trace tab); backend `payload.dev_md` in `web.view` | localStorage access is wrapped in try/catch; `?dev=1` forces it on. |
| Make a restriction phrase work without the LLM | `backend/app/rules.py`: `_EXCL`, `_REMOVAL`, `_ONLY`, `dish_filters` | Then a test in `tests/test_live_fixes.py` and an eval case. |
| Request vs person constraints | `backend/app/apply.py`: `REQUEST`, `_switch`, `restore` | `state.restrictions()` names presets for every note. |
