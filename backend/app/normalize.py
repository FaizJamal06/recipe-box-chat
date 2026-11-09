"""Ingredient line -> structured parts; the single source of truth for canonicalization (PRD 4.5).

Why it is shaped like this:
- One raw line can hold several required ingredients ("salt and pepper") and alternatives
  ("butter or margarine"). So parse_line returns a list of ParsedLine, one per required item, and
  each item carries its alternatives. ingest.py stores them as rows sharing (line_no, alt_group).
- `canonical` = what product it is (matching). `tags` = what it contains (hard constraints).
  Tags are computed from the name before any vocabulary fallback, so "vegan butter" never turns into dairy.
- All word lists live in lexicon/*.yaml so they can be reviewed and edited without touching code.
"""
import re
import unicodedata
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import yaml

LEX = Path(__file__).resolve().parent / "lexicon"
LEVELS = {None: 0, "may_contain": 1, "contains": 2}


def _load(name: str) -> dict:
    """Read one lexicon YAML file."""
    return yaml.safe_load((LEX / f"{name}.yaml").read_text(encoding="utf-8"))


def _alt(words) -> str:
    """Regex alternation, longest first so multi-word phrases win; spaces match any whitespace."""
    return "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in sorted(set(words), key=len, reverse=True))


_UNITS, _SYN, _FAM, _TAGS = _load("units"), _load("synonyms"), _load("families"), _load("tags")
UNIT_FAMILY = {u: d["family"] for u, d in _UNITS.items()}
_UNIT_OF = {a: u for u, d in _UNITS.items() for a in d["aliases"]}
SYNONYMS: dict[str, str] = _SYN["synonyms"]
_CONTAINERS = [a for a, u in _UNIT_OF.items() if UNIT_FAMILY[u] == "container"]

NUM = r"(?:\d+\s+\d+/\d+|\d+/\d+|\d*\.\d+|\d+)"
_QTY = re.compile(rf"^(?:about\s+|approx\.?\s+|approximately\s+)?({NUM})(?:\s*(?:-|to|or)\s*({NUM}))?\s*")
_UNIT = re.compile(rf"^(?:(?:small|medium|large)\s+)?({_alt(_UNIT_OF)})\.?(?=\s|$)\s*(?:of\s+)?")
# "1 (15 ounce) can", "2 15-ounce cans": a size in front of a container unit is per-container.
_SIZE = re.compile(rf"^\(?\s*({NUM})\s*-?\s*({_alt(_UNIT_OF)})\.?\s*\)?\s*(?=(?:{_alt(_CONTAINERS)})\b)")
_PLUS = re.compile(rf"^plus\s+{NUM}\s*(?:{_alt(_UNIT_OF)})?\.?\s+")
_PAREN = re.compile(r"\([^)]*\)?")
_DIGIT_TOKEN = re.compile(r"\S*\d\S*")
_PUNCT = re.compile(r"[^a-z\s,/&+_-]")
_DESCRIPTORS = re.compile(rf"(?<![\w-])(?:{_alt(_SYN['descriptors'])})(?![\w-])")
_KEEP = re.compile(rf"(?<![\w-])(?:{_alt(_SYN['keep_whole'])})(?![\w-])")
_AND = re.compile(r"\s+(?:and|plus)\s+|\s*[&+]\s*")
_OR = re.compile(r"\s+or\s+|\s*/\s*")
_FRACTIONS = {"½": "1/2", "⅓": "1/3", "⅔": "2/3", "¼": "1/4", "¾": "3/4", "⅕": "1/5", "⅖": "2/5", "⅗": "3/5",
              "⅘": "4/5", "⅙": "1/6", "⅚": "5/6", "⅛": "1/8", "⅜": "3/8", "⅝": "5/8", "⅞": "7/8"}
# Words that only look plural. Plural canonicals ("black beans") come from synonyms.yaml instead.
_NO_SINGULAR = {"molasses", "couscous", "hummus", "asparagus", "swiss", "grits", "oats", "greens", "brussels",
                "schnapps", "bitters", "series", "species", "herbes", "fries", "lees"}
_IRREGULAR = {"leaves": "leaf", "halves": "half", "loaves": "loaf", "cookies": "cookie", "pies": "pie",
              "brownies": "brownie", "chilies": "chili", "chillies": "chili", "veggies": "veggie",
              "smoothies": "smoothie", "calories": "calorie", "knives": "knife"}


@dataclass(frozen=True, slots=True)
class Name:
    """One option for an ingredient: cleaned text, canonical product, its family and contains-tags."""
    clean: str
    canonical: str
    family: str
    tags: tuple = ()  # ((tag, level), ...) so the object stays hashable/cacheable


@dataclass(frozen=True, slots=True)
class ParsedLine:
    """One required item of a raw line. qty is the mean of a range; qty_range keeps (lo, hi)."""
    raw: str
    qty: float | None = None
    qty_range: tuple | None = None
    unit: str | None = None
    unit_family: str | None = None
    name: Name | None = None
    alternatives: tuple = ()
    is_header: bool = False

    @property
    def options(self) -> tuple:
        """Primary name followed by its alternatives (any one satisfies the item)."""
        return ((self.name,) if self.name else ()) + self.alternatives


def clean_text(raw: str) -> str:
    """Strip ADVERTISEMENT, accents, apostrophes; lowercase; unicode fractions -> ' 1/2'; squeeze spaces."""
    s = raw.replace("ADVERTISEMENT", "").replace("⁄", "/")
    for ch, frac in _FRACTIONS.items():
        s = s.replace(ch, f" {frac}")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return " ".join(s.replace("'", "").split())


def is_header(s: str) -> bool:
    """Section header such as 'For the sauce:' or 'For the topping' (expects clean_text output)."""
    if s.endswith(":"):
        return True
    return bool(re.fullmatch(r"for (?:the )?[a-z ,&-]+", s)) and len(s.split()) <= 5


def _num(t: str) -> float:
    """'1 1/2' -> 1.5, '3/4' -> 0.75, '.5' -> 0.5."""
    try:
        return float(sum(Fraction(p) for p in t.split()))
    except (ValueError, ZeroDivisionError):
        return 0.0


def singular(name: str) -> str:
    """Singularize the last word only (the head noun): 'cherry tomatoes' -> 'cherry tomato'."""
    head, _, w = name.rpartition(" ")
    if w in _IRREGULAR:
        w = _IRREGULAR[w]
    elif len(w) > 3 and w not in _NO_SINGULAR and not w.endswith(("ss", "us", "is")):
        if w.endswith("ies"):
            w = w[:-3] + "y"
        elif w.endswith(("oes", "ches", "shes", "xes", "sses", "zes")):
            w = w[:-2]
        elif w.endswith("s"):
            w = w[:-1]
    return f"{head} {w}" if head else w


def synonym(name: str) -> str:
    """Synonym map applied to the name as written, then to its singular form."""
    return SYNONYMS.get(name) or SYNONYMS.get(singular(name)) or singular(name)


def suffix_match(key: str, vocab) -> str | None:
    """Longest word-suffix of `key` that is in `vocab` (head-final English: 'boneless pork loin' -> 'pork loin').
    Guard: the suffix may lose tags but never add one, so 'cashew butter' / 'vegan cheese' / 'hemp milk'
    never become butter / cheese / milk."""
    words, have = key.split(), {t for t, _ in tags_for(key)}
    for i in range(1, len(words)):
        cand = synonym(" ".join(words[i:]))
        if cand in vocab and {t for t, _ in tags_for(cand)} <= have:
            return cand
    return None


@lru_cache(maxsize=100_000)
def tags_for(name: str) -> tuple:
    """((tag, level), ...) for one ingredient name, from lexicon/tags.yaml (see the rules there)."""
    out = []
    if _NOT_FOOD.search(name):
        return ()
    for tag, (free, exc, contains, may) in _TAG_RE.items():
        if free and free.search(name):
            continue
        t = exc.sub(" ", name) if exc else name
        if contains.search(t):
            out.append((tag, "contains"))
        elif may and may.search(t):
            out.append((tag, "may_contain"))
    return tuple(out)


def _word_re(words) -> re.Pattern | None:
    """Whole-word regex allowing a plural s/es; None for an empty list."""
    return re.compile(rf"\b(?:{_alt(words)})(?:e?s)?\b") if words else None


_NOT_FOOD = _word_re(_TAGS.pop("not_food"))
_TAG_RE = {t: tuple(_word_re(d.get(k) or []) for k in ("free_if", "except", "contains", "may_contain"))
           for t, d in _TAGS.items()}
_FAMILY_OF = {m: f for f, d in _FAM.items() for m in d.get("members") or []}
_BROAD = {f: set(d.get("broad") or []) for f, d in _FAM.items()}


@lru_cache(maxsize=100_000)
def family_for(canonical: str) -> str:
    """Loose group (lexicon/families.yaml): explicit member, else head-noun suffix, else itself."""
    if canonical in _FAMILY_OF:
        return _FAMILY_OF[canonical]
    for fam, broad in _BROAD.items():
        if (canonical == fam or canonical.endswith(" " + fam)) and canonical not in broad:
            return fam
    return canonical


def _name(text: str) -> Name | None:
    """Words (protected phrases joined by '_') -> Name. Synonyms are tried before and after descriptor drop."""
    full = " ".join(text.replace("_", " ").split()).strip(" -")
    if not full:
        return None
    if full in SYNONYMS or singular(full) in SYNONYMS:
        key = synonym(full)
        clean = " ".join(_DESCRIPTORS.sub(" ", text).replace("_", " ").split()).strip(" -") or full
    else:
        clean = " ".join(_DESCRIPTORS.sub(" ", text).replace("_", " ").split()).strip(" -")
        if not clean:
            return None
        key = synonym(clean)
    return Name(clean, key, family_for(key), tags_for(key))


def _items(rest: str) -> list[list[Name]]:
    """'salt and pepper, to taste' -> [[salt], [black pepper]]; 'butter or margarine' -> [[butter, margarine]]."""
    rest = _KEEP.sub(lambda m: re.sub(r"\s+", "_", m.group(0)), rest)
    rest = rest.replace("and/or", " or ")
    for seg in rest.split(","):  # first comma segment that still names something ('boneless, skinless chicken')
        items = []
        for part in _AND.split(seg):
            # '1 egg + 1 tablespoon water': digits are gone already, drop the part's own leading unit
            opts = [n for n in (_name(_UNIT.sub("", o.strip(), count=1) or o) for o in _OR.split(part)) if n]
            if opts:
                items.append(opts)
        if items:
            return items
    return []


@lru_cache(maxsize=50_000)
def _parse(raw: str) -> tuple[ParsedLine, ...]:
    """Cached core of parse_line (most lines repeat: '1 teaspoon salt')."""
    s = clean_text(raw)
    if not s:
        return ()
    if is_header(s):
        return (ParsedLine(raw, is_header=True),)
    if ":" in s:  # 'Garnish: chopped parsley' -> parse the part after the label
        s = s.split(":", 1)[1].strip()
    qty = qty_range = unit = None
    m = _QTY.match(s)
    if m:
        lo, hi = _num(m.group(1)), (_num(m.group(2)) if m.group(2) else None)
        qty, qty_range = ((lo + hi) / 2, (lo, hi)) if hi is not None else (lo, None)
        s = s[m.end():]
    size = _SIZE.match(s)
    if size:
        s = s[size.end():]
    s = _PAREN.sub(" ", s).strip()
    m = _UNIT.match(s)
    if m and s[m.end():].strip():  # '4 ribs' alone: keep 'ribs' as the name, not as a unit
        unit, s = _UNIT_OF[re.sub(r"\s+", " ", m.group(1))], s[m.end():]
    s = _PLUS.sub("", s)  # '1 cup plus 2 tablespoons flour' (ponytail: the 'plus' amount is ignored)
    if size:  # 2 x (15 ounce) cans -> 30 ounce
        su = _UNIT_OF[re.sub(r"\s+", " ", size.group(2))]
        if UNIT_FAMILY[su] in ("mass", "volume"):
            qty, unit, qty_range = (qty or 1.0) * _num(size.group(1)), su, None
    s = _PUNCT.sub(" ", _DIGIT_TOKEN.sub(" ", s))
    uf = UNIT_FAMILY.get(unit)
    return tuple(ParsedLine(raw, qty, qty_range, unit, uf, opts[0], tuple(opts[1:])) for opts in _items(s))


def parse_line(raw: str, vocab=None) -> list[ParsedLine]:
    """Raw ingredient line -> one ParsedLine per required item ([] for empty/ADVERTISEMENT-only lines).

    vocab: optional set of known canonicals; a canonical outside it falls back to its longest
    in-vocab word suffix ('teriyaki marinade sauce' -> 'sauce' only if that is all we know).
    Tags are not changed by that fallback (they describe the text, not the guess).
    """
    out = list(_parse(raw))
    if vocab is None:
        return out
    fix = lambda n: n if n.canonical in vocab or not (c := suffix_match(n.canonical, vocab)) \
        else Name(n.clean, c, family_for(c), n.tags)
    return [ParsedLine(p.raw, p.qty, p.qty_range, p.unit, p.unit_family, fix(p.name),
                       tuple(fix(a) for a in p.alternatives), p.is_header) if p.name else p for p in out]


# ---- instructions (PRD 4.4) ----
_ABBREV = {"tsp", "tbsp", "tbs", "tbl", "oz", "approx", "f", "c", "lb", "lbs", "pkg", "fl", "qt", "pt", "no",
           "vs", "st", "dr", "mr", "mrs", "e.g", "i.e", "deg", "min", "mins", "hr", "hrs", "in", "ca", "pkgs"}
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def count_sentences(text: str) -> int:
    """Sentences in instructions. Splits on . ! ? + whitespace and newlines, but not after abbreviations
    (tsp., oz., approx., 350 F.) or a bare number ('1. Preheat'); decimals never split (no space after '.')."""
    n = 0
    for seg in (text or "").split("\n"):
        chunks = [c for c in _SENT_SPLIT.split(seg.strip()) if c]
        for i, c in enumerate(chunks):
            last = re.sub(r"[^a-z0-9.]", "", c.rsplit(None, 1)[-1].lower()).rstrip(".")
            if i == len(chunks) - 1 or not (last in _ABBREV or last.replace(".", "").isdigit()):
                n += 1
    return n
