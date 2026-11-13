# How I built this

**Workflow.** I used Claude (chat) as a planning partner to write a PRD with milestones, then had Claude Code implement one milestone at a time. After each milestone I reviewed its report, ran the tests and the oracle, used the app myself, and sent back fixes. Gemini runs inside the app (planner, voice, step rewriter) and offline as an allergen-tag auditor.

**Key decisions (I can walk through each)**
- No vector DB: the task is graded on exact filtering and full-set counts, which top-k similarity can't give.
- The LLM plans and rewords; code computes every fact; a validator rejects any number or ID that isn't in the results.
- Unknown is not safe: an ingredient the system can't verify never passes an allergy filter silently.
- Weak evidence still produces a labelled adaptation; only a defining ingredient (egg whites in a meringue) asks first.
- Deployed on day 1 to find hosting problems early. Hugging Face and Koyeb had both closed their free tiers, so it ended up on Railway.

**Bugs I found by testing it myself**
- "I'm allergic to wheat" still returned penne: an "or" alternative without a tag counted as safe. Rather than patching wheat, I had the whole class fixed: unknown ≠ safe for every allergen, an LLM audit of 3,000 ingredients, and a measured miss rate.
- "Actually I'm not vegan anymore, just no peanuts" → 0 results: filler words became a dish name.
- "Make it vegetarian" on a chicken biryani searched literally for "vegetarian biryani".
- Switching tasks carried old filters (a step limit) into the new request.
- "No salt" gave no adaptation, though 8 of 18 similar recipes skip salt, so I added an "omit it" option.
- The UI showed SQL and raw filter strings and looked bad on phones, so it got a developer-view toggle and a real mobile layout.

**What I checked instead of trusting**
- An independent oracle recomputes the stats from the raw JSON.
- The same questions to raw Gemini invent recipe IDs and give wrong counts (eval/REPORT.md).
- I reviewed the LLM tag audit and kept rules where the LLM was wrong (squash isn't a root vegetable).
