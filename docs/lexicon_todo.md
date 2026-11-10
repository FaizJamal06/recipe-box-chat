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

## Done

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
