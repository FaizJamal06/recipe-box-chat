"""Ingredient line -> structured parts; the single source of truth for canonicalization (PRD 4.5).

- A line can hold several required items ("salt and pepper") with alternatives ("butter or margarine"):
  parse_line returns one ParsedLine per item, each with its alternatives (ingest rows share line_no, alt_group).
- `canonical` = what product it is (matching); `tags` = what it contains (hard constraints), computed from the
  name before any vocab fallback ("vegan butter" never becomes dairy); line_tags() scans the whole line too.
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


def _alt(words) -> str:
    """Regex alternation, longest first so multi-word phrases win; spaces match any whitespace."""
    return "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in sorted(set(words), key=lambda w: (-len(w), w)))


_UNITS, _SYN, _FAM, _TAGS = (yaml.safe_load((LEX / f"{n}.yaml").read_text(encoding="utf-8"))
                             for n in ("units", "synonyms", "families", "tags"))
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
_FOR = re.compile(r"\s+for\s+[a-z _'-]*(?=,|$)")  # 'buttermilk for brushing' names buttermilk, not 'for brushing'
_UNIT_WORD = re.compile(rf"\b(?:{_alt(_UNIT_OF)})\b")
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
                "schnapps", "bitters", "series", "species", "herbes", "fries", "lees", "gras"}
_DECEPTIVE = set(_SYN["deceptive_heads"])
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
    not_food: bool = False  # equipment / serving note ('1 9-inch skillet', 'Special equipment: ...')

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
    return s.endswith(":") or (bool(re.fullmatch(r"for (?:the )?[a-z ,&-]+", s)) and len(s.split()) <= 5)


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
    """Synonym map applied to the name as written, then to its singular form; the result is always singular
    ('peanuts' and 'salted peanuts' -> 'peanut'), so ingest and user input land on the same canonical."""
    return singular(SYNONYMS.get(name) or SYNONYMS.get(singular(name)) or name)


def suffix_match(key: str, vocab) -> str | None:
    """Longest word-suffix of `key` that is in `vocab` (head-final English: 'boneless pork loin' -> 'pork loin').
    Guards: never a deceptive bare head (butter, milk, cheese, sauce... from synonyms.yaml), and the suffix
    may lose tags but never add one, so 'apple butter' / 'oat milk' / 'vegan cheese' keep their own name."""
    words, have = key.split(), {t for t, _ in tags_for(key)}
    for i in range(1, len(words)):
        cand = synonym(" ".join(words[i:]))
        if cand in vocab and cand not in _DECEPTIVE and {t for t, _ in tags_for(cand)} <= have:
            return cand
    return None


@lru_cache(maxsize=100_000)
def tags_for(name: str) -> tuple:
    """((tag, level), ...) per lexicon/tags.yaml rules; equipment masked first ('cookie cutter' is not gluten)."""
    out, name, hit = [], _NOT_FOOD.sub(" ", name), lambda rx, s: bool(rx and rx.search(s))
    for tag, (free, exc, contains, may, down, whole_c, whole_m) in TAG_RE.items():
        t = exc.sub(" ", name) if exc else name  # *_whole lists are matched before this mask: 'peanut butter cup'
        d = down.sub(" ", t) if down else t  # downgrade phrases ('soba noodle') cap the level at may_contain
        if hit(free, name):
            continue
        if hit(whole_c, name) or (not hit(whole_m, name) and hit(contains, d)):
            out.append((tag, "contains"))
        elif hit(whole_m, name) or hit(may, t) or hit(down, t):
            out.append((tag, "may_contain"))
    return tuple(out)


def _word_re(words, edge=(r"\b", r"\b")) -> re.Pattern | None:
    """Whole-word regex for the words and their singulars, allowing a plural s/es; None for an empty list."""
    words = set(words) | {singular(w) for w in words}
    return re.compile(rf"{edge[0]}(?:{_alt(words)})(?:e?s)?{edge[1]}") if words else None


# hyphen-aware ('pan-fried' stays); breads named 'pan ...' are food ('pan dulce', 'pan de mie')
_NOT_FOOD = _word_re(_TAGS.pop("not_food"), (r"(?<![\w-])", r"(?![\w-]|\s+(?:dulce|de\s+(?:mie|sal|muerto|bono)))"))
TAG_RE = {t: tuple(_word_re(d.get(k) or []) for k in ("free_if", "except", "contains", "may_contain", "downgrade",
                                                       "contains_whole", "may_contain_whole"))
           for t, d in _TAGS.items()}
# 'Caramel Mousse, recipe follows': a sub-recipe whose components are listed as their own lines
_SUBRECIPE = re.compile(r"\brecipes?\s+follows?\b|\(see recipe\)|\bsee recipe (?:below|above)\b")
# families.yaml -> {name suffix: family}. Family names and members map to the family, `broad` entries to
# themselves (their own group), `exclude` entries to None (the canonical stands alone). Names singularized.
_GROUP = {singular(m): singular(f) for f, d in _FAM.items() for m in [f, *(d.get("members") or [])]}
for _b in (b for d in _FAM.values() for b in d.get("broad") or []):
    _GROUP.setdefault(singular(_b), singular(_b))
_GROUP.update({singular(x): None for d in _FAM.values() for x in d.get("exclude") or []})
BROAD = {singular(f): sorted({singular(b) for b in d.get("broad") or []}) for f, d in _FAM.items()}


@lru_cache(maxsize=100_000)
def family_for(canonical: str) -> str:
    """Family from the longest known suffix: 'lean ground beef' -> beef, 'light sour cream' -> itself."""
    words = canonical.split()
    for i in range(len(words)):
        suf = " ".join(words[i:])
        if suf in _GROUP:
            return _GROUP[suf] or canonical
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


def _opts(part: str) -> list[Name]:
    """'butter or margarine' -> [butter, margarine]. Drops the part's own leading unit ('+ 1 tablespoon water';
    digits are gone already)."""
    return [n for n in (_name(_UNIT.sub("", o.strip(), count=1) or o) for o in _OR.split(part)) if n]


def _items(rest: str) -> tuple[list, list | None]:
    """(default, comma_split), each item = [primary, *alternatives]. default: first comma segment naming
    something ('onion, finely chopped' -> onion). comma_split: every part of a ', ... and ...' line, else None;
    parse_line uses it only when every part is a known canonical ('onion, peeled and chopped' stays one item)."""
    rest = _KEEP.sub(lambda m: re.sub(r"\s+", "_", m.group(0)), rest).replace("and/or", " or ")
    segs = rest.split(",")
    default = next((its for seg in segs if (its := [o for p in _AND.split(seg) if (o := _opts(p))])), [])
    split = None
    if len(segs) > 1 and _AND.search(rest[rest.index(","):]):
        parts = [_opts(p) for seg in segs for p in _AND.split(re.sub(r"^\s*and\s+", "", seg)) if p.strip()]
        split = parts if len(parts) > 1 and all(parts) else None
    return default, split


@lru_cache(maxsize=50_000)
def _parse(raw: str) -> tuple:
    """Cached core of parse_line (most lines repeat: '1 teaspoon salt') -> (items, line_tags, comma_split)."""
    s = clean_text(raw)
    if not s:
        return (), (), None
    if is_header(s):
        return (ParsedLine(raw, is_header=True),), (), None
    if _SUBRECIPE.search(s):  # kept as a reference line, not an ingredient; its words still count for tags
        return (ParsedLine(raw, is_header=True),), tags_for(_PAREN.sub(" ", s)), None
    if ":" in s:  # 'Garnish: chopped parsley' -> parse the part after the label
        label, s = s.split(":", 1)
        if "equipment" in label:  # 'Special equipment: ...'
            return (ParsedLine(raw, not_food=True),), (), None
    s, masked = _NOT_FOOD.subn(" ", s)  # equipment and serving notes never name an ingredient
    s, qty, qty_range, unit = s.strip(), None, None, None
    m = _QTY.match(s)
    if m:
        lo, hi = _num(m.group(1)), (_num(m.group(2)) if m.group(2) else None)
        qty, qty_range = ((lo + hi) / 2, (lo, hi)) if hi is not None else (lo, None)
        s = s[m.end():]
    size = _SIZE.match(s)
    if size:
        s = s[size.end():]
    notes = _UNIT_WORD.sub(" ", " ".join(_PAREN.findall(s)))  # '(or butter)' counts for tags, '(2 ribs)' not
    s = _PAREN.sub(" ", s).strip()
    m = _UNIT.match(s)
    if m and s[m.end():].strip():  # '4 ribs' alone: keep 'ribs' as the name, not as a unit
        unit, s = _UNIT_OF[re.sub(r"\s+", " ", m.group(1))], s[m.end():]
    s = _PLUS.sub("", s)  # '1 cup plus 2 tablespoons flour' (shortcut: the 'plus' amount is ignored)
    if size:  # 2 x (15 ounce) cans -> 30 ounce
        su = _UNIT_OF[re.sub(r"\s+", " ", size.group(2))]
        if UNIT_FAMILY[su] in ("mass", "volume"):
            qty, unit, qty_range = (qty or 1.0) * _num(size.group(1)), su, None
    line_tags = tags_for(f"{s} {notes}")  # keyword scan of everything after the amount (all comma parts)
    s = _FOR.sub("", _PUNCT.sub(" ", _DIGIT_TOKEN.sub(" ", s)))
    head = (qty, qty_range, unit, UNIT_FAMILY.get(unit))  # first item only; the others' amounts are unknown
    mk = lambda items: tuple(ParsedLine(raw, *(head if i == 0 else (None,) * 4), o[0], tuple(o[1:]))
                             for i, o in enumerate(items))
    default, split = _items(s)
    if masked and not default:  # '1 9-inch skillet', 'Toothpicks', 'Optional, for serving'
        return (ParsedLine(raw, not_food=True),), (), None
    return mk(default), line_tags, (mk(split) if split else None)


def line_tags(raw: str) -> tuple:
    """Tags from a keyword scan of the whole line (negations honoured): catches 'salt, pepper and butter'."""
    return _parse(raw)[1]


def comma_split(raw: str, vocab) -> list[ParsedLine] | None:
    """The comma-list reading of `raw` ('salt, pepper and paprika' -> 3 items) if every option is in vocab."""
    split = _parse(raw)[2]
    return list(split) if split and all(o.canonical in vocab for p in split for o in p.options) else None


def parse_line(raw: str, vocab=None) -> list[ParsedLine]:
    """Raw line -> one ParsedLine per required item. With a vocab: comma lists of known canonicals split, and an
    unknown canonical falls back to its longest safe in-vocab suffix ('heritage pork loin' -> 'pork loin')."""
    if vocab is None:
        return list(_parse(raw)[0])
    out = comma_split(raw, vocab) or list(_parse(raw)[0])
    fix = lambda n: n if n.canonical in vocab or not (c := suffix_match(n.canonical, vocab)) \
        else Name(n.clean, c, family_for(c), n.tags)
    return [ParsedLine(p.raw, p.qty, p.qty_range, p.unit, p.unit_family, fix(p.name),
                       tuple(fix(a) for a in p.alternatives), p.is_header) if p.name else p for p in out]


def normalize(text: str, vocab=None) -> list[str]:
    """Canonicals named in free text, e.g. user input ('peanuts' -> ['peanut']); same path as ingest."""
    return [p.name.canonical for p in parse_line(text, vocab) if p.name]
