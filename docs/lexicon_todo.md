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
- [not_food] "pan dulce", "pan de mie" -> "pan" is masked as equipment -> protect them via keep_whole
- [parse] "1 (3-pound chicken)", "red onion: 1, julienned" -> parse misses -> parse them
- [parse] storage-guide pseudo-lines ("Tomatoes--12 to 18 months") -> junk names ("to month", "year") -> drop
  them as not_food
- [parse] units/qty glued into names: "pinch salt" (100 recipes), "teaspoon salt", "cup water", "grinds black
  pepper", "egg tablespoon water" -> own canonicals, so they are not pantry staples in matching -> strip the unit
- [tags] no sugar tag: "no sugar" is an ingredient exclusion (sugar family + broad + text mention), so marshmallow,
  caramel, chocolate, candy still pass -> consider a `sugar` tag (contains: sweetened products) (seen in demo 6)
- [parse] branded compound lines ("Progresso Recipe Starters creamy roasted garlic ... cooking sauce") -> one
  long canonical, garlic not detected (search exclusions now also check FTS word mentions) -> head-noun rule
- [exclusion] KNOWN OVER-EXCLUSION: "no cream" drops "cream of tartar" (and coconut cream / cream of mushroom)
  recipes via the FTS mention net in search.hard_where (canonical/family path is fine) -> per-word safe phrases,
  e.g. FTS `"cream" NOT "cream of tartar"` (xfail test: test_exclusions.py::test_no_cream_keeps_cream_of_tartar).
  "no egg" vs eggplant and "no salt" vs unsalted butter are correct (porter tokens differ), tested.

## Done
