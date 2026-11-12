# Exploratory run: fresh sessions

## banana bread, typos, option switch, forced

**> find a banana bread recipe**

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 21 ms · type=search · total=309

> 🗣 I found 309 recipes for banana bread with your active search filter. Here are a few top choices: Banana Bread French Toast, Chocolate Banana Bread Pudding, Country Banana Bread, Banana Bread - Quick Bread for Machines, and Microwave Tofu Banana Bread. Enjoy exploring these delicious options!

**309 recipes** match _matches 'banana bread'_; showing 10.
_309 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Banana Bread French Toast** `ar:GiHk4/Wm95WTxwkxlmJtSmHUBdpv2La` — 6 ingredients · 2 steps
2. **Chocolate Banana Bread Pudding** `ar:d.BjGek97U5uIyZN4IAbXx7yZMbXNLa` — 7 ingredients · 3 steps
3. **Country Banana Bread** `ar:LCKlIJX8Jjf51FQPJqTQGydT1/m4zRi` — 4 ingredients · 3 steps
4. **Banana Bread - Quick Bread for Machines** `ar:c7DonAWp3sg843C9Gd4NmmcKoKJ6AU2` — 7 ingredients · 3 steps
5. **Microwave Tofu Banana Bread** `ar:5S4TJwjeeH.L/gDoUxUR0jfxC/8Vd4u` — 4 ingredients · 3 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): cache hit | LLM call 2 (voice): cache hit | Voice: ok

---

**> show me the frist one**

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 2 ms · type=recipe

> 🗣 Here is Banana Bread French Toast for your banana bread search. Enjoy preparing this recipe with its six ingredients and two simple steps.

**Banana Bread French Toast** `ar:GiHk4/Wm95WTxwkxlmJtSmHUBdpv2La` — 6 ingredients · 2 steps (opened on the right).

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (planner): cache hit | LLM call 2 (voice): cache hit | Voice: ok

---

**> no eggs in this pls**

`rule parser · high-confidence pattern` · 0 LLM calls · 376 ms · type=substitute

**Banana Bread French Toast** `ar:GiHk4/Wm95WTxwkxlmJtSmHUBdpv2La` · dish: _french toast_ (savory) · compared with 350 title matches (L1), 30 similar recipes (L2), 77,834 savory recipes (L3).
Removing **eggs** (3 eggs) · role: _binding_
1. **flaxseed** (chosen) — **Strong** · 1 of 11 'french toast' recipes without eggs (L1, lift 52.5) · 0 of 6 similar (L2) · 145 of 63,519 savory (L3) · curated: binding · explicit variants: `ar:xUubB0gHLaK9kxzRDjkhG5pXBDClZke`
2. **banana** — **Weak** · 1 of 11 'french toast' recipes without eggs (L1, lift 1.3) · 0 of 6 similar (L2) · 1,013 of 63,519 savory (L3) · curated: binding
3. **chia seed** — **Weak** · 0 of 11 'french toast' recipes without eggs (L1, lift 13.1) · 0 of 6 similar (L2) · 144 of 63,519 savory (L3) · curated: binding
_… 3 more in the Evidence tab._
**Adapted recipe** (side-by-side diff in the Results panel):
- − 3 eggs
- + flaxseed (estimate: 1 tablespoon ground flaxseed + 3 tablespoons water per egg; replaces eggs)
- Prep: Mix the ground flaxseed with 3 tablespoons water per egg and let it thicken for 5 minutes.
- Step 1 (changed): In a shallow bowl, whisk together the flaxseed, sweetened condensed milk and vanilla with a fork. Set aside.
- Step 2 (changed): Melt butter in a large skillet over medium heat. Slice banana bread into 4 thick slices. Dip each slice into the flaxseed mixture, then place in the hot pan. Cook on each side until golden brown. Dust with confectioners' sugar just before serving, if desired.
_Steps rewritten by the model and validated._
**Verified from dataset:**
- flaxseed for eggs: used by 1 of 11 'french toast' recipes without eggs (L1, lift 52.5), 0 of 6 similar recipes (L2) and 145 of 63,519 savory recipes (L3).
- Explicit variants using it: `ar:xUubB0gHLaK9kxzRDjkhG5pXBDClZke`.
**Predicted (not verifiable from recipe text):**
The texture of the french toast may be slightly denser since flaxseed provides a different binding structure than eggs. The taste could feature a mild nutty flavor from the flaxseed. Preparation requires mixing the flaxseed with water prior to combining with the other liquids.
> ✗ **Not safe for your restrictions:** 1 loaf banana bread: may contain egg. Say e.g. 'remove the banana bread too' to replace it as well.
> Allergy note: recipe text can't establish medical safety. Check every label for the allergen and for cross-contamination.

Suggestions: Try option 2 · Also remove banana bread
Trace: LLM call 1 (substitute): cache hit | Voice: template (answer type keeps the template)

---

**> use the second option instead**

`rule parser · high-confidence pattern` · 0 LLM calls · 416 ms · type=substitute

**Banana Bread French Toast** `ar:GiHk4/Wm95WTxwkxlmJtSmHUBdpv2La` · dish: _french toast_ (savory) · compared with 350 title matches (L1), 30 similar recipes (L2), 77,834 savory recipes (L3).
Removing **eggs** (3 eggs) · role: _binding_
1. **flaxseed** — **Strong** · 1 of 11 'french toast' recipes without eggs (L1, lift 52.5) · 0 of 6 similar (L2) · 145 of 63,519 savory (L3) · curated: binding · explicit variants: `ar:xUubB0gHLaK9kxzRDjkhG5pXBDClZke`
2. **banana** (chosen) — **Weak** · 1 of 11 'french toast' recipes without eggs (L1, lift 1.3) · 0 of 6 similar (L2) · 1,013 of 63,519 savory (L3) · curated: binding
3. **chia seed** — **Weak** · 0 of 11 'french toast' recipes without eggs (L1, lift 13.1) · 0 of 6 similar (L2) · 144 of 63,519 savory (L3) · curated: binding
_… 3 more in the Evidence tab._
> No adaptation: the best usable option for eggs is banana (Weak). Say 'adapt it anyway' for a heavily caveated version.

Suggestions: Adapt it anyway · Try option 3
Trace: Voice: template (answer type keeps the template)

---

**> adapt it anyway**

`rule parser · high-confidence pattern` · 0 LLM calls · 405 ms · type=substitute

**Banana Bread French Toast** `ar:GiHk4/Wm95WTxwkxlmJtSmHUBdpv2La` · dish: _french toast_ (savory) · compared with 350 title matches (L1), 30 similar recipes (L2), 77,834 savory recipes (L3).
Removing **eggs** (3 eggs) · role: _binding_
1. **flaxseed** — **Strong** · 1 of 11 'french toast' recipes without eggs (L1, lift 52.5) · 0 of 6 similar (L2) · 145 of 63,519 savory (L3) · curated: binding · explicit variants: `ar:xUubB0gHLaK9kxzRDjkhG5pXBDClZke`
2. **banana** (chosen) — **Weak** · 1 of 11 'french toast' recipes without eggs (L1, lift 1.3) · 0 of 6 similar (L2) · 1,013 of 63,519 savory (L3) · curated: binding
3. **chia seed** — **Weak** · 0 of 11 'french toast' recipes without eggs (L1, lift 13.1) · 0 of 6 similar (L2) · 144 of 63,519 savory (L3) · curated: binding
_… 3 more in the Evidence tab._
**Adapted recipe** (side-by-side diff in the Results panel):
- − 3 eggs
- + banana (estimate: 1/2 mashed banana per egg; replaces eggs)
- Step 1 (changed): In a shallow bowl, whisk together the banana, sweetened condensed milk and vanilla with a fork. Set aside.
- Step 2 (changed): Melt butter in a large skillet over medium heat. Slice banana bread into 4 thick slices. Dip each slice into the banana mixture, then place in the hot pan. Cook on each side until golden brown. Dust with confectioners' sugar just before serving, if desired.
_Steps rewritten by the model and validated._
> ⚠ Heavily caveated: the evidence for this substitute is Weak; treat amounts and method as guesses.
**Verified from dataset:**
- banana for eggs: used by 1 of 11 'french toast' recipes without eggs (L1, lift 1.3), 0 of 6 similar recipes (L2) and 1,013 of 63,519 savory recipes (L3).
**Predicted (not verifiable from recipe text):**
The texture will be softer and less stable due to the weak binding provided by the banana substitute. The flavor profile will gain a distinct fruity sweetness.
> ✗ **Not safe for your restrictions:** 1 loaf banana bread: may contain egg. Say e.g. 'remove the banana bread too' to replace it as well.
> Allergy note: recipe text can't establish medical safety. Check every label for the allergen and for cross-contamination.

Suggestions: Try option 3 · Also remove banana bread
Trace: LLM call 1 (substitute): cache hit | Voice: template (answer type keeps the template)

---

## make it vegan

**> find a pancake recipe**

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 30 ms · type=search · total=866

> 🗣 I found 866 matches for your pancake search. Some top options include 1946 Apple Buckwheat Pancakes, Amish Sourdough Pancakes, and Sausage Pancakes-on-Sticks.

**866 recipes** match _matches 'pancake'_; showing 10.
_866 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **1946 Apple Buckwheat Pancakes** `fn:H449YwkifMLsxY7yHoS5QbzCU1wdecy` — 5 ingredients · 6 steps
2. **Amish Sourdough Pancakes** `ar:qy9TfjYD1KLcpDO57jCkWtUOT9/2pTO` — 3 ingredients · 2 steps
3. **Sausage Pancakes-on-Sticks** `fn:XAWvCYSKqiy.miDM7et4x7GzFLfISJu` — 9 ingredients · 8 steps
4. **Chris Cakes Pancakes** `fn:6bGq5al/DOgEakpsT3FwOaRJEeUGHfy` — 4 ingredients · 3 steps
5. **Fiber One Pancakes** `fn:9j6uWaCLTkZZCiTl7c3NddEKq6g1nmW` — 2 ingredients · 1 step
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): cache hit | LLM call 2 (voice): cache hit | Voice: ok

---

**> show me the first one**

`rule parser · high-confidence pattern` · 0 LLM calls · 1 ms · type=recipe

> 🗣 Here is the first recipe for you. It is called 1946 Apple Buckwheat Pancakes, found using your pancake search.

**1946 Apple Buckwheat Pancakes** `fn:H449YwkifMLsxY7yHoS5QbzCU1wdecy` — 5 ingredients · 6 steps (opened on the right).

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (voice): cache hit | Voice: ok

---

**> make it vegan**

`rule parser · high-confidence pattern` · 1 LLM calls · 1578 ms · type=substitute

> Vegan → no meat, fish, shellfish, gelatin, dairy, eggs, honey.
**1946 Apple Buckwheat Pancakes** `fn:H449YwkifMLsxY7yHoS5QbzCU1wdecy` · dish: _buckwheat pancakes_ (savory) · compared with 14 title matches (L1), 8 similar recipes (L2), 77,834 savory recipes (L3).
Removing **butter** (Butter and maple syrup) · role: _fat, flavor_
1. **vegetable oil** (chosen) — **Strong** · 3 of 8 'buckwheat pancakes' recipes without butter (L1, lift 1.6) · curated: fat
2. **olive oil** — **Weak** · 0 of 8 'buckwheat pancakes' recipes without butter (L1, lift 1.0) · 0 of 1 similar (L2) · 21,242 of 61,367 savory (L3) · curated: fat, flavor
3. **coconut oil** — **Weak** · 0 of 8 'buckwheat pancakes' recipes without butter (L1, lift 1.0) · 0 of 1 similar (L2) · 284 of 61,367 savory (L3) · curated: fat, flavor
_… 2 more in the Evidence tab._
_Rejected: margarine (may contain dairy (label-dependent)); honey (contains honey)_
**Adapted recipe** (side-by-side diff in the Results panel):
- − Butter and maple syrup
- + 2 tablespoon vegetable oil (observed median in 3 recipes without butter)
- Step 1 (changed): Heat pan or griddle. Stir together pancake mixes and water and let stand for 5 minutes. Ladle about 3 ounces of batter on griddle and distribute apple over exposed side. Turn when bubbles start to break, taking care not to pat the pancakes. Cook until they spring back when touched. Serve with vegetable oil.
_Steps rewritten by the model and validated._
**Verified from dataset:**
- vegetable oil for butter: used by 3 of 8 'buckwheat pancakes' recipes without butter (L1, lift 1.6), 0 of 1 similar recipes (L2) and 6,770 of 61,367 savory recipes (L3).
- Observed amount of vegetable oil: median 2 tablespoon (n=3); butter in similar recipes that have it: median 3 tablespoon (n=3).
**Predicted (not verifiable from recipe text):**
Using vegetable oil instead of butter and maple syrup will slightly reduce richness and sweetness while maintaining moisture. The preparation method remains unchanged except for serving with the substitute.
> ✗ **Not safe for your restrictions:** 2 cups of your favorite pancake mix: may contain dairy; 2 cups of your favorite pancake mix: may contain egg; 1/4 cup buckwheat pancake mix: may contain dairy; 1/4 cup buckwheat pancake mix: may contain egg; 1/4 cup buckwheat pancake mix: couldn't be verified for fish; 1/4 cup buckwheat pancake mix: couldn't be verified for gelatin; 1/4 cup buckwheat pancake mix: couldn't be verified for honey; 1/4 cup buckwheat pancake mix: couldn't be verified for meat; 1/4 cup buckwheat pancake mix: couldn't be verified for shellfish. Say e.g. 'remove the pancake mix too' to replace it as well.
> Allergy note: recipe text can't establish medical safety. Check every label for the allergen and for cross-contamination.

Suggestions: Try option 2 · Also remove pancake mix
Trace: LLM call 1 (substitute): 1457 ms, 647 prompt tok, ok | Voice: template (answer type keeps the template)

---

## user-named swap, then two at once

**> find a chocolate chip cookie recipe**

`LLM · gemini-3.5-flash-lite` · 2 LLM calls · 2625 ms · type=search · total=943

> 🗣 I found 943 recipes matching your search for chocolate chip cookie. Some top options include Chocolate Chip Cookie Dough Breakfast Tarts, Easy Chocolate Chip Cookie Dough Cheesecake, and Chocolate Chip Cookie Pie Crust.

**943 recipes** match _matches 'chocolate chip cookie'_; showing 10.
_943 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Chocolate Chip Cookie Dough Breakfast Tarts** `fn:A5QASy9/zLSCdvXwXJ3ZwhaQwXxJV2i` — 7 ingredients · 6 steps
2. **Easy Chocolate Chip Cookie Dough Cheesecake** `ar:iqk5XOpQOGCD.nbIzlczFga5PfoAyBO` — 5 ingredients · 4 steps
3. **Chocolate Chip Cookie Pie Crust** `fn:oQxof/DMNnvFoXWjv9idYb9V15P4jyG` — 4 ingredients · 3 steps
4. **Chocolate Chip Cookie and Mint Ice Cream Sandwiches** `epi:7WR1upPntA7Z6EOJIu7G7vLNWeveD9e` — 6 ingredients · 5 steps
5. **Chocolate Chip Cookie Ice Cream Cake** `ar:Rg20jkBuhdvSux21QiXrZIMwgLy7XoS` — 6 ingredients · 3 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): 2590 ms, 521 prompt tok, ok | LLM call 2 (voice): 934 ms, 481 prompt tok, ok | Voice: ok

---

**> show me the first one**

`rule parser · high-confidence pattern` · 1 LLM calls · 1 ms · type=recipe

> 🗣 Based on your search for a chocolate chip cookie, I found Chocolate Chip Cookie Dough Breakfast Tarts using your active filter. It has seven ingredients and six steps.

**Chocolate Chip Cookie Dough Breakfast Tarts** `fn:A5QASy9/zLSCdvXwXJ3ZwhaQwXxJV2i` — 7 ingredients · 6 steps (opened on the right).

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (voice): 2737 ms, 253 prompt tok, ok | Voice: ok

---

**> replace butter with coconut oil**

`rule parser · high-confidence pattern` · 0 LLM calls · 564 ms · type=substitute

**Chocolate Chip Cookie Dough Breakfast Tarts** `fn:A5QASy9/zLSCdvXwXJ3ZwhaQwXxJV2i` · dish: _breakfast tarts_ (baked) · compared with 10 title matches (L1), 13 similar recipes (L2), 28,735 baked recipes (L3).
> 'butter' isn't in this recipe (checked every ingredient line of `fn:A5QASy9/zLSCdvXwXJ3ZwhaQwXxJV2i`).

Suggestions: 
Trace: Voice: template (answer type keeps the template)

---

**> take out the butter and the eggs**

`rule parser · high-confidence pattern` · 0 LLM calls · 430 ms · type=substitute

**Chocolate Chip Cookie Dough Breakfast Tarts** `fn:A5QASy9/zLSCdvXwXJ3ZwhaQwXxJV2i` · dish: _breakfast tarts_ (baked) · compared with 10 title matches (L1), 13 similar recipes (L2), 28,735 baked recipes (L3).
Removing **eggs** (1 egg) · role: _binding, leavening, moisture, structure_
1. **banana** (chosen) — **Weak** · 0 of 0 'breakfast tarts' recipes without eggs (L1, lift 1.0) · 0 of 0 similar (L2) · 129 of 10,142 baked (L3) · curated: binding, moisture
2. **applesauce** — **Weak** · 0 of 0 'breakfast tarts' recipes without eggs (L1, lift 1.0) · 0 of 0 similar (L2) · 87 of 10,142 baked (L3) · curated: binding, moisture
3. **flaxseed** — **Weak** · 0 of 0 'breakfast tarts' recipes without eggs (L1, lift 1.0) · 0 of 0 similar (L2) · 57 of 10,142 baked (L3) · curated: binding, structure
_… 7 more in the Evidence tab._
> 'butter' isn't in this recipe (checked every ingredient line of `fn:A5QASy9/zLSCdvXwXJ3ZwhaQwXxJV2i`).
> No adaptation: the best usable option for eggs is banana (Weak). Say 'adapt it anyway' for a heavily caveated version.

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

## demo 8 with follow-up allergies

**> Replace cream in this pasta recipe without dairy**

`rule parser · high-confidence pattern` · 1 LLM calls · 2535 ms · type=substitute

> I picked `ar:Uh368ePNqgPJITjq4cLqfGyEj1il5ki` 'Pasta with Tomato Cream Sauce', the top match for 'pasta' that contains cream. Open another recipe to switch.
**Pasta with Tomato Cream Sauce** `ar:Uh368ePNqgPJITjq4cLqfGyEj1il5ki` · dish: _pasta_ (pasta) · compared with 1,592 title matches (L1), 54 similar recipes (L2), 6,780 pasta recipes (L3).
Removing **cream** (1 cup half-and-half) · role: _richness, body_
1. **cashew** (chosen) — **Strong** · 4 of 1411 'pasta' recipes without cream (L1, lift 0.6) · curated: richness, body · explicit variants: `ar:sb1Unxe/KM1D3BbqKHz27h8tfgRVPUa`
2. **silken tofu** — **Strong** · 3 of 1411 'pasta' recipes without cream (L1, lift 0.5) · curated: body · explicit variants: `epi:SX4WUn7soISKA9E..uPhdLIJ6L/J4Fy`
3. **coconut milk** — **Weak** · 2 of 1411 'pasta' recipes without cream (L1, lift 0.4) · 0 of 47 similar (L2) · 58 of 6,042 pasta (L3) · curated: richness, body
_… 7 more in the Evidence tab._
_Rejected: half and half (contains dairy); evaporated milk (contains dairy); cream cheese (contains dairy); feta cheese (contains dairy)_
> ⚠ Conflicting evidence: the tiers disagree, or a better-supported candidate fails a restriction.
**Adapted recipe** (side-by-side diff in the Results panel):
- − 1 cup half-and-half
- + 1/2 cup cashew (observed median in 4 recipes without cream)
- Prep: Soak the cashews in hot water for 15 minutes, drain, and blend with fresh water until smooth.
- Step 1 (changed): In a large saucepan combine pasta sauce, cashew, garlic, salt, pepper, nutmeg and basil. Simmer over low heat for 45 to 50 minutes; do not boil.
_Steps rewritten by the model and validated._
**Verified from dataset:**
- cashew for cream: used by 4 of 1411 'pasta' recipes without cream (L1, lift 0.6), 0 of 47 similar recipes (L2) and 30 of 6,042 pasta recipes (L3).
- Explicit variants using it: `ar:sb1Unxe/KM1D3BbqKHz27h8tfgRVPUa`.
- Observed amount of cashew: median 1/2 cup (n=4); cream in similar recipes that have it: median 1 cup (n=176).
**Predicted (not verifiable from recipe text):**
Using cashew will slightly alter the texture by providing body and richness similar to the original ingredient. The overall taste profile will remain creamy and savory.
> ✗ **Not safe for your restrictions:** 1/8 cup freshly grated Parmesan cheese: contains dairy. Say e.g. 'remove the parmesan cheese too' to replace it as well.
> Allergy note: recipe text can't establish medical safety. Check every label for the allergen and for cross-contamination.

Suggestions: Try option 2 · Also remove parmesan cheese · Allergic to tree nuts?
Trace: LLM call 1 (substitute): 1814 ms, 727 prompt tok, ok | Voice: template (answer type keeps the template)

---

**> I'm also allergic to tree nuts**

`rule parser · high-confidence pattern` · 0 LLM calls · 168 ms · type=substitute

**Pasta with Tomato Cream Sauce** `ar:Uh368ePNqgPJITjq4cLqfGyEj1il5ki` · dish: _pasta_ (pasta) · compared with 1,592 title matches (L1), 54 similar recipes (L2), 6,780 pasta recipes (L3).
Removing **cream** (1 cup half-and-half) · role: _richness, body_
1. **silken tofu** (chosen) — **Strong** · 3 of 1411 'pasta' recipes without cream (L1, lift 0.5) · curated: body · explicit variants: `epi:SX4WUn7soISKA9E..uPhdLIJ6L/J4Fy`
2. **coconut milk** — **Weak** · 2 of 1411 'pasta' recipes without cream (L1, lift 0.4) · 0 of 47 similar (L2) · 58 of 6,042 pasta (L3) · curated: richness, body
3. **cornstarch** — **Weak** · 11 of 1411 'pasta' recipes without cream (L1, lift 0.3) · curated: body · explicit variants: `ar:uGTjXLFuN7yP06OGX0v8Nw.AoBgXCpe`
_… 6 more in the Evidence tab._
_Rejected: cashew (contains tree_nut); half and half (contains dairy); evaporated milk (contains dairy); cream cheese (contains dairy); … 1 more in the Evidence tab_
> ⚠ Conflicting evidence: the tiers disagree, or a better-supported candidate fails a restriction.
**Adapted recipe** (side-by-side diff in the Results panel):
- − 1 cup half-and-half
- + 9 ounce silken tofu (observed median in 3 recipes without cream)
- Prep: Blend the silken tofu until completely smooth.
- Step 1 (changed): In a large saucepan combine pasta sauce, silken tofu, garlic, salt, pepper, nutmeg and basil. Simmer over low heat for 45 to 50 minutes; do not boil.
_Steps rewritten by the model and validated._
**Verified from dataset:**
- silken tofu for cream: used by 3 of 1411 'pasta' recipes without cream (L1, lift 0.5), 0 of 47 similar recipes (L2) and 8 of 6,042 pasta recipes (L3).
- Explicit variants using it: `epi:SX4WUn7soISKA9E..uPhdLIJ6L/J4Fy`.
- Observed amount of silken tofu: median 9 ounce (n=3); cream in similar recipes that have it: median 1 cup (n=176).
**Predicted (not verifiable from recipe text):**
Using silken tofu instead of half-and-half will alter the richness and body of the sauce. The preparation may require blending or thorough incorporation since tofu has a solid consistency compared to liquid dairy.
> ✗ **Not safe for your restrictions:** 1/8 cup freshly grated Parmesan cheese: contains dairy. Say e.g. 'remove the parmesan cheese too' to replace it as well.
> Allergy note: recipe text can't establish medical safety. Check every label for the allergen and for cross-contamination.

Suggestions: Try option 2 · Also remove parmesan cheese · Allergic to soy?
Trace: LLM call 1 (substitute): cache hit | Voice: template (answer type keeps the template)

---

**> the second option**

`rule parser · high-confidence pattern` · 0 LLM calls · 187 ms · type=substitute

**Pasta with Tomato Cream Sauce** `ar:Uh368ePNqgPJITjq4cLqfGyEj1il5ki` · dish: _pasta_ (pasta) · compared with 1,592 title matches (L1), 54 similar recipes (L2), 6,780 pasta recipes (L3).
Removing **cream** (1 cup half-and-half) · role: _richness, body_
1. **silken tofu** — **Strong** · 3 of 1411 'pasta' recipes without cream (L1, lift 0.5) · curated: body · explicit variants: `epi:SX4WUn7soISKA9E..uPhdLIJ6L/J4Fy`
2. **coconut milk** (chosen) — **Weak** · 2 of 1411 'pasta' recipes without cream (L1, lift 0.4) · 0 of 47 similar (L2) · 58 of 6,042 pasta (L3) · curated: richness, body
3. **cornstarch** — **Weak** · 11 of 1411 'pasta' recipes without cream (L1, lift 0.3) · curated: body · explicit variants: `ar:uGTjXLFuN7yP06OGX0v8Nw.AoBgXCpe`
_… 6 more in the Evidence tab._
_Rejected: cashew (contains tree_nut); half and half (contains dairy); evaporated milk (contains dairy); cream cheese (contains dairy); … 1 more in the Evidence tab_
> ⚠ Conflicting evidence: the tiers disagree, or a better-supported candidate fails a restriction.
> No adaptation: the best usable option for cream is coconut milk (Weak). Say 'adapt it anyway' for a heavily caveated version.

Suggestions: Adapt it anyway · Try option 3
Trace: Voice: template (answer type keeps the template)

---

**> remove the parmesan too**

`rule parser · high-confidence pattern` · 1 LLM calls · 1796 ms · type=substitute

**Pasta with Tomato Cream Sauce** `ar:Uh368ePNqgPJITjq4cLqfGyEj1il5ki` · dish: _pasta_ (pasta) · compared with 1,592 title matches (L1), 54 similar recipes (L2), 6,780 pasta recipes (L3).
Removing **cream** (1 cup half-and-half) · role: _richness, body_
1. **silken tofu** (chosen) — **Strong** · 3 of 1411 'pasta' recipes without cream (L1, lift 0.5) · curated: body · explicit variants: `epi:SX4WUn7soISKA9E..uPhdLIJ6L/J4Fy`
2. **coconut milk** — **Weak** · 2 of 1411 'pasta' recipes without cream (L1, lift 0.4) · 0 of 47 similar (L2) · 58 of 6,042 pasta (L3) · curated: richness, body
3. **cornstarch** — **Weak** · 11 of 1411 'pasta' recipes without cream (L1, lift 0.3) · curated: body · explicit variants: `ar:uGTjXLFuN7yP06OGX0v8Nw.AoBgXCpe`
_… 6 more in the Evidence tab._
_Rejected: cashew (contains tree_nut); half and half (contains dairy); evaporated milk (contains dairy); cream cheese (contains dairy); … 1 more in the Evidence tab_
> ⚠ Conflicting evidence: the tiers disagree, or a better-supported candidate fails a restriction.
Removing **parmesan** (1/8 cup freshly grated Parmesan cheese) · role: _flavor, saltiness_
1. **nutritional yeast** (chosen) — **Strong** · 2 of 1027 'pasta' recipes without parmesan (L1, lift 0.8) · 0 of 3 similar (L2) · 8 of 4,662 pasta (L3) · curated: flavor, saltiness · explicit variants: `ar:9YenlBxRzb6U0Rn/aYuRs/pxqI7f/dS`, `ar:sb1Unxe/KM1D3BbqKHz27h8tfgRVPUa`
2. **green onion** — **Weak** · 132 of 1027 'pasta' recipes without parmesan (L1, lift 2.6) · co-occurs; role not established
3. **cherry tomato** — **Weak** · 110 of 1027 'pasta' recipes without parmesan (L1, lift 2.1) · co-occurs; role not established · explicit variants: `ar:546v./ZzzsRCRC6ukAzBL3.NuYMSkPO`
_… 4 more in the Evidence tab._
> ⚠ Conflicting evidence: the tiers disagree, or a better-supported candidate fails a restriction.
**Adapted recipe** (side-by-side diff in the Results panel):
- − 1 cup half-and-half
- + 9 ounce silken tofu (observed median in 3 recipes without cream)
- − 1/8 cup freshly grated Parmesan cheese
- + nutritional yeast (estimate: not verified; start with the same amount; replaces parmesan)
- Prep: Blend the silken tofu until completely smooth.
- Step 1 (changed): In a large saucepan combine pasta sauce, silken tofu, garlic, salt, pepper, nutmeg and basil. Simmer over low heat for 45 to 50 minutes; do not boil.
- Step 3 (changed): Toss pasta with sauce and nutritional yeast. Serve immediately.
_Steps rewritten by the model and validated._
**Verified from dataset:**
- silken tofu for cream: used by 3 of 1411 'pasta' recipes without cream (L1, lift 0.5), 0 of 47 similar recipes (L2) and 8 of 6,042 pasta recipes (L3).
- Explicit variants using it: `epi:SX4WUn7soISKA9E..uPhdLIJ6L/J4Fy`.
- Observed amount of silken tofu: median 9 ounce (n=3); cream in similar recipes that have it: median 1 cup (n=176).
- nutritional yeast for parmesan: used by 2 of 1027 'pasta' recipes without parmesan (L1, lift 0.8), 0 of 3 similar recipes (L2) and 8 of 4,662 pasta recipes (L3).
- Explicit variants using it: `ar:9YenlBxRzb6U0Rn/aYuRs/pxqI7f/dS`, `ar:sb1Unxe/KM1D3BbqKHz27h8tfgRVPUa`.
**Predicted (not verifiable from recipe text):**
The dish may experience changes in richness and body due to the substitution of silken tofu for cream. Flavor and saltiness will also be affected by replacing parmesan with nutritional yeast.
> ✓ Every adapted ingredient was verified free of: dairy, tree_nut.
> Allergy note: recipe text can't establish medical safety. Check every label for the allergen and for cross-contamination.

Suggestions: Try option 2 · Allergic to soy?
Trace: LLM call 1 (substitute): 1392 ms, 1033 prompt tok, ok | Voice: template (answer type keeps the template)

---

## no evidence, defining ingredient, typo verb

**> remove the saffron from this paella**

`rule parser · high-confidence pattern` · 0 LLM calls · 66 ms · type=substitute

> I picked `fn:myU740rouIkbpAlRGDQOAo6YQxCfzQq` 'Shellfish and Chicken Paella with Saffron Rice Chorizo and Green Peas', the top match for 'paella' that contains saffron. Open another recipe to switch.
**Shellfish and Chicken Paella with Saffron Rice Chorizo and Green Peas** `fn:myU740rouIkbpAlRGDQOAo6YQxCfzQq` · dish: _paella_ (savory) · compared with 138 title matches (L1), 4 similar recipes (L2), 77,834 savory recipes (L3).
Removing **saffron** (Large pinch saffron) · role: _unknown in roles.yaml_
1. **carrot** (chosen) — **Weak** · 11 of 94 'paella' recipes without saffron (L1, lift 2.9) · co-occurs; role not established
2. **mushroom** — **Weak** · 6 of 94 'paella' recipes without saffron (L1, lift 1.7) · co-occurs; role not established
3. **pimento** — **Weak** · 6 of 94 'paella' recipes without saffron (L1, lift 3.4) · co-occurs; role not established
_… 3 more in the Evidence tab._
> ⚠ Conflicting evidence: the tiers disagree, or a better-supported candidate fails a restriction.
> No adaptation: the best usable option for saffron is carrot (Weak). Say 'adapt it anyway' for a heavily caveated version.

Suggestions: Adapt it anyway · Try option 2 · Allergic to onion, garlic or root vegetables?
Trace: Voice: template (answer type keeps the template)

---

**> remove the chicken from this chicken curry**

`rule parser · high-confidence pattern` · 0 LLM calls · 657 ms · type=substitute

> I picked `ar:WLHrYUAyL3ST6LnWh62ZJcK4kgG5P76` 'Vietnamese Lemon Grass Chicken Curry', the top match for 'chicken curry' that contains chicken. Open another recipe to switch.
**Vietnamese Lemon Grass Chicken Curry** `ar:WLHrYUAyL3ST6LnWh62ZJcK4kgG5P76` · dish: _curry_ (savory) · compared with 1,114 title matches (L1), 1 similar recipes (L2), 77,834 savory recipes (L3).
Removing **chicken** (1 (3 pound) whole chicken, cut into pieces) · role: _unknown in roles.yaml_
1. **shrimp** (chosen) — **Weak** · 70 of 859 'curry' recipes without chicken (L1, lift 5.3) · co-occurs; role not established
2. **mustard seed** — **Weak** · 55 of 859 'curry' recipes without chicken (L1, lift 2.4) · co-occurs; role not established
3. **vegetable broth** — **Weak** · 53 of 859 'curry' recipes without chicken (L1, lift 8.1) · co-occurs; role not established
_… 3 more in the Evidence tab._
> Chicken is in the dish name ('Vietnamese Lemon Grass Chicken Curry'): without it, it becomes a different dish. I've shown the evidence below; say 'adapt it anyway' if you still want an adaptation.

Suggestions: Adapt it anyway · Try option 2 · Allergic to shellfish?
Trace: Voice: template (answer type keeps the template)

---

**> substitue the eggs in this quiche**

`rule parser · high-confidence pattern` · 0 LLM calls · 1601 ms · type=substitute

> I picked `ar:g4UkgqIF0fBgvDURgGSfazeFZ1y6F3a` 'Easiest Zucchini Quiche', the top match for 'quiche' that contains eggs. Open another recipe to switch.
**Easiest Zucchini Quiche** `ar:g4UkgqIF0fBgvDURgGSfazeFZ1y6F3a` · dish: _quiche_ (savory) · compared with 232 title matches (L1), 6 similar recipes (L2), 77,834 savory recipes (L3).
Removing **eggs** (6 eggs, beaten) · role: _binding_
1. **banana** (chosen) — **Weak** · 0 of 5 'quiche' recipes without eggs (L1, lift 1.0) · 0 of 1 similar (L2) · 1,013 of 63,519 savory (L3) · curated: binding
2. **flaxseed** — **Weak** · 0 of 5 'quiche' recipes without eggs (L1, lift 1.0) · 0 of 1 similar (L2) · 145 of 63,519 savory (L3) · curated: binding
3. **chia seed** — **Weak** · 0 of 5 'quiche' recipes without eggs (L1, lift 1.0) · 0 of 1 similar (L2) · 144 of 63,519 savory (L3) · curated: binding
_… 5 more in the Evidence tab._
> No adaptation: the best usable option for eggs is banana (Weak). Say 'adapt it anyway' for a heavily caveated version.

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

## Hinglish, absent ingredient

**> paneer butter masala recipe**

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 9 ms · type=search · total=7

> 🗣 I found 7 fully verified matches for your search for paneer butter masala. Some of the top results include Paneer Butter Masala, Paneer Tikka Masala, and Paneer Makhani. Let me know if you would like more details on any of these recipes.

**7 recipes** match _matches 'paneer butter masala'_; showing 7.
_7 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Paneer Butter Masala** `ar:ZmVPKvJRYCQq3VZX8o1H4CZgOVTzhLu` — 16 ingredients · 3 steps
2. **Paneer Tikka Masala** `ar:gKkJ9ZwnstHasWs7i.iV0TlbBT0ohyO` — 15 ingredients · 2 steps
3. **Paneer Tikka Sandwich** `ar:u/s6KRCpExE7mkYX/lbAHdgT0lXU2nC` — 11 ingredients · 3 steps
4. **Rosy's Palak Paneer** `ar:zgwAduk6YKR8QIyFZiQVWY.HWvjI3Zi` — 13 ingredients · 2 steps
5. **Paneer Makhani** `ar:TaXtBZpgWvbpWWsM/8Vz8gSGlDcKcIK` — 15 ingredients · 3 steps
_… 2 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): cache hit | LLM call 2 (voice): cache hit | Voice: ok

---

**> show me the first one**

`rule parser · high-confidence pattern` · 0 LLM calls · 1 ms · type=recipe

> 🗣 Here is Paneer Butter Masala, found using your active search filter for that dish. It features sixteen ingredients and three steps.

**Paneer Butter Masala** `ar:ZmVPKvJRYCQq3VZX8o1H4CZgOVTzhLu` — 16 ingredients · 3 steps (opened on the right).

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (voice): cache hit | Voice: ok

---

**> isme makhan nahi chahiye**

`rule parser · high-confidence pattern` · 0 LLM calls · 1917 ms · type=substitute

**Paneer Butter Masala** `ar:ZmVPKvJRYCQq3VZX8o1H4CZgOVTzhLu` · dish: _paneer masala_ (savory) · compared with 3 title matches (L1), 4 similar recipes (L2), 77,834 savory recipes (L3).
Removing **butter** (2 tablespoons butter) · role: _fat, flavor_
1. **olive oil** (chosen) — **Weak** · 0 of 1 'paneer masala' recipes without butter (L1, lift 1.0) · 0 of 2 similar (L2) · 21,242 of 61,367 savory (L3) · curated: fat, flavor
2. **coconut oil** — **Weak** · 0 of 1 'paneer masala' recipes without butter (L1, lift 1.0) · 0 of 2 similar (L2) · 284 of 61,367 savory (L3) · curated: fat, flavor
3. **vegetable oil** — **Weak** · 1 of 1 'paneer masala' recipes without butter (L1, lift 1.3) · 2 of 2 similar (L2) · 6,770 of 61,367 savory (L3) · use more vegetable oil (already in the recipe)
_… 2 more in the Evidence tab._
> Butter is in the dish name ('Paneer Butter Masala'): without it, it becomes a different dish. I've shown the evidence below; say 'adapt it anyway' if you still want an adaptation.

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> remove the eggs**

`rule parser · high-confidence pattern` · 0 LLM calls · 1830 ms · type=substitute

**Paneer Butter Masala** `ar:ZmVPKvJRYCQq3VZX8o1H4CZgOVTzhLu` · dish: _butter masala_ (savory) · compared with 3 title matches (L1), 4 similar recipes (L2), 77,834 savory recipes (L3).
> 'eggs' isn't in this recipe (checked every ingredient line of `ar:ZmVPKvJRYCQq3VZX8o1H4CZgOVTzhLu`).

Suggestions: 
Trace: Voice: template (answer type keeps the template)

---

## no recipe in context

**> remove the eggs**

`rule parser · high-confidence pattern` · 0 LLM calls · 0 ms · type=text

Which recipe should I change? Open one first (e.g. 'show me the first one'), or name the dish.

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---

**> replace milk with almond milk**

`rule parser · high-confidence pattern` · 0 LLM calls · 0 ms · type=text

Which recipe should I change? Open one first (e.g. 'show me the first one'), or name the dish.

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---
