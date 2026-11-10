"""Family-tag consistency audit: members whose tags differ from their family's majority.

A family (lexicon/families.yaml + suffix grouping) should mostly agree on tags: every pasta is gluten, every
cheese is dairy. For each family, the majority tags are those held at 'contains' by >= 50% of the family's
recipes (recipe-weighted). A member that lacks a majority tag (or only has it at may_contain) is a likely
lexicon miss ("bucatini" without gluten); one that has a tag the family lacks is listed as 'extra' for review.
Uses data/recipes.db vocab (canonical, family, recipe_count) and the CURRENT lexicon via normalize.tags_for,
so it shows what the next rebuild will tag. Read-only.
Run: python scripts/audit_tags.py [--min 20] [--top 40]
"""
import argparse
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app import normalize as nz  # noqa: E402
from app.config import DB  # noqa: E402


def audit(con: sqlite3.Connection, min_recipes: int = 20) -> list[tuple]:
    """[(kind, family, tag, member, member_level, member_recipes, majority_share)] sorted by recipes desc."""
    fams = defaultdict(list)
    for c, f, n in con.execute("SELECT canonical, family, recipe_count FROM vocab WHERE recipe_count > 0"):
        fams[f].append((c, n, dict(nz.tags_for(c))))
    out = []
    for f, members in fams.items():
        total = sum(n for _, n, _ in members)
        if len(members) < 2 or total < min_recipes:
            continue
        tags = {t for _, _, tg in members for t in tg}
        share = {t: sum(n for _, n, tg in members if tg.get(t) == "contains") / total for t in tags}
        for c, n, tg in members:
            if n < min_recipes:
                continue
            for t, s in share.items():
                if s >= 0.5 and tg.get(t) != "contains":
                    out.append(("missing", f, t, c, tg.get(t, "-"), n, s))
                elif s < 0.1 and tg.get(t) == "contains" and c != f:
                    out.append(("extra", f, t, c, "contains", n, s))
    return sorted(out, key=lambda r: (r[0] != "missing", -r[5]))


def main() -> None:
    """Print the audit; exit 0 always (it is a review list, not a gate)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=20, help="ignore members/families with fewer recipes")
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    con = sqlite3.connect(f"{DB.as_uri()}?mode=ro", uri=True)
    rows = audit(con, a.min)
    miss = [r for r in rows if r[0] == "missing"]
    print(f"Family-tag audit (members with >= {a.min} recipes): {len(miss)} missing, {len(rows) - len(miss)} extra")
    for kind, f, t, c, lv, n, s in rows[:a.top]:
        print(f"  {kind:7} {t:9} family={f:<18} member={c!r:<34} level={lv:<11} {n:>6,} recipes "
              f"(family {100 * s:.0f}% contains)")


if __name__ == "__main__":
    main()
