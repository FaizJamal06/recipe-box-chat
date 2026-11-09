"""Print N truncated sample records per raw file, so nobody ever opens data/raw/ directly.

Usage: python scripts/peek.py --n 3 [--width 120]
"""
import argparse
import json
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def clip(v, width: int):
    """Truncate strings (and strings inside lists) for display."""
    if isinstance(v, str):
        return v if len(v) <= width else v[:width] + f"… (+{len(v) - width} chars)"
    if isinstance(v, list):
        return [clip(x, width) for x in v[:6]] + ([f"… (+{len(v) - 6} items)"] if len(v) > 6 else [])
    return v


def main() -> None:
    """Show the structure and first N records of every JSON file in data/raw/."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--width", type=int, default=120)
    a = ap.parse_args()
    for p in sorted(RAW.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        print(f"\n== {p.name}: {type(data).__name__}, {len(data)} entries")
        items = list(data.items())[: a.n] if isinstance(data, dict) else enumerate(data[: a.n])
        for k, rec in items:
            print(f"-- key={k}")
            for f, v in rec.items():
                print(f"   {f}: {clip(v, a.width)!r}")


if __name__ == "__main__":
    main()
