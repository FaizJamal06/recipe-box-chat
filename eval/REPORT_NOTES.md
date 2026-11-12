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
