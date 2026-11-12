# Evaluation report

Mode: **replay (LLM cache only)** · 2026-11-13 02:03 · commit `f0fe8d8` · DB fingerprint `{"comma_splits": 4006, "garlic_family_recipes": 32826, "ingredient_lines": 1347635, "onion_family_recipes": 31304, "rare_remapped": 37499, "recipe_tags": 484224, "unverified_alcohol": 39212, "unverified_dairy": 35112, "unverified_egg": 38620, "unverified_fish": 39931, "unverified_gelatin": 40370, "unverified_gluten": 35480, "unverified_honey": 40444, "unverified_meat": 36725, "unverified_peanut": 40710, "unverified_pork": 39272, "unverified_poultry": 39553, "unverified_root_veg": 37207, "unverified_sesame": 40696, "unverified_shellfish": 40187, "unverified_soy": 39303, "unverified_tree_nut": 40089, "vocab_sha1": "81ac30178734", "vocab_size": 20206}`

**24 / 24 cases pass** (40 turns). Every check is programmatic (eval/cases.yaml, eval/run.py): results are re-checked with independent SQL, stats against eval/oracle.py's pure-Python recount.

| case | result | what failed |
|---|---|---|
| Demo 1: penne, then no dairy, the second one's steps, no garlic | ✅ pass |  |
| Demo 2: garlic and onion count + percentage equals the oracle | ✅ pass |  |
| Demo 3: five tomato recipes with the fewest steps equal the oracle | ✅ pass |  |
| Demo 4a: calories are refused (no nutrition field) | ✅ pass |  |
| Demo 4b: desserts are a labelled title-keyword proxy | ✅ pass |  |
| Demo 5: pantry match, no peanuts, at most 6 steps, then exclude eggs | ✅ pass |  |
| Quantities: 2 eggs and 1 cup rice are checked against the recipe's amounts | ✅ pass |  |
| Demo 6: saffron + marshmallows, no sugar, at most 2 steps: marshmallow dropped (it is sugar), results obey both | ✅ pass |  |
| No-match: the same at most 1 step: explicit no-match, alternatives flagged by the constraint they break | ✅ pass |  |
| Demo 7: banana bread without eggs, dataset only, Strong evidence, cited ids re-checked | ✅ pass |  |
| Demo 8: cream without dairy, then a tree-nut allergy re-grades (cashew drops out) | ✅ pass |  |
| Demo 9: meringue egg whites: Weak or None, and it asks before adapting | ✅ pass |  |
| Gate: the adapted pasta still has Parmesan, so it is not called dairy-free | ✅ pass |  |
| Removing a restriction: 'dairy is fine now' drops the dairy filter | ✅ pass |  |
| Reference resolution: 'the second one' opens result #2 | ✅ pass |  |
| Typos: 'frist' still means the first result | ✅ pass |  |
| Strict mode: no result even may contain dairy or has an unverified ingredient | ✅ pass |  |
| Unknown is not safe: fully verified results come before unverified ones | ✅ pass |  |
| dataset_only: every proposed substitute is a dataset ingredient | ✅ pass |  |
| Cook time is refused (no time field) | ✅ pass |  |
| A wheat allergy excludes gluten (stricter than needed, and said so) | ✅ pass |  |
| Vegan preset: no meat, fish, shellfish, dairy, egg, honey or gelatin in results | ✅ pass |  |
| Cuisine: no cuisine field, so a labelled title-keyword proxy | ✅ pass |  |
| At most 2 LLM calls per turn, even on a long conversation | ✅ pass |  |

## Latency and LLM calls

Server-side wall time per turn (TestClient, same process), measured after the startup warm-up.

| run | all turns p50 / p90 | substitution turns p50 / p90 | LLM calls per turn (mean / max) | LLM errors |
|---|---|---|---|---|
| this run (replay) | 194 / 877 ms (n=40) | 297 / 663 ms (n=7) | 0.85 / 2 | 0 |
| last live run, 2026-11-13 01:48 | 3,926 / 15,378 ms (n=40) | 2,870 / 6,678 ms (n=7) | 1.23 / 2 | 18 |

In a replay every LLM answer comes from the cache (0 ms), so replay latency is the engine alone.

Slowest turns this run: demo5_match #1 3,285 ms (rule parser · high-confidence pattern); quantity_sufficiency #1 2,404 ms (rule parser · high-confidence pattern); demo5_match #2 1,769 ms (rule parser · high-confidence pattern); demo6_no_match #1 889 ms (rule parser · high-confidence pattern); demo3_rank #1 767 ms (LLM · gemini-3.5-flash-lite)

## Baseline: the same questions to raw Gemini, no tools

2 of 6 answers cite recipe ids that don't exist in the dataset; 3 answers state counts or rankings that don't match the oracle. Recipe Box answers every one from the DB (ids re-checked, counts equal to the oracle).

| question | raw LLM said | checked against the DB / oracle | Recipe Box |
|---|---|---|---|
| How many recipes are in the dataset, and how many of them are valid (h | The dataset contains a total of 125,164 recipe records. | oracle: 125,164 records, 122,933 valid; no number matches the valid count | 125,164 records, 122,933 valid |
| How many recipes contain both garlic and onion? What percentage of the | There are 45,210 recipes in the dataset that contain both garlic and onion, which represents approximately 36.1% of the total dataset. | oracle: strict 16,065, broad 23,068; no number matches | strict 16,065 = 13.07%; broad 23,068 = 18.76% |
| Among recipes containing tomato, which five have the fewest instructio | Dataset is not directly queryable in this environment to return specific recipe IDs for tomato recipes with the fewest instruction steps. | no recipe id given; 0 of 5 match the oracle's ids | 5 ids, all in the DB: `fn:Cv.LzyOIGtSJN3dvLIBqPQo8ac.K97G`, `ar:mkK6Tvis28vdP.VVri6zUKoiSXP.2bW`, `fn:qghRY30sgJjcP5lpqMZ95qozeMkSFuW` … |
| Find a penne pasta recipe without dairy. Give its recipe id. | A dairy-free penne pasta recipe can be found with the ID epi:241470. ids: epi:241470 | 1 of 1 ids don't exist in the dataset | 10 ids, all in the DB: `ar:23to8XzUux0FF.g5ZFsqnxvhByMzfJ.`, `fn:ck/foCIv1g.W0SyPMLF5DWS/ZdeQBRi`, `ar:zwRAInNlhnKD1jMf/HOm5a9oKhjC8Om` … |
| Which recipes in the dataset are egg-free banana breads that use apple | I do not have access to the full dataset contents to query specific recipe formulations like egg-free banana breads using applesauce. | no recipe id given | 1 ids, all in the DB: `ar:.GLWQH0bkiU3fRzwc68PqTCqGHJj2fy` |
| I have eggs, onions, tomatoes, and rice. Suggest five recipes using as | I cannot provide specific recipe suggestions from the dataset as I do not have direct access to run a search query, but here is a placeholder response indicatin | 5 of 5 ids don't exist in the dataset | 5 ids, all in the DB: `ar:YrORiIjDlCOz7InEOviK5wKjubaNccC`, `fn:acDMAvfOXqTStpzy3eogF301HowU3im`, `ar:QyVarQzRar/zTLW7ExZpc6qbYC1xQF6` … |

## Notes (hand-written)

**What the pass rate does and doesn't show.** 24 cases, 40 turns, all assertions programmatic. Result ids are
re-checked with independent SQL (`recipe_tags`, `ingredient_lines`, `unverified`), demo 2/3 numbers are compared with
eval/oracle.py's pure-Python recount, and substitution citations are re-checked recipe by recipe. What it doesn't
cover: ranking *quality* (only constraints and ids), and the wording of replies beyond a few required phrases.

**Failures found while building the eval, and fixed** (all have regression tests):
- "Which recipes … use applesauce instead of eggs?" was parsed as a *substitution* by a high-confidence rule, so even
  the live LLM was skipped. A question asking for recipes is now never a substitution.
- "show me the frist one" only worked through the LLM; common ordinal typos are now rule-level.
- Demo 6: marshmallows passed "no sugar". The `sugar` family's broad list now includes marshmallows, caramel and
  candy (query time, no rebuild), so marshmallow is dropped from the pantry with the reason shown.
- The oracle values file was being overwritten by the test suite (a test calls `oracle.check()` on a fixture); only
  the CLI run writes it now.

**Demo 6 deviates from the PRD wording, on purpose.** The PRD expects an explicit no-match for "saffron and
marshmallows, no sugar, at most 2 steps". With marshmallows correctly dropped (they are sugar), the dataset has 35
saffron recipes with ≤ 2 steps and no sugar, so a no-match would be false. The case asserts the honest behaviour
(marshmallow dropped, every result ≤ 2 steps and sugar-free, broad), and a second case ("at most 1 step") asserts the
explicit no-match with alternatives flagged by the constraint they break.

**A slowdown the replay caught, after the live run.** The M6 rebuild ends with `ANALYZE`. With those statistics, the per-result evidence query (`recipe_tags` joined by recipe_id, which had only a `tag` index) became a ~30k-row scan per result: 'I cannot have dairy' took 11.6 s and 'Find a vegan curry recipe' (7 tags) 55 s. Fixed with an index on `recipe_tags(recipe_id, tag)` (in ingest.py, and created in place on the current DB: 0.9 s, no rebuild): the same turns now take 0.24 s. A test pins the query plan. **The live latency row predates this fix**; its slow search turns are part of its p90. The replay row is the current engine.

**Latency.** The live run hit a bad Gemini hour: 18 LLM errors in 40 turns (503 overloaded, timeouts). Each failed
call costs its full timeout before the rule fallback answers; with the search slowdown above, that pushes the
all-turn p90 to ~15 s. The
fallback model (gemini-3.5-flash) was tried where the budget allowed and was overloaded too. Substitution turns:
p50 2.9 s / p90 6.7 s live; the engine part alone is 0.3–0.7 s after the startup warm-up (the step rewrite has a
deliberate 12 s cap). Replay latency = engine only.

**The live run is from before three fixes** (the recipe_tags index, the question-vs-substitution guard, filler words
in the keyword fallback). The replay re-runs every case on the current code; the LLM answers it replays are the
live run's, from the cache.

**Baseline fairness.** The raw model gets the dataset's sources, size and id format in its prompt (so the record
count in question 1 is given away; the question checks the *valid* count). It is asked for JSON with every number and
id it states. It has no tools, which is the point of the comparison.
