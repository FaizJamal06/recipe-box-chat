"""CLI over the same engine as the API; also the fallback demo.

Run from the repo root: python -m backend.app.cli                         (interactive, one sticky session)
                        python -m backend.app.cli --ask "How many recipes contain garlic and onion?"
                        python -m backend.app.cli --session demos/demo1_refine.txt [--no-llm]
A session file holds one user turn per line ('#' lines and blank lines are skipped). After every reply the
CLI prints the planner used (LLM or rule parser + why), LLM calls and latency, and the sticky state.
"""
import argparse
import sys
from pathlib import Path

from . import llm
from .db import connect, load_dataset
from .session import Session


def main() -> None:
    """Load the DB counts once at startup, then run --ask / --session turns or a REPL, in one session."""
    ap = argparse.ArgumentParser(description="Recipe Box chatbot (CLI)")
    ap.add_argument("--ask", action="append", help="answer this message (repeatable; same session)")
    ap.add_argument("--session", type=Path, help="file with one user turn per line")
    ap.add_argument("--no-llm", action="store_true", help="use the rule parser only")
    a = ap.parse_args()
    warm = None if a.no_llm else llm.warm()  # google-genai (~6 s cold) loads while the DB loads
    con = connect()
    ds = load_dataset(con)
    if warm:
        try:
            warm.result()  # startup cost, not a turn's: the 6 s LLM budget is for the request only
        except Exception:  # noqa: BLE001  (a broken install shows up as a rule-parser fallback per turn)
            pass
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # recipe titles have accents
    s = Session(con, ds, use_llm=not a.no_llm)
    turns = list(a.ask or [])
    if a.session:
        turns += [x.strip() for x in a.session.read_text(encoding="utf-8").splitlines()
                  if x.strip() and not x.lstrip().startswith("#")]
    for q in turns:
        t = s.respond(q)
        print(f"> {q}\n{t.reply}\n{t.meta()}\nState: {s.state.chips()}\n")
    if turns:
        return
    print(f"Recipe Box: {ds.header(ds.valid)}. Ctrl+C or empty line to quit.")
    try:
        while q := input("> ").strip():
            t = s.respond(q)
            print(f"{t.reply}\n{t.meta()}\nState: {s.state.chips()}\n")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
