# Overnight report: M6 part 1 (2026-11-13)

Done: the lexicon fixes, the speed work, one rebuild, the eval suite with a live run, the raw-LLM baseline. Nothing is
pushed. The README is untouched (part 2).

## Results

| | |
|---|---|
| Tests | **231 passed** (`python -m pytest -q`, from `backend/`), up from 190 |
| Oracle (full data, LLM off) | **9 / 9 PASS**, after the rebuild and again after the last lexicon change |
| Eval | **24 / 24 cases pass**: live once (01:48) and in replay (24 cases, 40 turns) |
| Baseline (raw Gemini, no tools, same questions) | 2 / 6 answers cite recipe ids that don't exist (`epi:241470`; 5 of 5 invented for the pantry question); 3 / 6 give counts or rankings that don't match the oracle (it says 45,210 garlic+onion recipes, 36.1%; the oracle says 16,065 strict / 23,068 broad); twice it declined to give ids. Recipe Box: every number equals the oracle, every id exists. Table in eval/REPORT.md |
| Rebuild | 125,164 records, 122,933 valid, 382 s, **peak RSS 331 MB**, DB **971 MB** from the build, **995 MB** after the in-place recipe_tags index (was 737 MB: covering indexes + recipe_canon) |
| Fingerprint | vocab_sha1 `81ac30178734`, vocab 20,206, ingredient_lines 1,347,635, recipe_tags 484,224, comma splits 4,006, rare remapped 37,499, garlic-family recipes 32,826, onion-family 31,304 |

### Latency, before and after

| | before (M5, 2026-11-12) | after (now) |
|---|---|---|
| Substitution turn, engine only (API, LLM off) | 4.4–9 s on the first turn for a recipe, 0.25–4.8 s warm | **0.27–0.69 s** for 11 different substitution turns after the startup warm-up, including recipes the warm-up never touched (paella, quiche, paneer, vegan pancakes) |
| Eval replay (engine, all turns) | – | p50 **188 ms** / p90 **741 ms**; substitution turns p50 317 / p90 616 ms |
| Eval live (with Gemini) | – | p50 3.9 s / p90 15.4 s all turns; substitution p50 2.9 s / p90 6.7 s. This run predates the recipe_tags index fix (below), and Gemini was failing: 18 LLM errors (503s, timeouts) in 40 turns |
| Startup | contexts + sizes ~15 s | the same, plus demos 7–9 replayed in a background thread (11 s in total on this machine, while the oracle was running) |

Target "substitution turns ≤ 6 s after warm-up": met for the engine (≤ 0.7 s). With the model, p90 is 6.7 s because
the step rewrite has the 12 s cap you chose in M5 and Gemini was slow last night.

## What changed (3 commits: `da45ef2`, `f0fe8d8`, plus this report)

- **Lexicon:** I reviewed all 106 non-root_veg rows of docs/tag_audit.md where the LLM says "contains" and we say
  nothing, plus your list. About 60 real misses are tagged (full list in docs/lexicon_todo.md → Done). Two mechanics
  were needed:
  - `contains_whole` / `may_contain_whole` lists, matched before the `except` mask. Without them "peanut butter cup"
    could never be dairy, because "peanut butter" is excepted.
  - Removing rum/brandy extract from the alcohol `except` list.
- **Parser bug (safety relevant):** "2 tablespoons buttermilk for brushing" was stored as the canonical "for brushing"
  (the suffix fallback picked "for brushing", which had become a vocab entry). The dairy was lost at the canonical
  level, though the line scan still caught it. The trailing "for <purpose>" phrase is now stripped. 944 recipes had
  "for dusting". This moved demo 2 by +1/+2 and demo 3 by +5; the oracle recomputes independently and agrees.
- **"sugar cookies", "egg salad"** can now be L1 phrases.
- **Speed:**
  - covering indexes on ingredient_lines;
  - `recipe_canon` + `recipe_size`, so L2 Jaccard is exact (the n_ingredients shortcut is gone);
  - `ANALYZE` at the end of the build;
  - a startup thread that warms demos 7–9;
  - an index on `recipe_tags(recipe_id, tag)` (see below).
- **LLM:** on HTTP 503/504, one retry on `GEMINI_FALLBACK_MODEL` (default `gemini-3.5-flash`), using what's left of
  that call's budget, only if ≥ 2.5 s remain. `LLM_REPLAY=1` makes the cache the only source.
- **Oracle:** now runs with the rule parser (no quota, no timeouts) and saves its numbers to
  `eval/oracle_values.json`, which eval/run.py compares stats against.
- **Eval:**
  - `eval/cases.yaml` has 24 cases, 40 turns, programmatic assertions only. Results are re-checked with independent
    SQL, never with the code under test.
  - `eval/run.py` (live or `--replay`) writes `eval/REPORT.md`.
  - `eval/baseline_oneshot.py`.
  - `make eval` (replay), `make eval-live`, `make baseline`.

## Bugs the eval found (all fixed, with regression tests)

1. **A query-plan regression from my own rebuild.** After `ANALYZE`, the per-result evidence query became a
   30k-row scan per result. "I cannot have dairy" took 11.6 s; "find a vegan curry recipe" took **55 s**. An index on
   `recipe_tags(recipe_id, tag)` brought it to 0.24 s. It's added to ingest.py and was created in place on the
   current DB (0.9 s, no second rebuild). A test pins the query plan.
2. "Which recipes … use applesauce instead of eggs?" was hijacked by the substitution parser, a high-confidence
   rule, so the LLM never saw it. Questions asking for recipes are now never substitutions.
3. "show me the frist one" only worked through the LLM; ordinal typos are now rule-level.
4. Demo 6: marshmallows passed "no sugar". The sugar family's `broad` list (read at query time) now includes
   marshmallows, caramel and candy.
5. The test suite was overwriting `eval/oracle_values.json` with fixture numbers.

## Decisions I made without you

1. **Wonton wrapper, vanilla wafer, gnocchi, ranch, pasta dough** are egg **may_contain**, not contains
   (label-dependent, like fresh pasta). **Royal icing** and **Hellmann's** are contains.
2. **Kept untagged on purpose** (listed in lexicon_todo): distilled whiskey for gluten, ginger beer and margarita mix
   for alcohol, Campbell's tomato soup for dairy, crème de cacao for dairy, cocktail sauce for shellfish.
3. **Too ambiguous to tag:** "crisp", "frank", "jiffy". Plain "cooking spray" is not tagged soy either: it would flag
   thousands of recipes for refined lecithin. Baking spray is tagged (it also has flour).
4. **"jack" = Monterey Jack cheese (dairy)**, with "jack daniel(s)" and "jackfruit" excepted.
5. **"pig", "speck" = pork + meat; "schmaltz", "poussin", "giblet" = poultry + meat** (meat already covers poultry,
   so the vegan preset stays correct). **Snail/escargot = shellfish** (molluscs).
6. **Fallback model `gemini-3.5-flash`**, overridable with `GEMINI_FALLBACK_MODEL`. When I probed it, it was also
   returning 503. The name is accepted (no 404 or 400), but I never saw it answer.
7. **Each validation attempt keeps its full timeout;** a fallback shares the budget of the attempt it retries.
8. **The warm-up replays the three demo prompts** with the rule parser on a private connection. The caches are keyed
   by DB path, so requests share them.
9. **Demo 6 deviates from the PRD wording.** With marshmallows correctly dropped, 35 saffron recipes with ≤ 2 steps
   and no sugar really exist, so an "explicit no-match" would be false. The case asserts that honest answer, and a
   second case ("at most 1 step") asserts the explicit no-match with flagged alternatives.
10. **The desserts question** answers with a labelled title-keyword proxy under payload type "unsupported". The case
    asserts the label ("no category field", "PROXY", "title"), not a stats type.
11. **The baseline's system prompt** describes the dataset (sources, size, id format). That gives away the record
    count, but the question checks the *valid* count. Recipe Box's column uses the full system (LLM planner via the
    cache).
12. **I ran the live eval only once,** as asked. Three fixes landed after it; the replay re-checks every case on the
    current code with the live run's cached LLM answers.
13. **The in-place index** on the existing DB counts as a migration, not the second rebuild you said not to do.

## Failed, skipped or not verified

- **The fallback model never answered successfully** in my probe (503). Its logic is unit-tested with a scripted
  remote; the live run tried it where budget allowed, and it timed out or was overloaded.
- **Live latency** includes the pre-index-fix searches and a bad Gemini hour. I didn't spend quota on a second live
  run.
- **No automated test for the startup warm-up thread;** it's exercised by every eval run (run.py joins it).
- **11 recipes** keep a junk "for lining"-style canonical from equipment lines that *start* with "for" after
  masking. This is logged for the next rebuild.
- **The DB grew to 995 MB.** The Docker image and the Railway build will be bigger. RAM is unaffected (peak RSS at
  build 331 MB; the runtime reads through SQLite).
- **Not done (part 2):** README, DECISIONS.md, the Railway redeploy, the demo recording.
- **`.claude/settings.json`** shows as modified in git. I didn't touch or commit it.

## Commands to verify

```bash
cd backend && python -m pytest -q          # 231 passed
cd .. && python eval/oracle.py             # 9 x PASS (~3 min), writes eval/oracle_values.json
python eval/run.py --replay                # 24/24, rewrites eval/REPORT.md (no quota)
python eval/baseline_oneshot.py --replay   # baseline from the cache
git log --format='%an <%ae>%n%b' | grep -i -E 'claude|anthropic'   # prints nothing
```
