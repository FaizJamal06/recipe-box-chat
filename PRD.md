# PRD — "Recipe Box" Grounded Recipe Chatbot

Owner: Faiz Jamal · Deadline: 4 days from receipt · Status: build-ready
Audience: Claude Code (implementer) + Faiz (reviewer, will defend this code live in an interview)

> **Prime directive:** the LLM never states a dataset fact. Code retrieves and computes; the LLM only
> (a) turns user text into a structured plan and (b) rewrites instructions/explanations from evidence
> it is handed. Every number, recipe ID and ingredient claim shown to the user comes from a tool result.

---

## 0. How to use this document (Claude Code: read this first)

- Work **one milestone at a time** (§10). For a milestone, read §1–§3 once, then only the sections
  that milestone names. Do not re-read the whole PRD each turn.
- P0 = required for submission. P1 = do if milestone is on time. P2 = only if everything else is done.
- When a requirement here conflicts with "write less code", the requirement wins. Ponytail governs
  *how* we build, not *whether* a P0 item exists.
- Never load raw dataset files into context. Use `scripts/peek.py` (§10, M0).

## 1. Goal and grading

Build a conversational chatbot over the Recipe Box dataset (all 3 JSON files, ~125k recipes) that:

| Task | Weight | What "great" looks like |
|---|---|---|
| T1 Search + factual Q&A + stats | 3/10 | Multi-turn refinement with sticky restrictions; stats computed over the *full filtered set* with filters, N, denominator and method stated |
| T2 Ingredient matching | 3/10 | Explainable score; matched / unused / extra ingredients per result; hard constraints never silently relaxed; quantity check where reliable |
| T3 Evidence-based substitution | **4/10** | Local recipes cited by ID as evidence, strength graded, full adapted recipe (ingredients + instructions) as a diff, predicted vs verified effects separated |
| Eval | gate | ≥5 demo conversations, a reproducible eval set with a pass/fail report, and a one-shot-LLM baseline that fails where we don't |

Non-goals: inventing recipes (T2), nutrition/cook-time facts, user accounts, mobile app, fine-tuning.
Vector search / FAISS is **out of the shipping scope**: optional post-launch milestone M7 only (§9 D3).

**Main goal: a live, working chatbot at a public URL.** A working core deployed on Day 3 beats a
polished app on localhost on Day 4. The Space goes live at the end of M4 and gets redeployed after.

## 2. Constraints that shape every decision

1. **4 days, one developer + Claude Code.** Simple, boring, explainable stack. No LangChain/LlamaIndex
   (opaque; Faiz must modify code live in the interview).
2. **Free-tier LLM (Gemini via Google AI Studio)** — free-tier limits are roughly 5–15 RPM and
   100–1,000 requests/day depending on model, and change often. Design for **≤2 LLM calls per turn**,
   with caching and a rule-based fallback planner.
3. **Interviewer must run it locally** from the README in <10 minutes, and we also ship a **live demo**.
4. Every module small (target <300 lines), typed, with docstrings that explain the *why*.

## 3. Architecture (one page)

```
            ┌──────────── React UI (chat + evidence panel + constraint chips) ────────────┐
            │                                                                              │
            ▼                                                                              │
   FastAPI  /api/chat ──► Session (sticky state) ──► Planner ──► Executor (pure Python) ──► Composer
                              │                     (LLM #1:     │  search.py   (FTS5 BM25 + filters)   (templates;
                              │                      JSON plan;  │  stats.py    (SQL over full set)      LLM #2 only
                              │                      rule        │  match.py    (scored ranking)         for T3
                              │                      fallback)   │  substitute.py (evidence mining)      rewrite)
                              ▼                                  ▼
                        state_patch merge              SQLite: recipes · ingredient_lines · recipe_tags · vocab · FTS5
                                                                   ▲
                                         ingest.py + normalize.py + lexicon/*.yaml (built once, offline)
```

- **Storage:** one SQLite file (`data/recipes.db`), stdlib `sqlite3`, FTS5 for keyword search.
- **Backend:** Python 3.11, FastAPI, `google-genai`, `pyyaml`, `pytest`. That's it (plus uvicorn).
- **Frontend:** Vite + React + TypeScript + Tailwind, built to static files and served by FastAPI.
- **Deploy:** single Docker image → Hugging Face Spaces (Docker SDK, free CPU). DB built at image build.
- **CLI:** `python -m app.cli` uses the same engine (the assignment accepts CLI; it's our fallback demo).

## 4. Data and normalization (the foundation — most bugs live here)

### 4.1 Source
- Download: `https://eightportions.com/recipes_raw.zip` (script with retry; README also documents manual
  placement into `data/raw/`).
- **Confirmed from the scraper source** (github.com/rtlee9/recipe-box, `src/get_recipes.py`): each record
  is written as `{title, ingredients, instructions, picture_link}`, and **any field can be `None`** when
  scraping failed. Files are keyed per site (`ar` = Allrecipes, `epi` = Epicurious, `fn` = Food Network).
- **Expected, verify in M0:** the hosted zip uses the names `recipes_raw_nosource_{ar,epi,fn}.json`; each is
  a dict `{hash_key: record}`, `ingredients` is a list of strings, `instructions` a single string; ~125k
  records total; Allrecipes ingredient lists contain literal `"ADVERTISEMENT"` artifacts.
- Ignore `picture_link` (images not needed). Don't use the scraper; it's only a schema reference.

### 4.2 Stable IDs and originals
- `recipe_id = f"{source}:{hash_key}"` with `source ∈ {ar, epi, fn}`. Assert uniqueness at ingest.
- Store **original** title, ingredient lines and instructions verbatim. Derived/clean fields live in
  separate columns. Display strips only `ADVERTISEMENT` (documented).

### 4.3 Validity (single definition, used everywhere)
A recipe is **valid** iff: non-empty title, ≥1 real ingredient line (not empty, not `ADVERTISEMENT`, not a
section header like `"For the sauce:"`), non-empty instructions. Invalid records are kept in the DB with
`invalid_reason` but excluded from search/stats/matching. Every stats answer states
"N valid of M records".

### 4.4 Counting rules (must be stated in answers)
- `n_ingredients` = number of real ingredient lines (rule above).
- `n_steps` = number of non-empty newline-separated segments of `instructions` after strip.
  Also store `n_sentences` (secondary). M0 profiles per-source formatting; if a ranking is dominated by
  1-step paragraph-style recipes, the answer adds a caveat line (P1: show sentence-rule ranking too).

### 4.5 Ingredient line → structured
`normalize.parse_line(raw) -> ParsedLine(raw, qty, unit, name_clean, canonical, family, alternatives[], is_header)`
1. lowercase; strip `ADVERTISEMENT`; remove parentheticals (keep a copy — sizes like "(15 oz)" feed qty).
2. qty: integers, decimals, ranges ("2-3" → 2.5, keep range), unicode & ascii fractions ("1 1/2", "½").
3. unit from `lexicon/units.yaml` (cup, tbsp, tsp, oz, lb, g, kg, ml, l, pinch, dash, clove, can, package,
   slice, stick …) with unit family (volume / mass / count / container).
4. drop size & prep descriptors (`large, small, fresh, chopped, minced, diced, sliced, softened, melted,
   divided, to taste, room temperature, peeled, seeded, freshly ground …`); keep text before first comma.
5. split alternatives on ` or ` / `/` → `alternatives` (e.g. "butter or margarine").
6. canonicalize: synonym map (`lexicon/synonyms.yaml`, e.g. scallion/spring onion→green onion,
   garbanzo→chickpea, cilantro/coriander leaves→cilantro) → singularize → longest-match against the
   canonical vocabulary.

**Identity vs. contains (key design decision — explain in DECISIONS.md):**
- `canonical` = *what product it is* (used for matching). Forms stay distinct when they change the match:
  `tomato ≠ tomato paste ≠ tomato sauce ≠ sun-dried tomato`, `garlic ≠ garlic powder`,
  `rice ≠ rice vinegar ≠ rice flour`, `egg ≠ egg noodles`, `onion ≠ green onion ≠ onion powder`.
- `family` = looser group for "broad" stats (onion family includes red/white/yellow/sweet onion;
  broad mode also includes green onion & onion powder). Defined in `lexicon/families.yaml`.
- `tags` = *what it contains* (used for hard constraints), from `lexicon/tags.yaml`, two levels:
  `contains` and `may_contain`. Examples that tests must cover:
  - dairy: milk, cream, butter, cheese (all types), yogurt, ghee, whey, buttermilk, sour cream → contains.
    **Not dairy:** coconut milk/cream, almond/soy/oat milk, peanut butter, cream of tartar, butternut squash,
    cocoa butter (contains), "dairy-free"/"vegan" prefixed items. `margarine`, `chocolate`, `bread` → may_contain.
  - egg: egg, egg white/yolk, mayonnaise, egg noodles, meringue → contains.
  - peanut: peanut, peanut butter, peanut oil → contains. tree_nut separate (almond, cashew, walnut, pecan,
    pine nut, pesto→may_contain …).
  - gluten, meat, poultry, fish, shellfish, pork (for "vegetarian", "no pork" etc.).
- Hard filters exclude `contains`. `may_contain` lines are shown with a ⚠ "check label" badge;
  a `strict` toggle excludes them too. A line with a compliant alternative ("butter or margarine" under
  no-dairy) is eligible **with a visible note** — never silently.

**Coverage target:** ≥90% of real ingredient lines map to a canonical with recipe frequency ≥5.
Report the actual number in `docs/DATA_PROFILE.md` and README. (P2: LLM-assisted mapping of the long
tail, committed as a reviewed CSV — disclose if used.)

### 4.6 Schema
```sql
recipes(id TEXT PRIMARY KEY, source TEXT, title TEXT, ingredients_raw TEXT /*JSON list*/,
        instructions_raw TEXT, n_ingredients INT, n_steps INT, n_sentences INT,
        valid INT, invalid_reason TEXT)
ingredient_lines(recipe_id TEXT, line_no INT, raw TEXT, name_clean TEXT, canonical TEXT,
        family TEXT, qty REAL, unit TEXT, unit_family TEXT, alt_group INT, is_header INT)
recipe_tags(recipe_id TEXT, tag TEXT, level TEXT, evidence_line_no INT)   -- one row per (recipe, tag)
vocab(canonical TEXT PRIMARY KEY, family TEXT, recipe_count INT)
recipes_fts USING fts5(id UNINDEXED, title, ingredients, tokenize='porter')  -- title weighted 3x in bm25()
```
Indexes on `ingredient_lines(canonical)`, `ingredient_lines(recipe_id)`, `recipe_tags(tag)`.

## 5. Conversation engine

### 5.1 Session state (sticky; visible in UI as chips)
```python
@dataclass
class SessionState:
    active_task: Literal["search","match","substitute","stats", None]
    query_text: str | None            # dish / NL keywords, e.g. "penne pasta"
    include: list[str]                # canonical ingredients that must appear
    exclude: list[str]                # canonical ingredients forbidden (hard)
    exclude_tags: list[str]           # e.g. ["dairy","peanut"] (hard)
    max_steps: int | None; max_ingredients: int | None
    have: list[HaveItem]              # T2 pantry: name, qty?, unit?
    prefs: dict                       # e.g. {"fewest_extra": True, "fewest_steps": False}
    strict_may_contain: bool
    last_results: list[str]           # recipe IDs in displayed order (for "the second one")
    selected_recipe_id: str | None    # for "this recipe"
    history: list[Turn]               # last 6 turns only, for the planner
```
Rule: a newly stated restriction **adds** to state and re-runs the active task; it is removed only if the
user says so ("dairy is fine now", chip ×). A brand-new dish request resets `query_text`/`include` but
**keeps restrictions** (they are about the person, not the dish) — say so in the reply once.

### 5.2 Planner (LLM call #1)
Input: compact state JSON + numbered `last_results` (id + title, max 10) + last 6 turns + user message.
Output (Gemini structured output / JSON schema, validated with dataclasses; on invalid JSON retry once):
```json
{"intent":"search|recipe_detail|stats|match|substitute|unsupported|clarify|smalltalk",
 "state_patch":{"mode":"refine|new","query_text":null,"include_add":[],"exclude_add":[],
                "exclude_remove":[],"exclude_tags_add":[],"exclude_tags_remove":[],
                "max_steps":null,"have_set":null,"prefs":{}},
 "stats":{"op":"count|percentage|top_ingredients|mean|median|rank","field":"n_ingredients|n_steps",
          "order":"asc|desc","limit":5,"all_of":[],"any_of":[],"none_of":[],"title_contains":[],
          "normalization":"strict|broad|both"},
 "target":{"kind":"result_index|recipe_id|title|selected","value":null},
 "substitution":{"remove":[],"restrictions":[],"dataset_only":true,"external_ok":false},
 "unsupported":{"attribute":"nutrition|cook_time|servings|rating|category|other","reason":""}}
```
- Planner names ingredients in plain words; the **executor** canonicalizes them with `normalize` (single
  source of truth). The planner never outputs IDs that weren't in `last_results`.
- **Rule fallback planner** (P0, small): regex patterns for the 7 demo conversations + generic
  "how many recipes contain X and Y", "fewest steps", "I have …", "no X", "remove/replace X". Used when the
  LLM errors/429s; the UI shows a small "LLM unavailable — rule parser" badge.
- Cache planner responses keyed by (prompt hash) in `data/llm_cache.sqlite` → reproducible eval replays.

### 5.3 Unsupported-attribute guard (deterministic, runs before planner output is trusted)
The dataset has **no** nutrition, total cook time, servings, ratings, cuisine or category fields.
- Nutrition/calories/macros → refuse with what's missing; offer ingredient-level facts instead.
- Cook time → "no cook-time field"; P1: list durations *mentioned in the instructions* (regex
  `\d+ (minutes|hours)`), labelled "mentioned in instructions, not a total time".
- Category questions ("average ingredients in desserts") → state there is no category field; offer a
  clearly-labelled **title-keyword proxy** (e.g. title contains cake|cookie|pie|brownie|pudding), show the
  keyword list, and compute on that.
- Any external fact or estimate must be labelled `External` / `Estimate`.

## 6. Task executors

### 6.1 T1 search (`search.py`)
- Candidate retrieval: FTS5 `bm25(recipes_fts, 3.0, 1.0)` on `query_text` (planner may add 2–4 expansion
  keywords for NL requests, e.g. "cozy winter soup" → soup, stew, chowder) ∩ `include` (SQL on
  `ingredient_lines.canonical`) − `exclude`/`exclude_tags` (SQL on `recipe_tags` / canonical) ∩ step limit.
- Return top 10 with: id, title, source, n_ingredients, n_steps, **evidence**: for each active restriction,
  the ingredient lines proving compliance (e.g. no-dairy → "0 dairy-tagged lines; checked 9 lines";
  include penne → the matching raw line). Also the total eligible count ("312 recipes match; showing 10").
- `recipe_detail`: full original ingredients + instructions + parsed view.

### 6.2 T1 stats (`stats.py`) — never LLM-computed
Typed ops over the **complete filtered set** (SQL), no free-form LLM SQL:
`count`, `percentage` (denominator = valid recipes unless user specifies a subset — always printed),
`top_ingredients(k)` (by recipe frequency, not line count), `mean`/`median` of `n_ingredients`/`n_steps`,
`rank(field, order, limit)` with deterministic tie-break `(field, id)`.
Every result returns: `value`, `filters` (human-readable), `n_analyzed`, `denominator`, `method` (one
sentence), `sql` (exact query string, shown under "Show calculation"), `normalization_note`.
For ingredient-presence questions default `normalization="both"`: report **strict** (canonical, e.g. fresh
garlic forms only) and **broad** (family, e.g. incl. garlic powder / green onion) and explain the difference.

### 6.3 T2 matching (`match.py`)
Definitions (state them in README and in the UI legend):
- `U` = user's have-set (canonical); `P` = pantry staples assumed available: `salt, black pepper, water`
  (shown in the UI, user can toggle off); `R` = recipe's canonical set − `P`.
- **matched** = U∩R · **unused** = U−R (your ingredients this recipe doesn't use) · **extra required** = R−U.

Eligibility (hard, applied before scoring): no `exclude`/`exclude_tags` violation (contains-level; plus
may_contain if strict), `n_steps ≤ max_steps`, `|matched| ≥ 1`.
Score (deterministic, shown as a breakdown bar per result):
```
score = w_m·|matched| − w_e·|extra| − w_s·n_steps − w_q·(#matched items with insufficient quantity)
default w_m=2.0, w_e=1.0, w_s=0.1, w_q=0.5
prefs: "use as many as possible" → w_m=3.0 ; "fewest additional" → w_e=1.5 ; "fewest steps" → w_s=0.5
tie-break: |matched| desc, |extra| asc, n_steps asc, id asc
```
"Why ranked here" sentence generated from the components (template, not LLM).
Quantities: if the user gave qty and the recipe line has qty in the **same unit family** (convert within
volume / mass / count only; never volume↔mass) → `sufficient | short by X`. Otherwise
"name-level match; quantity not verified". 
**No-match:** if eligible set is empty → say exactly "No recipe satisfies all hard constraints" + list the
constraints; then a separate, red-flagged "Closest alternatives (each violates: …)" built by relaxing **one**
constraint at a time and naming it. Never mix the two lists.
Candidate prefilter: recipes containing ≥1 item of U (index lookup), then score in Python.

### 6.4 T3 substitution (`substitute.py`) — biggest weight, most care
Input: target recipe (resolve "this banana bread" → `selected_recipe_id`, else search and **state which ID
was picked**), ingredients to remove, user restrictions, `dataset_only`, `external_ok`.

1. **Lines affected:** all lines whose canonical/tags match the removed item (egg → whole eggs, whites, yolks).
2. **Role:** `lexicon/roles.yaml` keyed by (ingredient, dish context). Dish context from a tiny classifier:
   baked (flour + bake/oven words), sauce/pasta, dessert-cold, savory-other. E.g. egg@baked →
   binding, leavening, moisture, structure; cream@pasta → richness/fat, body/thickening. Unknown pair →
   LLM proposes roles, labelled "model reasoning, not dataset evidence".
3. **Candidates:** curated `lexicon/candidates.yaml` per (ingredient, role) **plus data-discovered**
   candidates (step 5 contrast mining). Remove any candidate violating user restrictions (e.g. yogurt under
   dairy-free, cashew under tree-nut allergy, mayonnaise under no-egg). If `dataset_only`, keep only
   canonicals present in `vocab` with recipe_count ≥ 5.
4. **Dish family** (three evidence tiers):
   - L1 *same dish*: title contains the dish phrase (e.g. "banana bread") or its head variants
     (banana + bread|loaf).
   - L2 *similar recipes*: Jaccard(canonical sets) ≥ 0.35 with the target, same dish context.
   - L3 *broad context*: all recipes with the same dish context (e.g. all baked goods).
5. **Evidence mining per tier:** split family into WITH-target and WITHOUT-target. For each candidate:
   `support = #WITHOUT recipes containing candidate`, `lift = P(cand|WITHOUT) / P(cand|WITH)`.
   Titles with explicit variant markers (`eggless, egg-free, no-egg, vegan, dairy-free, non-dairy`) are
   **direct** evidence. Data-discovered candidates = canonicals with lift ≥ 2 and support ≥ 3 in L1/L2.
   Also pull 1–2 instruction sentences from supporting recipes that mention the candidate (e.g. how flax is
   prepared) — quoted with the recipe ID.
6. **Strength grade** (shown as a badge, defined in README):
   `Strong` = ≥1 explicit-variant L1 recipe or support ≥3 in L1 · `Moderate` = support ≥3 in L2 ·
   `Weak` = only L3 or support <3 · `None`. **Conflicting** flag when top candidates' lifts disagree across
   tiers, or the best-supported candidate violates a restriction. Weak/None/Conflicting → say so plainly;
   if `external_ok` and P2 implemented → external search, links shown in a separate "External sources" box.
7. **Quantity:** if ≥3 supporting recipes have parseable qty for both candidate and the family's typical
   target qty → report median observed ratio ("eggless L1 recipes used a median ¼ cup applesauce where
   egg versions used 2 eggs") labelled *observed, indirect*. Else quantity = "not verified; start with X"
   labelled *estimate*.
8. **Adapted recipe (P0):** ingredient list diff is **deterministic** (remove affected lines, add substitute
   lines). Instructions: **LLM call #2** with numbered original steps + substitution + supporting snippets;
   must return JSON `[{n, text, changed, reason}]`. **Validator:** unchanged steps must be byte-identical to
   the originals; no remaining mention of the removed ingredient (synonym regex); the substitute is
   mentioned where the target was. On failure retry once, then deterministic fallback (insert a prep step
   + replace mentions).
9. **Effects:** two labelled blocks — *Verified from dataset* (counts, IDs, ratios) and *Predicted (not
   verifiable from recipe text)* (taste/texture/prep changes, LLM-written from the role + evidence).
10. **Safety line** whenever an allergy is involved: recipe text can't establish medical safety; check
    labels for cross-contamination. If no adaptation is supportable → say so and don't produce one.

## 7. Composer and API

- Replies for search / stats / match are **templated** from executor output (zero hallucination, no LLM
  call). Only T3 instructions + effects use LLM #2. Post-check every reply: every recipe ID in the text
  must exist in the payload (strip and log otherwise).
- `POST /api/chat {session_id, message}` → `{reply_md, payload:{type, ...executor output}, state, trace[]}`
  where `trace` = human-readable pipeline steps ("Parsed: exclude_tags+=dairy" → "Filtered 1,284 → 211"
  → "Ranked by BM25").
- `GET /api/recipe/{id}`, `PATCH /api/session/{id}/state` (chip removal/toggles), `POST /api/session/{id}/reset`,
  `GET /api/health` (DB counts, LLM reachable).
- Sessions in memory (dict + TTL). Per-session rate limit (e.g. 10 msgs/min) to protect the free key.

## 8. UI (good, not gold-plated)

Design direction: warm "recipe box" editorial — cream background, ink text, one accent (tomato red),
serif display headings (Fraunces), Inter for body, JetBrains Mono for recipe IDs. Use the
`frontend-design` skill once at the start of the UI milestone.

Layout (desktop first, responsive to tablet):
- **Left (60%) chat:** messages, markdown, inline result cards. Empty state = 7 example-prompt chips
  (the demo conversations in §11) — click to send.
- **Constraint bar** above input: sticky chips for active state (`no dairy ×`, `≤6 steps ×`, `have: eggs,
  rice…`, `strict ⚠ toggle`). Removing a chip PATCHes state and re-runs.
- **Right (40%) evidence panel**, tabs: **Results** (cards) · **Calculation** (filters, N, denominator,
  method, SQL, normalization note) · **Evidence** (T3 table: candidate | role | tier | support | lift |
  strength badge | supporting IDs) · **Trace**.
- Recipe card: title, mono ID with copy button, source badge (AR/EPI/FN), #ingredients, #steps,
  color chips (matched green / extra amber / unused grey / violation red / may-contain ⚠).
  Click → drawer with the original recipe.
- Substitution view: side-by-side diff (strikethrough removed, green added) for ingredients and steps;
  "Verified" vs "Predicted" blocks visually distinct.
- Loading state shows the trace steps as they're known; errors are human ("LLM rate-limited — used rule
  parser").

## 9. Key decisions (copy into `DECISIONS.md` with 2–3 lines of reasoning each)
- D1 SQLite + FTS5 over a vector DB: graded on exact filtering/aggregation over the full set; SQL gives
  reproducible counts; zero infra.
- D2 LLM as planner, not oracle; typed stats ops instead of LLM-written SQL (safer, testable).
- D3 No vector DB in the shipped version: the task is graded on exact filtering and full-set
  aggregation, which top-k similarity search can't provide (the PDF says not to aggregate over semantic-search
  hits), and embeddings handle negation ("no dairy") badly. BM25 + LLM keyword expansion covers the required
  queries. Embedding 125k recipes also adds build time, RAM and setup on the free host. Post-launch M7 adds
  vectors as a *candidate retriever only* (hybrid with BM25); filters and stats stay in SQL.
- D4 Identity vs contains-tags (§4.5) — matching precision and allergen safety need different notions.
- D5 Conservative may_contain handling; never silently relax.
- D6 Weighted, displayed score over lexicographic sort (lexicographic lets a 4-match/15-extra recipe beat
  3-match/2-extra).
- D7 Evidence tiers + lift for substitution: answers "what do recipes *without* X tend to use instead".
- D8 Templates for factual replies; LLM only where language generation is the job.

## 10. Milestones (each = one Claude Code session; `/clear` between)

| # | When | Scope | Done when |
|---|---|---|---|
| M0 | Day 1, 1–2h | Scaffold repo (§12), `scripts/download.py`, `scripts/peek.py` (prints N sample records, truncated), `scripts/profile_data.py` → `docs/DATA_PROFILE.md` (records per file, empty/invalid counts, ADVERTISEMENT freq, n_steps distribution per source, top 300 cleaned ingredient names). **De-risk deploy:** a Dockerfile whose build downloads the zip, plus a FastAPI `/api/health` returning record counts, pushed to the HF Space | Faiz reviews profile; §4.1 confirmed or PRD amended; Space URL shows health JSON (proves HF can download the data) |
| M1 | Day 1 | `normalize.py`, `lexicon/*.yaml`, `ingest.py`, DB build; tests with a 30-recipe fixture (`tests/fixtures/mini.json`) incl. every tricky case in §4.5 | `make db` builds in <10 min; coverage number in DATA_PROFILE; `pytest -q` green |
| M2 | Day 2 AM | `search.py`, `stats.py`, rule planner, `cli.py` | Demo convs 2 & 3 (§11) correct in CLI; stats cross-checked by `eval/oracle.py` (pure Python over parsed JSON, **not** SQL) |
| M3 | Day 2 PM | `llm.py`, `planner.py` (+cache), `session.py`, `match.py`, unsupported guard | Demo convs 1, 4, 5, 6 correct in CLI incl. follow-ups |
| M4 | Day 3 AM | `api.py`, frontend (layout, chips, cards, panel, drawer), DB built in the Docker image, **first live deploy** | Demos 1–6 work on the **live URL**, not just localhost; looks good on 1440px and 1024px |
| M5 | Day 3 PM | `substitute.py` + roles/candidates lexicons + diff UI, redeploy | Demo convs 7, 8, 9 produce cited, graded, validated adaptations on the live URL |
| M6 | Day 4 | `eval/` (cases, runner, baseline), README, DECISIONS, final redeploy, 3-min demo recording, submit | `make eval` writes `eval/REPORT.md`; live URL works from a fresh browser; fresh-clone README run tested; GitHub contributors page shows only Faiz |
| M7 | After submit (optional) | Hybrid retrieval: `fastembed` (bge-small, ONNX, no PyTorch) over title + top ingredients, FAISS `IndexFlatIP`, built in the Docker image; fuse with BM25 via reciprocal rank fusion; SQL hard filters run **after** fusion; stats untouched | Vague queries ("cozy rainy-night soup") improve on 5 hand-picked cases; all eval cases still pass |

**Cut order if behind** (cut from the bottom): P2 external search → P1 sentence-rule ranking → P1
cook-time mentions → Trace tab polish → tablet layout. Never cut: the live deploy, T3 evidence + diff,
eval report, README run instructions, no-match handling.

## 11. Demo conversations (also the eval seed; each must work end-to-end)
1. **Refine (T1):** "Find a penne pasta recipe" → "I cannot have dairy" → "show me the steps for the second
   one" → "also no garlic". Restrictions persist; evidence lines shown.
2. **Stats (T1):** "How many recipes contain both garlic and onion? What percentage of the dataset is that?"
   → strict + broad counts, denominator, normalization note, SQL.
3. **Rank (T1):** "Among recipes containing tomato, which five have the fewest instruction steps?" → IDs, step
   rule stated, paragraph-format caveat if applicable.
4. **Unsupported:** "How many calories are in that one?" and "What's the average number of ingredients in
   desserts?" → refusal with what's missing / labelled title-keyword proxy.
5. **Match (T2):** "I have eggs, onions, tomatoes, and rice. Suggest five recipes using as many as possible,
   no peanuts, at most six steps, fewest additional ingredients." → "Exclude eggs too." → results update.
   Plus quantity variant: "I have 2 eggs and 1 cup rice".
6. **No-match (T2):** "I have saffron and marshmallows, no sugar, at most 2 steps" → explicit no-match +
   separately flagged alternatives.
7. **Substitution strong (T3):** "Take this banana bread recipe and remove eggs. Use only ingredients that
   appear in the dataset. What replacements have evidence from related baked recipes, and how might the
   texture change?"
8. **Substitution dairy (T3):** "Replace cream in this pasta recipe without dairy. Prefer examples from the
   database." then "I'm also allergic to tree nuts" → cashew drops out, re-graded.
9. **Substitution weak/conflicting (T3):** "Remove the egg whites from this meringue / angel food cake" →
   Weak/None, honest refusal or heavily caveated adaptation.

## 12. Repo layout
```
README.md  DECISIONS.md  PRD.md  CLAUDE.md  Makefile  Dockerfile  requirements.txt  .env.example
backend/app/{config,db,normalize,ingest,search,stats,match,substitute,llm,planner,session,compose,api,cli}.py
backend/app/lexicon/{units,synonyms,families,tags,roles,candidates}.yaml
backend/tests/{test_normalize,test_stats,test_match,test_substitute,test_session}.py  tests/fixtures/mini.json
frontend/ (Vite React TS Tailwind)      scripts/{download,peek,profile_data}.py  scripts/git-hooks/commit-msg
eval/{cases.yaml,run.py,oracle.py,baseline_oneshot.py,REPORT.md}   docs/DATA_PROFILE.md
```
Makefile targets: `setup` (venv + npm ci), `data`, `db`, `test`, `eval`, `run` (build UI + uvicorn),
`cli`, `docker`.

## 13. Evaluation (P0)
- `eval/cases.yaml`: ≥15 cases (the 9 demos + restriction removal, "the second one" reference resolution,
  quantity sufficiency, strict may_contain, dataset_only filter, category proxy, cook-time refusal).
  Each case = list of turns + **programmatic assertions** on the payload, e.g.
  `all_results_lack_tag: dairy`, `stat_equals_oracle`, `ids_exist`, `no_match: true`,
  `cited_ids_contain_candidate`, `steps_unchanged_except: [...]`, `strength_in: [Weak, None]`.
- `make eval` runs with live LLM or `--replay` from cache; writes `eval/REPORT.md`: pass/fail table, what
  failed and why (honest), latency, LLM calls per turn.
- `eval/baseline_oneshot.py`: ask the raw LLM (no tools) the same questions; check its IDs against the DB
  and its numbers against the oracle. Report at least one fabricated ID or wrong count side-by-side with
  ours. This goes in the README.

## 14. README must contain (brief)
Quickstart (local, ≤5 commands) · Docker one-liner · live demo URL · architecture diagram · the counting
& normalization rules · scoring formula · evidence grading · eval results table + baseline example ·
known limitations (from `/ponytail-debt` ledger) · **AI tools used** (one short paragraph: Claude Code for
implementation under this PRD; design, rules and evaluation decisions reviewed by me) — the assignment
requires this disclosure.

## 15. Definition of done
- Fresh clone → README steps → working app on a clean machine.
- `git log --format='%an <%ae>%n%b' | grep -i -E 'claude|anthropic'` returns nothing; the GitHub
  contributors list shows only Faiz.
- Live URL works; `/api/health` green.
- All 9 demo conversations pass in the UI; `eval/REPORT.md` committed.
- Faiz can explain, without notes: the step rule, identity vs contains, the match score, evidence tiers/lift,
  why no LLM SQL, and change any one weight or rule live in under 5 minutes.
