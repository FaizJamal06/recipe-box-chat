# Exploratory run: one session

## one session (all messages)

**> find a banana bread recipe**

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 113 ms · type=search · total=309

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

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 10 ms · type=recipe

> 🗣 Here is Banana Bread French Toast for your banana bread search. Enjoy preparing this recipe with its six ingredients and two simple steps.

**Banana Bread French Toast** `ar:GiHk4/Wm95WTxwkxlmJtSmHUBdpv2La` — 6 ingredients · 2 steps (opened on the right).

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (planner): cache hit | LLM call 2 (voice): cache hit | Voice: ok

---

**> no eggs in this pls**

`rule parser · high-confidence pattern` · 0 LLM calls · 5012 ms · type=substitute

**Eggs → flaxseed** in **Banana Bread French Toast** — **Weak** evidence. Chosen because: Weak, not conflicting, 1/11 L1 recipes without eggs use it (lift too few to compute); next: banana (Weak, 1/11).
L1 = 346 recipes titled 'french toast', 11 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 0 candidates rejected.
> No adaptation: the best usable option for eggs is flaxseed (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> use the second option instead**

`rule parser · high-confidence pattern` · 0 LLM calls · 329 ms · type=substitute

**Eggs → banana** in **Banana Bread French Toast** — **Weak** evidence. Chosen because you picked option 2.
L1 = 346 recipes titled 'french toast', 11 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 0 candidates rejected.
> No adaptation: the best usable option for eggs is banana (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 3
Trace: Voice: template (answer type keeps the template)

---

**> adapt it anyway**

`rule parser · high-confidence pattern` · 1 LLM calls · 9774 ms · type=substitute

**Eggs → 1 1/2 mashed banana (estimate: 1/2 mashed banana per egg; replaces 3 eggs)** in **Banana Bread French Toast** — **Weak** evidence. Chosen because you picked option 2.
L1 = 346 recipes titled 'french toast', 11 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 0 candidates rejected.
> ✗ **Not safe for your restrictions:** 1 loaf banana bread: may contain egg. Say e.g. 'remove the banana bread too' to replace it as well.
_Full evidence and diff in the panel._

Suggestions: Try option 3 · Also remove banana bread
Trace: LLM call 1 (substitute): 9426 ms, error | Voice: template (LLM not used this turn)

---

**> find a pancake recipe**

`rule parser · LLM timeout` · 1 LLM calls · 6132 ms · type=search · total=866

**866 recipes** match _matches 'pancake'_; showing 10.
_866 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **1946 Apple Buckwheat Pancakes** `fn:H449YwkifMLsxY7yHoS5QbzCU1wdecy` — 5 ingredients · 6 steps
2. **Amish Sourdough Pancakes** `ar:qy9TfjYD1KLcpDO57jCkWtUOT9/2pTO` — 3 ingredients · 2 steps
3. **Sausage Pancakes-on-Sticks** `fn:XAWvCYSKqiy.miDM7et4x7GzFLfISJu` — 9 ingredients · 8 steps
4. **Chris Cakes Pancakes** `fn:6bGq5al/DOgEakpsT3FwOaRJEeUGHfy` — 4 ingredients · 3 steps
5. **Fiber One Pancakes** `fn:9j6uWaCLTkZZCiTl7c3NddEKq6g1nmW` — 2 ingredients · 1 step
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): 6010 ms, timeout | Voice: template (LLM not used this turn)

---

**> show me the first one**

`rule parser · high-confidence pattern` · 0 LLM calls · 2 ms · type=recipe

> 🗣 Here is 1946 Apple Buckwheat Pancakes for your pancake search with eggs removed. It has 5 ingredients and 6 steps to follow.

**1946 Apple Buckwheat Pancakes** `fn:H449YwkifMLsxY7yHoS5QbzCU1wdecy` — 5 ingredients · 6 steps (opened on the right).

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (voice): cache hit | Voice: ok

---

**> make it vegan**

`rule parser · high-confidence pattern` · 0 LLM calls · 4423 ms · type=substitute

> Vegan → no meat, fish, shellfish, gelatin, dairy, eggs, honey.
**Butter → vegetable oil** in **1946 Apple Buckwheat Pancakes** — **Weak** evidence. Chosen because: Weak, not conflicting, 2/6 L1 recipes without butter use it (lift too few to compute); next: olive oil (Weak, 0/6).
L1 = 11 recipes titled 'buckwheat pancakes', 6 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 1 candidates rejected.
> No adaptation: the best usable option for butter is vegetable oil (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> find a chocolate chip cookie recipe**

`rule parser · LLM timeout` · 1 LLM calls · 26635 ms · type=search · total=73

> Kept your restrictions (dairy, egg, fish, gelatin, honey, meat, shellfish): they're about you, not the dish. Say e.g. 'dairy is fine now' to drop one.
**39 fully verified recipes** match _matches 'chocolate chip cookie'; no dairy (contains); no egg (contains); no fish (contains); no gelatin (contains); no honey (contains); no meat (contains); no shellfish (contains)_; showing 10.
_73 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Julia's Best Ever Chocolate Chip Cookies In A Jar** `ar:nlCKbdyih.7MkkD2UJoVWPIi2X.qr1y` — 5 ingredients · 2 steps
2. **Banana Oatmeal Chocolate Chip Cookies** `epi:T6QxNuxub8fQtdGKk.BZMtn84Y22Dni` — 7 ingredients · 9 steps
3. **Nutty "Raw" Chocolate Chip Cookie Dough** `fn:7WQsog9BznhyOcLGJhXEI/dXkZxIDku` — 8 ingredients · 3 steps
4. **Gluten-Free Double Chocolate Chip Cookies** `fn:uKIfSK6IzZAyvDmqUJFApgoUPGP3ame` — 11 ingredients · 5 steps
5. **Healthy Vegan Pumpkin Oat Chocolate Chip Cookies** `ar:vT2YUTDevXOtKnhj01C2qlK3b6tBKW.` — 16 ingredients · 5 steps
_… 5 more in the Results panel._
_⚠ 34 more recipes match but have an ingredient I couldn't verify; turn on strict to hide them, or show them in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): 6008 ms, timeout | Voice: template (LLM not used this turn)

---

**> show me the first one**

`rule parser · high-confidence pattern` · 1 LLM calls · 872 ms · type=recipe

**Julia's Best Ever Chocolate Chip Cookies In A Jar** `ar:nlCKbdyih.7MkkD2UJoVWPIi2X.qr1y` — 5 ingredients · 2 steps (opened on the right).
- no dairy: '2 cups semisweet chocolate chips' may contain dairy (check the label)
- no egg: 0 egg-tagged lines, all 5 lines verified
- no fish: 0 fish-tagged lines, all 5 lines verified
- no gelatin: 0 gelatin-tagged lines, all 5 lines verified
- no honey: 0 honey-tagged lines, all 5 lines verified
- no meat: 0 meat-tagged lines, all 5 lines verified
- no shellfish: 0 shellfish-tagged lines, all 5 lines verified

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (voice): 4008 ms, timeout | Voice: template (timeout)

---

**> replace butter with coconut oil**

`rule parser · high-confidence pattern` · 0 LLM calls · 2026 ms · type=substitute

> 'butter' isn't in this recipe (checked every ingredient line of `ar:nlCKbdyih.7MkkD2UJoVWPIi2X.qr1y`).
_Full evidence and diff in the panel._

Suggestions: 
Trace: Voice: template (answer type keeps the template)

---

**> take out the butter and the eggs**

`rule parser · high-confidence pattern` · 0 LLM calls · 7 ms · type=substitute

> 'butter' isn't in this recipe (checked every ingredient line of `ar:nlCKbdyih.7MkkD2UJoVWPIi2X.qr1y`).
> 'eggs' isn't in this recipe (checked every ingredient line of `ar:nlCKbdyih.7MkkD2UJoVWPIi2X.qr1y`).
_Full evidence and diff in the panel._

Suggestions: 
Trace: Voice: template (answer type keeps the template)

---

**> Replace cream in this pasta recipe without dairy**

`rule parser · high-confidence pattern` · 0 LLM calls · 8800 ms · type=substitute

> I picked `ar:Uh368ePNqgPJITjq4cLqfGyEj1il5ki` 'Pasta with Tomato Cream Sauce', the top match for 'pasta' that contains cream; every match has another line that isn't verified free of dairy and egg and fish and gelatin and honey and meat and shellfish. Open another recipe to switch.
**Cream → cornstarch** in **Pasta with Tomato Cream Sauce** — **Weak** evidence. Chosen because: Weak, not conflicting, 2/52 L1 recipes without cream use it (lift too few to compute); next: coconut milk (Weak, 1/52).
L1 = 216 recipes titled 'cream sauce', 52 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 4 candidates rejected.
> No adaptation: the best usable option for cream is cornstarch (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> I'm also allergic to tree nuts**

`rule parser · high-confidence pattern` · 0 LLM calls · 271 ms · type=substitute

**Cream → cornstarch** in **Pasta with Tomato Cream Sauce** — **Weak** evidence. Chosen because: Weak, not conflicting, 2/52 L1 recipes without cream use it (lift too few to compute); next: coconut milk (Weak, 1/52).
L1 = 216 recipes titled 'cream sauce', 52 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 5 candidates rejected.
> No adaptation: the best usable option for cream is cornstarch (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> the second option**

`rule parser · high-confidence pattern` · 0 LLM calls · 254 ms · type=substitute

**Cream → coconut milk** in **Pasta with Tomato Cream Sauce** — **Weak** evidence. Chosen because you picked option 2.
L1 = 216 recipes titled 'cream sauce', 52 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 5 candidates rejected.
> No adaptation: the best usable option for cream is coconut milk (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 3
Trace: Voice: template (answer type keeps the template)

---

**> remove the parmesan too**

`rule parser · high-confidence pattern` · 0 LLM calls · 4061 ms · type=substitute

**Cream → cornstarch** in **Pasta with Tomato Cream Sauce** — **Weak** evidence. Chosen because: Weak, not conflicting, 2/52 L1 recipes without cream use it (lift too few to compute); next: coconut milk (Weak, 1/52).
**Parmesan → nutritional yeast** in **Pasta with Tomato Cream Sauce** — **Weak** evidence. Chosen because: Weak, not conflicting, 2/171 L1 recipes without parmesan use it (lift too few to compute); next: shallot (Weak, 51/171).
L1 = 216 recipes titled 'cream sauce', 52 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 5 candidates rejected.
> No adaptation: the best usable option for cream is cornstarch (Weak); the best usable option for parmesan is nutritional yeast (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> remove the saffron from this paella**

`rule parser · high-confidence pattern` · 0 LLM calls · 7414 ms · type=substitute

> I picked `fn:myU740rouIkbpAlRGDQOAo6YQxCfzQq` 'Shellfish and Chicken Paella with Saffron Rice Chorizo and Green Peas', the top match for 'paella' that contains saffron; every match has another line that isn't verified free of dairy and egg and fish and gelatin and honey and meat and shellfish and tree_nut. Open another recipe to switch.
**Saffron → vegetable oil** in **Shellfish and Chicken Paella with Saffron Rice Chorizo and Green Peas** — **Weak** evidence. Chosen because: Weak, not conflicting, 10/94 L1 recipes without saffron use it (lift 2.3); next: pimento (Weak, 6/94).
L1 = 138 recipes titled 'paella', 94 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 0 candidates rejected.
> No adaptation: the best usable option for saffron is vegetable oil (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> remove the chicken from this chicken curry**

`rule parser · high-confidence pattern` · 0 LLM calls · 6055 ms · type=substitute

> I picked `ar:nG/oG9eORud8sz.IPNJ.HAuDpap46ea` 'Chicken Curry V', the top match for 'chicken curry' that contains chicken; apart from the lines being replaced, every line is verified free of dairy and egg and fish and gelatin and honey and meat and shellfish and tree_nut, so the adapted recipe can pass the safety check. Open another recipe to switch.
**Chicken → flour** in **Chicken Curry V** — **Weak** evidence. Chosen because: Weak, not conflicting, 3/11 L1 recipes without chicken use it (lift 6.5); next: red bell pepper (Weak, 3/11).
L1 = 82 recipes titled 'chicken curry', 11 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 0 candidates rejected.
> Chicken is in the dish name ('Chicken Curry V'): without it, it becomes a different dish. I've shown the evidence below; say 'adapt it anyway' if you still want an adaptation.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2 · Allergic to gluten?
Trace: Voice: template (answer type keeps the template)

---

**> substitue the eggs in this quiche**

`rule parser · high-confidence pattern` · 0 LLM calls · 6257 ms · type=substitute

> I picked `ar:g4UkgqIF0fBgvDURgGSfazeFZ1y6F3a` 'Easiest Zucchini Quiche', the top match for 'quiche' that contains eggs; every match has another line that isn't verified free of dairy and egg and fish and gelatin and honey and meat and shellfish and tree_nut. Open another recipe to switch.
**Eggs → banana** in **Easiest Zucchini Quiche** — **Weak** evidence. Chosen because: Weak, not conflicting, 0/5 L1 recipes without eggs use it (lift too few to compute); next: flaxseed (Weak, 0/5).
L1 = 232 recipes titled 'quiche', 5 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 1 candidates rejected.
> No adaptation: the best usable option for eggs is banana (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> paneer butter masala recipe**

`LLM unavailable, ran as keyword search` · 1 LLM calls · 6640 ms · type=search · total=0

> I couldn't use the language model, so I ran your message as a keyword search for 'paneer butter masala' in titles and ingredients.
> No recipe matches those words, and without the language model I can't tell what you meant. I can only help with recipes: try 'find a pasta recipe' or 'I have eggs and rice'.
**0 recipes** match _matches 'paneer butter masala'; no dairy (contains); no egg (contains); no fish (contains); no gelatin (contains); no honey (contains); no meat (contains); no shellfish (contains); no tree_nut (contains)_; showing 0.
_0 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
No recipe satisfies every restriction; none were relaxed.

Suggestions: 
Trace: LLM call 1 (planner): 6011 ms, timeout | Voice: template (LLM not used this turn)

---

**> show me the first one**

`rule parser · high-confidence pattern` · 0 LLM calls · 0 ms · type=text

Which recipe? Say e.g. 'the second one' after a search, or search first.

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---

**> isme makhan nahi chahiye**

`rule parser · high-confidence pattern` · 0 LLM calls · 803 ms · type=substitute

> 'butter' isn't in this recipe (checked every ingredient line of `ar:g4UkgqIF0fBgvDURgGSfazeFZ1y6F3a`).
_Full evidence and diff in the panel._

Suggestions: 
Trace: Voice: template (answer type keeps the template)

---

**> remove the eggs**

`rule parser · high-confidence pattern` · 0 LLM calls · 423 ms · type=substitute

**Eggs → banana** in **Easiest Zucchini Quiche** — **Weak** evidence. Chosen because: Weak, not conflicting, 0/5 L1 recipes without eggs use it (lift too few to compute); next: flaxseed (Weak, 0/5).
L1 = 232 recipes titled 'quiche', 5 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 1 candidates rejected.
> No adaptation: the best usable option for eggs is banana (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> remove the eggs**

`rule parser · high-confidence pattern` · 0 LLM calls · 426 ms · type=substitute

**Eggs → banana** in **Easiest Zucchini Quiche** — **Weak** evidence. Chosen because: Weak, not conflicting, 0/5 L1 recipes without eggs use it (lift too few to compute); next: flaxseed (Weak, 0/5).
L1 = 232 recipes titled 'quiche', 5 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 1 candidates rejected.
> No adaptation: the best usable option for eggs is banana (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> replace milk with almond milk**

`rule parser · high-confidence pattern` · 0 LLM calls · 1254 ms · type=substitute

> 'milk' isn't in this recipe (checked every ingredient line of `ar:g4UkgqIF0fBgvDURgGSfazeFZ1y6F3a`).
_Full evidence and diff in the panel._

Suggestions: 
Trace: Voice: template (answer type keeps the template)

---
