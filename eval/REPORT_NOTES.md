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
