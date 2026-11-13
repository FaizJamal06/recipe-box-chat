# Evaluation report

Mode: **replay (LLM cache only)** · 2026-11-13 23:11 · commit `c05f9ed` · DB fingerprint `{"comma_splits": 4006, "garlic_family_recipes": 32826, "ingredient_lines": 1347635, "onion_family_recipes": 31304, "rare_remapped": 37499, "recipe_tags": 484224, "unverified_alcohol": 39212, "unverified_dairy": 35112, "unverified_egg": 38620, "unverified_fish": 39931, "unverified_gelatin": 40370, "unverified_gluten": 35480, "unverified_honey": 40444, "unverified_meat": 36725, "unverified_peanut": 40710, "unverified_pork": 39272, "unverified_poultry": 39553, "unverified_root_veg": 37207, "unverified_sesame": 40696, "unverified_shellfish": 40187, "unverified_soy": 39303, "unverified_tree_nut": 40089, "vocab_sha1": "81ac30178734", "vocab_size": 20206}`

**35 / 35 cases pass** (66 turns). Every check is programmatic (eval/cases.yaml, eval/run.py): results are re-checked with independent SQL, stats against eval/oracle.py's pure-Python recount.

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
| A0.1 'Actually I'm not vegan anymore, just no peanuts': vegan removed, peanuts the only restriction, dish kept | ✅ pass |  |
| A0.1 removal phrasings: 'I can eat dairy now', 'I'm no longer vegetarian' | ✅ pass |  |
| A0.1 a message nothing can parse: one short question with chips, the dish is not overwritten | ✅ pass |  |
| A0.2 'make it vegetarian' after a chicken biryani search: a filter (chicken dropped, and said), not a search word | ✅ pass |  |
| A0.2 'veg biryani': veg = the vegetarian filter, the search is 'biryani' | ✅ pass |  |
| A0.2 zero results: the search words are relaxed (and named), the restriction never is | ✅ pass |  |
| A0.3 a new dish clears request filters (step limit) and keeps person restrictions; a chip restores them | ✅ pass |  |
| A0.3 a have-list doesn't leak into the next dish search | ✅ pass |  |
| A0.4 a seasoning gets an 'omit it' option graded by same-dish recipes without it; line removed, steps adjusted | ✅ pass |  |
| A0.5 the kept-restrictions note names presets ('vegan, no peanuts'), not their tags | ✅ pass |  |
| The 'No step limit?' chip ('remove the step limit') clears the limit; it isn't a substitution | ✅ pass |  |

## Latency and LLM calls

Server-side wall time per turn (TestClient, same process), measured after the startup warm-up.

| run | all turns p50 / p90 | substitution turns p50 / p90 | LLM calls per turn (mean / max) | LLM errors |
|---|---|---|---|---|
| this run (replay) | 170 / 894 ms (n=66) | 402 / 884 ms (n=8) | 0.44 / 1 | 0 |
| last live run, 2026-11-13 22:37 | 541 / 3,724 ms (n=66) | 2,250 / 2,896 ms (n=8) | 1.27 / 3 | 22 |

In a replay every LLM answer comes from the cache (0 ms), so replay latency is the engine alone.

Slowest turns this run: demo5_match #1 3,400 ms (rule parser · high-confidence pattern); a03_match_to_search #1 3,051 ms (rule parser · high-confidence pattern); quantity_sufficiency #1 2,546 ms (rule parser · high-confidence pattern); demo5_match #2 2,166 ms (rule parser · high-confidence pattern); demo3_rank #1 1,067 ms (LLM · gemini-3.5-flash-lite)

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

**What the pass rate does and doesn't show.** 35 cases, 66 turns, all assertions programmatic (checks in
`eval/checks.py`). Result ids are re-checked with independent SQL (`recipe_tags`, `ingredient_lines`, `unverified`),
demo 2/3 numbers are compared with eval/oracle.py's pure-Python recount, and substitution citations are re-checked
recipe by recipe. What it doesn't cover: ranking *quality* (only constraints and ids), and the wording of replies
beyond a few required phrases.

**M6 part 2: the 11 new cases came from live testing** (A0.1–A0.5 and the step-limit chip). All 11 failed before the
fixes and pass now, in replay and in the one live run:
- "Actually I'm not vegan anymore, just no peanuts" kept vegan and searched for the dish "actually not anymore".
- "make it vegetarian" after a chicken biryani search asked "which recipe?"; the LLM path searched "vegetarian biryani".
- A new dish kept the old step limit and have-list; the kept-restrictions note listed eight tags instead of "vegan".
- "remove the salt" had no answer: salt has no curated substitute. Now "omit it" is an option (8 of 18 broiled
  chicken recipes have no salt).
- The "No step limit?" suggestion chip sent "remove the step limit", which the substitution parser took as an edit.

**The live run (one, to save quota) hit the free tier's limits:** 22 LLM errors in 66 turns, mostly 429 quota
exhaustion near the end of the run, plus 503s and one voice reply withheld by the validator ("number word nine not
in facts"). Every failed call fell back to the rule parser or the templated reply, and all 35 cases still passed.

**A finding from the live run, fixed after it:** one turn made 3 LLM requests (planner, then a voice call that hit a
503 and retried on the fallback model). The PRD allows 2. The cap is now enforced in one place (`llm.turn()` /
`MAX_PER_TURN`), counting retries, fallbacks and cache hits, with a regression test. The live row below predates this
fix and the plain-English "chosen because" wording; the replay re-runs every case on the final code with the live
run's cached answers (a cache miss behaves like an outage, so some turns replay through the rule parser).

**With the LLM off entirely** (`GEMINI_API_KEY=` empty, rule parser for every turn, no voice) all 35 cases pass too:
all turns p50 146 / p90 593 ms.

**Latency.** Replay latency is the engine alone (cache hits cost 0 ms). Live substitution turns: p50 2.3 s / p90 2.9 s;
all turns p50 0.5 s / p90 3.7 s, down from 3.9 s / 15.4 s in the M6 part 1 run (the recipe_tags index fix landed
after that run).

**Baseline fairness.** The raw model gets the dataset's sources, size and id format in its prompt (so the record
count in question 1 is given away; the question checks the *valid* count). It is asked for JSON with every number and
id it states. It has no tools, which is the point of the comparison.
