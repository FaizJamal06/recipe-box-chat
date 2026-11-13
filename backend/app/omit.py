"""The "omit it" option of a substitution (PRD 6.4): for a seasoning or optional item (salt, pepper, a garnish, herbs,
nuts as a topping), doing without it is a real answer, graded by how many same-dish recipes don't use it.

Optional = the item's family is in roles.yaml `optional`, or the recipe's own line says so ('for garnish',
'optional', 'to taste', 'for serving', 'for topping'). Grade, from the dish's tiers (no rate contrast: the question is
only "do similar recipes go without it?"):
  Strong   = >= 3 L1 recipes without it and >= 25% of L1 ('8 of 18 broiled chicken recipes have no salt')
  Moderate = >= 3 L2 recipes without it and >= 25% of L2
  Weak     = any L1 or L2 recipe without it; None otherwise.
The adaptation removes the line and takes the item out of the steps (strip()).
"""
import re

import yaml

from . import normalize as nz
from .evidence import Tier

OPTIONAL = set(yaml.safe_load((nz.LEX / "roles.yaml").read_text(encoding="utf-8")).get("optional") or [])
_SAYS = re.compile(r"\b(?:optional|garnish|to taste|for serving|for topping|for sprinkling|for dusting|as needed)\b", re.I)
NAME = "omit it"
_QUAL = (r"(?:(?:a\s+)?(?:pinch|dash|sprinkle|little)\s+of\s+|(?:freshly\s+)?(?:ground|cracked|kosher|sea|coarse|fine|"
         r"table|chopped|fresh|toasted)\s+)*")  # 'a pinch of' / 'freshly ground' before the item


def optional(spec, lines: list[tuple[int, str]]) -> bool:
    """Is leaving it out a sensible option? (A defining item still asks first: substitute.defining.)"""
    return bool({spec.canonical, spec.family} & OPTIONAL) or any(_SAYS.search(raw) for _, raw in lines)


def grade(c, fam: dict, withs: set):
    """Fill the omit candidate's tiers (support = recipes without the item) and strength."""
    c.tiers = {t: Tier(len(ids & withs), len(ids - withs), len(ids - withs), 0, None, sorted(ids - withs))
               for t, ids in fam.items()}
    share = lambda t: c.tiers[t].n_without / max(1, c.tiers[t].n_with + c.tiers[t].n_without)
    a, b = c.tiers["L1"], c.tiers["L2"]
    c.strength = ("Strong" if a.n_without >= 3 and share("L1") >= .25 else
                  "Moderate" if b.n_without >= 3 and share("L2") >= .25 else
                  "Weak" if a.n_without or b.n_without else "None")
    c.ids = a.ids[:6] or b.ids[:6]
    return c


def summary(c, item: str, dish: str) -> str:
    """'8 of 18 'broiled chicken' recipes have no salt' (L1, else L2)."""
    t, where = (c.tiers["L1"], f"'{dish}'") if c.tiers["L1"].n_without else (c.tiers["L2"], "similar")
    return f"{t.n_without} of {t.n_with + t.n_without} {where} recipes have no {item}"


def strip(text: str, rx: re.Pattern, item: str) -> str:
    """The step without the item: 'salt and pepper' -> 'pepper', 'Season chicken with salt.' -> that sentence dropped;
    a step that was only about it becomes '(Skip: this step only added <item>.)'."""
    t = re.sub(rf"\s*,?\s*\b(?:and|or)\s+{_QUAL}(?:{rx.pattern})", "", text, flags=re.I)  # 'pepper and salt'
    t = re.sub(rf"\b{_QUAL}(?:{rx.pattern})\s*(?:,|\band\b|\bor\b)\s*", "", t, flags=re.I)  # 'salt, pepper' / 'salt and pepper'
    if rx.search(t):  # still there: drop the sentences that mention it
        t = " ".join(s for s in re.split(r"(?<=[.!?])\s+", t) if not rx.search(s))
    return t.strip() or f"(Skip: this step only added {item}.)"
