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

## Done
