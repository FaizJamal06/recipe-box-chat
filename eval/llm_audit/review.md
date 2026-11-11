## Review notes (hand-written)

### Unknown is not safe

A recipe passes "no T" silently only if every ingredient is verified: its canonical is known (a native vocab
canonical, ≥ 5 valid recipes, not reached via the suffix fallback) or the line scanner explicitly cleared T
(a `free_if` / `except` phrase such as "dairy-free" or "rice noodles"). An "or" option only counts if it is itself
verified. Everything else goes to the `unverified` table: lenient mode shows the recipe with ⚠ "1 ingredient
couldn't be verified: '<line>'", strict mode excludes it. See `backend/app/safety.py`.

I measured a looser reading first ("recognised" = any lexicon keyword anywhere in the option's name): 18% of
recipes unverified instead of ~30%. I rejected it because it repeats the original bug in a new form: "jerk chicken
marinade" would count as verified soy-free just because "chicken" is a known word.

### Canonical audit: what changed

3,000 most common canonicals, 30 calls of 100 (21 retries on 503 / timeouts), cached. Before the fixes: 723
(canonical, tag) disagreements: 497 "LLM says contains, we say nothing", 192 "LLM contains, we may_contain",
29 possible over-tags, 5 level differences. Fixed in `tags.yaml`:

- Real misses: yukon gold / russet (root_veg), thigh / drumstick / breast / wing / neck / shoulder / bone / roast /
  filet mignon / soppressata (meat), swiss, crema, bocconcini, boursin, pepper jack, sherbet (dairy), lemon curd
  (egg + dairy), angel food cake, crepe (egg), toast, pie, crostini, pumpernickel, cupcake, brownie, biscotti, wafer,
  gingersnap, baking mix, french-fried onion, malted milk (gluten), amaretti (tree nut + gluten), imitation crabmeat
  (fish), tentacle (shellfish), fermented black bean (soy), port, campari and 20 wine names (alcohol), mixed
  vegetable, coleslaw mix, pesto, pico de gallo, kimchi, harissa, aioli (root_veg).
- Label-dependent products now warn (may_contain) instead of passing silently: chocolate / candy / cooking spray
  (soy lecithin), ice cream, gelato, fresh-pasta shapes, ravioli, tortellini, cakes, creamy dressings (egg), cakes,
  biscuits, crescent rolls, pie shells, naan (dairy), oyster / barbecue / steak sauce, soup mixes, gochujang
  (gluten), hoisin (sesame), extracts and dijon (alcohol), tapenade (fish), and onion/garlic-based sauces,
  seasonings and sausages (root_veg, for the Jain preset).
- Over-tags fixed: sherry wine vinegar and scotch bonnet (not alcohol), tuna / salmon / swordfish / halibut steak and
  steak sauce / seasoning / spice (not meat), cream sherry and marshmallow cream (not dairy), bean thread / rice
  stick noodles, bread machine / cake yeast, bread-and-butter pickles (not gluten), crab boil seasoning (not
  shellfish); crisp rice cereal and corn flakes downgraded to gluten may_contain (barley malt).
- New guards found while adding words: dark/medium/french roast coffee, wing sauce (not meat), swiss chard (not
  dairy), pie filling and pumpkin / apple pie spice (not gluten), cake flour (not egg/dairy), cream of tartar.

Kept on purpose (the LLM disagrees, the rule stays; these rows remain in the table below):

- root_veg on peppers, chiles, squash, pumpkin, celery salt, fennel: not root vegetables.
- gluten on whiskey / bourbon: distilled spirits are gluten-free.
- soy on vegetable oil and oil brands: highly refined soybean oil is exempt from allergen labelling, and tagging
  "vegetable oil" would flag ~20k recipes.
- alcohol on ginger beer / root beer; shellfish on oyster crackers and cocktail sauce: not present.
- water chestnut and arrowroot in root_veg: kept (stricter is safer for the Jain preset).
- Many compound products are may_contain rather than contains (recipes and brands vary): they warn in lenient mode
  and are excluded in strict mode, so the disagreement is about the label, not about safety.

### Measured accuracy: hand check of the first pass (current lexicon, before the last fixes)

Silent misses (we neither tagged nor warned), 10 in 150 recipes:

- alcohol `epi:TKy.nrnD/z8pz5NZTM.DZNrJ56sslEO`: "claret or other dry red wine". Claret was a known canonical without
  an alcohol tag, so it "verified" the alternative. **Real miss, fixed** (claret + 13 more wine names). This is the
  limit of "known = verified": it is only as good as the lexicon, which is what this audit is for.
- peanut `fn:l2MErOvH.SuN6A33BTwQVGwRdFM9xgu` ("peanut or canola oil") and gluten `epi:c95XyPAja4guRxRCKrfAl6zGNansv96`
  ("white spelt or ground millet flour"): the LLM ignored the "or" rule; both recipes can be made safely. Correct.
- root_veg ×7 (`ar:HswoevEfp6JuiSm.DfRg/U6lXqllzSy`, `ar:V6chpgzjEhxhTSYvzzjql1nTt30/TGS`,
  `ar:ikN/AHjSjpLyZWcnJIzJS9QfulCsVfy`, `ar:v5GP.yKm2/BeIgrUkfZ145KomocsxWu`, `ar:v6ejpSAqsUko/q8ZkWRXk8BhY/GfBgW`,
  `epi:5oCSyt9tTxFzDmWmVHGx2CgjnRyCKTO`, `fn:XegvIjdiLw5geE8Yo.MEkV4lX9XAGzy`): no onion, garlic or root vegetable in
  the lines (oats + apple, banana bread, butternut squash, asafoetida, orzo salad, pie dough). LLM errors.

False alarms (we say contains, the LLM says no), checked: "steak spice seasoning" (meat) was real and is fixed;
the rest are LLM errors (bacon and chicken breast are meat, andouille is pork, soy sauce contains wheat, walnut
oil is a tree nut).

### How to read the accuracy table

The only real silent miss the sample found (claret, alcohol: 1 of 26 = 3.8% on the first pass) is fixed in this
build, so the after-review column is 0 everywhere. That is evidence, not proof: 150 recipes give few positives for
some tags (fish 5, sesame 5, peanut 6, soy 8, gelatin 0), so a 0% there says little. The canonical audit above covers
those tags much more broadly. Re-run `python scripts/llm_audit.py sample --n 300` with a larger sample to tighten it.
