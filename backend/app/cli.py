"""CLI over the same engine as the API; also the fallback demo.

Run from the repo root: python -m backend.app.cli            (interactive)
                        python -m backend.app.cli --ask "How many recipes contain garlic and onion?"
"""
import argparse
import sys

from .db import connect, load_dataset
from .session import respond


def main() -> None:
    """Load the DB counts once at startup, then answer --ask or a REPL loop."""
    ap = argparse.ArgumentParser(description="Recipe Box chatbot (CLI)")
    ap.add_argument("--ask", action="append", help="answer this message and exit (repeatable)")
    a = ap.parse_args()
    con = connect()
    ds = load_dataset(con)
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # recipe titles have accents
    for q in a.ask or []:
        print(f"> {q}\n{respond(con, ds, q)[0]}\n")
    if a.ask:
        return
    print(f"Recipe Box: {ds.header(ds.valid)}. Ctrl+C or empty line to quit.")
    try:
        while q := input("> ").strip():
            print(respond(con, ds, q)[0] + "\n")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
