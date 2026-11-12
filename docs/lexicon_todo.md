# Lexicon todo

Known lexicon issues, batched. Each one gets fixed together with a regression test in
`backend/tests/test_normalize.py`, and they all ship in one DB rebuild. Don't rebuild for a single item.

Format: `- [area] example line -> what happens now -> what it should do`

## Open

- [families] "vegan cheese", "dairy-free cheese" -> family cheese -> standalone (tags are already right)
- [families] "oat milk" -> family milk; "coconut flour", "chickpea flour" -> family flour -> standalone, or broad only
- [families] "sun-dried tomatoes in oil" -> standalone canonical -> map to sun-dried tomato
- [synonyms] "finlandia butter", "borden butter", "english butter" -> unmapped (the deceptive-head guard keeps
  them out of butter) -> add synonyms to butter
- [parse] "1 (3-pound chicken)", "red onion: 1, julienned" -> parse misses -> parse them
- [parse] storage-guide pseudo-lines ("Tomatoes--12 to 18 months") -> junk names ("to month", "year") -> drop
  them as not_food
- [parse] units/qty glued into names: "pinch salt" (100 recipes), "teaspoon salt", "cup water", "grinds black
  pepper", "egg tablespoon water" -> own canonicals, so they are not pantry staples in matching -> strip the unit
- [tags] no sugar tag: "no sugar" is an ingredient exclusion (sugar family + broad + text mention), so marshmallow,
  caramel, chocolate, candy still pass -> consider a `sugar` tag (contains: sweetened products) (seen in demo 6)
- [parse] branded compound lines ("Progresso Recipe Starters creamy roasted garlic ... cooking sauce") -> one
  long canonical, garlic not detected (search exclusions now also check FTS word mentions) -> head-noun rule
- [exclusion] the mention net's safe phrases are per recipe (FTS NOT): a recipe with "cream of tartar" AND a stray
  unparsed "cream" mention elsewhere slips past the net (parsed cream lines are still caught by family/canonical)
- [families] audit (scripts/audit_tags.py) leftovers, all reviewed, tags are right but the family is loose:
  "pork steak", "pork shoulder steak" in family beef (steak suffix); "monterey jack cheese jalapeno" in chili pepper,
  "condensed cream of mushroom soup garlic" in garlic, "egg tablespoon milk" in milk (glued compound lines, see the
  units/qty item above); "turkey italian sausage" in italian sausage (poultry, no pork: correct)
- [families] audit, intended differences (kept): gluten-free flours (rice/corn/coconut/chickpea/tapioca/millet/...)
  in family flour; plant milks in milk; vegan cream cheese; turkey bacon/ham; chicken/turkey sausage; generic
  "sausage" pork = may_contain; ravioli/tortellini dairy = may_contain (fillings vary); buckwheat flour gluten =
  may_contain; peanut/walnut/hazelnut oil keep their nut tag; malt vinegar gluten; egg pasta egg

- [audit] left after the 2026-11-12 rebuild (docs/tag_audit.md has the full list): "pie weight" is equipment
  (gluten over-tag, should be not_food); "vanilla wafer" dairy/egg may_contain; "peanut butter chip" dairy (the
  "peanut butter" dairy exception masks the may_contain word); "rum extract" alcohol (its except entry beats
  may_contain); "crisp" (fruit-crisp topping) gluten/dairy may_contain; "smoked sausage" poultry may_contain
- [unverified] ~30% of valid recipes have at least one ingredient no tag could be verified for (long-tail compound
  names: "small-diced yellow onion", "havarti dill cheese", "jerk sauce"). Strict mode excludes them by design.
  Shrinking it honestly = more synonyms/descriptors so those names land on known canonicals, not a looser rule.
  Note-like lines ("Ingredient info: ... available at ...", "*Also known as ...") are ~2% of them: make them not_food.

- [substitution, from M5] (no DB rebuild in M5; roles.yaml / candidates.yaml are read at runtime)
  - "aquafaba" is in 3 recipes (< vocab_min 5) -> unknown canonical, so it is rejected as unverified for egg whites
    -> lower the bar for curated candidates, or add aquafaba with tags (egg-free, legume) and accept it
  - compound lines "Butter and maple syrup", "Salt and pepper" -> one line, so removing butter drops the syrup in the
    adapted list -> split "X and Y" lines into two parsed items
  - roles.yaml has no saffron / chicken / meat entries -> role "unknown" (model guess only inside an adaptation)
    -> add roles for the common proteins and spices
  - "pancake mix", "cake mix", "baking mix" are dairy/egg may_contain -> correct, but common in demos; consider
    "may contain" wording on the gate rather than a hard ✗ when the line is a labelled mix

## Done

- 2026-11-12 [safety] unknown is not safe (safety.py, `unverified` table); soy, sesame, honey, gelatin, alcohol,
  root_veg tags; diet presets (lexicon/diets.yaml); LLM canonical audit + sample accuracy (docs/tag_audit.md) and the
  fixes it found (see eval/llm_audit/review.md)

- 2026-11-10 [tags] wheat pasta / wheat products all gluten:contains (bucatini, cavatappi/cavatapi, orecchiette,
  linguini, spaghettini, lo mein, atta, maida, sooji, roti, ...); rice/corn/chickpea/lentil/quinoa pasta and noodles
  exempt; buckwheat/soba capped at may_contain via the new `downgrade` list. Root cause of the leak: "penne or
  bucatini" was only `alt` because bucatini had no tag.
- 2026-11-10 [tags] "cannelloni bean" not gluten; "beef steak tomato" not meat; "crisco butter shortening" not dairy;
  ravioli/tortellini dairy may_contain (from the family-tag audit)
- 2026-11-10 [exclusion] "no cream" keeps cream of tartar / coconut cream, "no butter" keeps peanut butter etc.
  (synonyms.yaml `mention_safe`)
- 2026-11-10 [not_food] "pan dulce", "pan de mie", "pan de sal" are breads, not pans
- 2026-11-10 [parse] "X, recipe follows" lines are sub-recipe references: stored, not counted as ingredients,
  their words still tag the recipe
