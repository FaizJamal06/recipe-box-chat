# RUNBOOK — how to drive Claude Code through this build

## One-time setup (15 min)

```bash
mkdir recipe-box-chat && cd recipe-box-chat && git init
# copy PRD.md, CLAUDE.md, RUNBOOK.md, .claude/, scripts/ from this kit into the repo root
git config user.name  "Faiz Jamal"
git config user.email "<the email on your GitHub account>"
git config core.hooksPath scripts/git-hooks      # strips any AI co-author trailer
echo -e "data/\n.env\nnode_modules/\nfrontend/dist/\n.venv/\n__pycache__/" > .gitignore
git add . && git commit -m "chore: project spec and tooling"
```

Get a Gemini API key at aistudio.google.com → put it in `.env` (`GEMINI_API_KEY=...`). Check which Flash
model your key's free tier allows in AI Studio's rate-limit view and set `GEMINI_MODEL` to that.

Inside Claude Code (run these as **two separate prompts**):
```
/plugin marketplace add DietrichGebert/ponytail
```
```
/plugin install ponytail@ponytail
```
Then `/ponytail full`. Use `/ponytail-review` before each milestone commit and `/ponytail-debt` at the end
(that ledger becomes the README's "Known limitations").

## Keeping Claude Code off the repo's author list
GitHub lists someone as a contributor if they're the commit **author**, or named in a `Co-authored-by:`
trailer. Three layers stop both:
1. `.claude/settings.json` → `attribution.commit` and `attribution.pr` set to `""` (hides CC's trailer and PR footer).
2. `scripts/git-hooks/commit-msg` strips any AI trailer that slips through (tested).
3. `git config user.name/user.email` = you, so you're the author of every commit.

Also:
- Run Claude Code **locally in your terminal/VS Code**. Don't use the Claude GitHub App, `@claude` in issues,
  or cloud sessions that push for you; those can commit as a bot account.
- Push yourself (`git push`), from your machine.
- After the first CC commit, check: `git log -1 --format='%an <%ae>%n%B'`. You should see only your name and
  no `Co-Authored-By` line. If the trailer is there, re-run `git config core.hooksPath scripts/git-hooks`
  and amend: `git commit --amend` (save without the line).
- Before submitting: `git log --format='%an <%ae>%n%b' | grep -i -E 'claude|anthropic'` should print nothing.

Keep the README's short "AI tools used" paragraph anyway. The assignment requires it, and git metadata
is separate from that disclosure.

## Token rules for you
- One milestone = one session. `/clear` when a milestone is done. `/compact` if a session gets long.
- Start each milestone in **plan mode** (Shift+Tab), approve the plan, then let it build.
- Default model Sonnet for M0–M4 and M6. Switch to Opus for M1 normalization rules and M5 substitution,
  where getting it wrong costs the most.
- Don't paste the dataset or big logs into chat. Ask for summaries.
- After each milestone ask: *"Explain what you built in 10 bullets I could say in an interview, incl. one
  trade-off."* Save the answers to `docs/interview-notes.md`. That's your interview prep.

## Kickoff prompts (paste one per session)

**M0**
> Read CLAUDE.md and PRD §0–§4 and §10–§12. Do milestone M0 only: scaffold the repo layout from §12
> (empty modules with docstrings), Makefile, requirements.txt, .env.example, scripts/download.py,
> scripts/peek.py, scripts/profile_data.py. Run download + profile and write docs/DATA_PROFILE.md.
> Also write a Dockerfile (python:3.11-slim, port 7860) whose build runs scripts/download.py, and a
> minimal FastAPI app with GET /api/health returning record counts per file, so I can push it to my
> Hugging Face Space today. Then tell me which assumptions in PRD §4.1 were wrong. Don't build M1 yet.

**M1**
> Milestone M1 (PRD §4, §10). Build normalize.py, lexicon/*.yaml, ingest.py and the DB. First write
> tests/fixtures/mini.json (30 recipes covering every tricky case in §4.5) and the tests, then make them
> pass, then build the full DB and add the coverage number to DATA_PROFILE.md. Show me the 30 most
> frequent unmapped ingredient names at the end.

**M2**
> Milestone M2 (PRD §5.2 rule fallback, §5.3, §6.1, §6.2). search.py, stats.py, rule planner, cli.py and
> eval/oracle.py. Demo conversations 2 and 3 from §11 must be correct in the CLI and match the oracle.

**M3**
> Milestone M3 (PRD §5, §6.3). llm.py (Gemini, structured JSON, cache), planner.py, session.py,
> match.py and the unsupported guard. Demo conversations 1, 4, 5 and 6 must pass in the CLI, follow-ups included.

**M4**
> Milestone M4 (PRD §7, §8). Use the frontend-design skill once for direction, then build api.py and
> the React UI exactly as §8 lays it out. All CLI-passing conversations must work in the browser.
> Keep components few: ChatPane, ConstraintBar, EvidencePanel, RecipeCard, RecipeDrawer, DiffView.
> Update the Dockerfile to build the UI and the DB in the image (multi-stage), so I can deploy it live today.

**M5**
> Milestone M5 (PRD §6.4 — the highest-weighted task, be careful). substitute.py, roles.yaml,
> candidates.yaml, the instruction-rewrite validator and DiffView. Demo conversations 7, 8, 9 must
> produce cited, graded, validated output. Show me the evidence table for banana bread / no eggs.

**M6**
> Milestone M6 (PRD §13–§15). eval cases + runner + baseline_oneshot, REPORT.md, README, DECISIONS.md,
> Dockerfile for Hugging Face Spaces (port 7860, DB built at image build), then I'll deploy.
> Finally run /ponytail-debt and put the ledger in README "Known limitations".

**M7 (optional, only after you've submitted)**
> Milestone M7 (PRD §10, §9 D3). Add hybrid retrieval: fastembed bge-small over title + top ingredients,
> FAISS IndexFlatIP built in the Docker image, reciprocal rank fusion with BM25 in search.py. Hard
> filters stay in SQL after fusion; stats untouched. Add 5 vague-query eval cases; all old cases must still pass.

## Deploy (first push at the end of M0, redeploy after M4, M5, M6; ~30 min the first time)
1. huggingface.co → New Space → SDK **Docker** → CPU basic (free).
2. Space settings → Secrets: `GEMINI_API_KEY`, `GEMINI_MODEL`.
3. `git remote add space https://huggingface.co/spaces/<you>/recipe-box-chat && git push space main`
4. Wait for the build to finish, open the URL, run all 9 demo conversations. Free Spaces sleep when idle,
   so open the URL ~5 minutes before the interview.

## Day plan
| Day | Milestones | Checkpoint you verify yourself |
|---|---|---|
| 1 (today/Tue) | M0, M1 | Space URL shows health JSON; DATA_PROFILE.md makes sense; tricky-case tests pass |
| 2 | M2, M3 | All CLI demos 1–6 correct; oracle numbers match |
| 3 | M4, M5 | **Live URL** runs demos 1–6 (morning) and 7–9 (evening) |
| 4 | M6 + buffer | Fresh-clone install works; authorship check clean; submit |
| later | M7 (optional) | Vague queries better, nothing else broke |
