# Exploratory run: fresh sessions

## banana bread, typos, option switch, forced

**> find a banana bread recipe**

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 64 ms · type=search · total=309

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

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 8 ms · type=recipe

> 🗣 Here is Banana Bread French Toast for your banana bread search. Enjoy preparing this recipe with its six ingredients and two simple steps.

**Banana Bread French Toast** `ar:GiHk4/Wm95WTxwkxlmJtSmHUBdpv2La` — 6 ingredients · 2 steps (opened on the right).

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (planner): cache hit | LLM call 2 (voice): cache hit | Voice: ok

---

**> no eggs in this pls**

`rule parser · high-confidence pattern` · 0 LLM calls · 367 ms · type=substitute

**Eggs → flaxseed** in **Banana Bread French Toast** — **Weak** evidence. Chosen because: Weak, not conflicting, 1/11 L1 recipes without eggs use it (lift too few to compute); next: banana (Weak, 1/11).
L1 = 346 recipes titled 'french toast', 11 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 0 candidates rejected.
> No adaptation: the best usable option for eggs is flaxseed (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> use the second option instead**

`rule parser · high-confidence pattern` · 0 LLM calls · 354 ms · type=substitute

**Eggs → banana** in **Banana Bread French Toast** — **Weak** evidence. Chosen because you picked option 2.
L1 = 346 recipes titled 'french toast', 11 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 0 candidates rejected.
> No adaptation: the best usable option for eggs is banana (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 3
Trace: Voice: template (answer type keeps the template)

---

**> adapt it anyway**

`rule parser · high-confidence pattern` · 1 LLM calls · 9765 ms · type=substitute

**Eggs → 1 1/2 mashed banana (estimate: 1/2 mashed banana per egg; replaces 3 eggs)** in **Banana Bread French Toast** — **Weak** evidence. Chosen because you picked option 2.
L1 = 346 recipes titled 'french toast', 11 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 0 candidates rejected.
> ✗ **Not safe for your restrictions:** 1 loaf banana bread: may contain egg. Say e.g. 'remove the banana bread too' to replace it as well.
_Full evidence and diff in the panel._

Suggestions: Try option 3 · Also remove banana bread
Trace: LLM call 1 (substitute): 9405 ms, error | Voice: template (LLM not used this turn)

---

## make it vegan

**> find a pancake recipe**

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 107 ms · type=search · total=866

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

`rule parser · high-confidence pattern` · 0 LLM calls · 263 ms · type=substitute

> Vegan → no meat, fish, shellfish, gelatin, dairy, eggs, honey.
**Butter → vegetable oil** in **1946 Apple Buckwheat Pancakes** — **Weak** evidence. Chosen because: Weak, not conflicting, 2/6 L1 recipes without butter use it (lift too few to compute); next: olive oil (Weak, 0/6).
L1 = 11 recipes titled 'buckwheat pancakes', 6 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 1 candidates rejected.
> No adaptation: the best usable option for butter is vegetable oil (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

## user-named swap, then two at once

**> find a chocolate chip cookie recipe**

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 128 ms · type=search · total=943

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
Trace: LLM call 1 (planner): cache hit | LLM call 2 (voice): cache hit | Voice: ok

---

**> show me the first one**

`rule parser · high-confidence pattern` · 0 LLM calls · 2 ms · type=recipe

> 🗣 Based on your search for a chocolate chip cookie, I found Chocolate Chip Cookie Dough Breakfast Tarts using your active filter. It has seven ingredients and six steps.

**Chocolate Chip Cookie Dough Breakfast Tarts** `fn:A5QASy9/zLSCdvXwXJ3ZwhaQwXxJV2i` — 7 ingredients · 6 steps (opened on the right).

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (voice): cache hit | Voice: ok

---

**> replace butter with coconut oil**

`rule parser · high-confidence pattern` · 0 LLM calls · 1701 ms · type=substitute

> 'butter' isn't in this recipe (checked every ingredient line of `fn:A5QASy9/zLSCdvXwXJ3ZwhaQwXxJV2i`).
_Full evidence and diff in the panel._

Suggestions: 
Trace: Voice: template (answer type keeps the template)

---

**> take out the butter and the eggs**

`rule parser · high-confidence pattern` · 1 LLM calls · 4745 ms · type=substitute

**Eggs → 1 cup yogurt (observed median in 5 recipes without eggs; estimate for 1 egg: 1/4 cup, from 1/4 cup per egg)** in **Chocolate Chip Cookie Dough Breakfast Tarts** — **Strong** evidence. Chosen because: Strong, not conflicting, 5/362 L1 recipes without eggs use it (lift 3.0); next: applesauce (Strong, 2/362).
L1 = 1,013 recipes titled 'tarts', 253 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 2 candidates rejected.
> ✗ **Not safe for your restrictions:** 1 cup store-bought chocolate chip cookie dough: may contain egg. Say e.g. 'remove the chocolate chip cookie dough too' to replace it as well.
_Full evidence and diff in the panel._

Suggestions: Try option 2 · Also remove chocolate chip cookie dough · Allergic to dairy?
Trace: LLM call 1 (substitute): 2256 ms, overloaded | Voice: template (LLM not used this turn)

---

## demo 8 with follow-up allergies

**> Replace cream in this pasta recipe without dairy**

`rule parser · high-confidence pattern` · 0 LLM calls · 1921 ms · type=substitute

> I picked `ar:Uh368ePNqgPJITjq4cLqfGyEj1il5ki` 'Pasta with Tomato Cream Sauce', the top match for 'pasta' that contains cream; every match has another line that isn't verified free of dairy. Open another recipe to switch.
**Cream → cornstarch** in **Pasta with Tomato Cream Sauce** — **Weak** evidence. Chosen because: Weak, not conflicting, 2/52 L1 recipes without cream use it (lift too few to compute); next: coconut milk (Weak, 1/52).
L1 = 216 recipes titled 'cream sauce', 52 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 4 candidates rejected.
> No adaptation: the best usable option for cream is cornstarch (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> I'm also allergic to tree nuts**

`rule parser · high-confidence pattern` · 0 LLM calls · 246 ms · type=substitute

**Cream → cornstarch** in **Pasta with Tomato Cream Sauce** — **Weak** evidence. Chosen because: Weak, not conflicting, 2/52 L1 recipes without cream use it (lift too few to compute); next: coconut milk (Weak, 1/52).
L1 = 216 recipes titled 'cream sauce', 52 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 5 candidates rejected.
> No adaptation: the best usable option for cream is cornstarch (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> the second option**

`rule parser · high-confidence pattern` · 0 LLM calls · 251 ms · type=substitute

**Cream → coconut milk** in **Pasta with Tomato Cream Sauce** — **Weak** evidence. Chosen because you picked option 2.
L1 = 216 recipes titled 'cream sauce', 52 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 5 candidates rejected.
> No adaptation: the best usable option for cream is coconut milk (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 3
Trace: Voice: template (answer type keeps the template)

---

**> remove the parmesan too**

`rule parser · high-confidence pattern` · 0 LLM calls · 426 ms · type=substitute

**Cream → cornstarch** in **Pasta with Tomato Cream Sauce** — **Weak** evidence. Chosen because: Weak, not conflicting, 2/52 L1 recipes without cream use it (lift too few to compute); next: coconut milk (Weak, 1/52).
**Parmesan → nutritional yeast** in **Pasta with Tomato Cream Sauce** — **Weak** evidence. Chosen because: Weak, not conflicting, 2/171 L1 recipes without parmesan use it (lift too few to compute); next: shallot (Weak, 51/171).
L1 = 216 recipes titled 'cream sauce', 52 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 5 candidates rejected.
> No adaptation: the best usable option for cream is cornstarch (Weak); the best usable option for parmesan is nutritional yeast (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

## no evidence, defining ingredient, typo verb

**> remove the saffron from this paella**

`rule parser · high-confidence pattern` · 0 LLM calls · 286 ms · type=substitute

> I picked `fn:myU740rouIkbpAlRGDQOAo6YQxCfzQq` 'Shellfish and Chicken Paella with Saffron Rice Chorizo and Green Peas', the top match for 'paella' that contains saffron. Open another recipe to switch.
**Saffron → vegetable oil** in **Shellfish and Chicken Paella with Saffron Rice Chorizo and Green Peas** — **Weak** evidence. Chosen because: Weak, not conflicting, 10/94 L1 recipes without saffron use it (lift 2.3); next: pimento (Weak, 6/94).
L1 = 138 recipes titled 'paella', 94 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 0 candidates rejected.
> No adaptation: the best usable option for saffron is vegetable oil (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> remove the chicken from this chicken curry**

`rule parser · high-confidence pattern` · 0 LLM calls · 2963 ms · type=substitute

> I picked `ar:WLHrYUAyL3ST6LnWh62ZJcK4kgG5P76` 'Vietnamese Lemon Grass Chicken Curry', the top match for 'chicken curry' that contains chicken. Open another recipe to switch.
**Chicken → flour** in **Vietnamese Lemon Grass Chicken Curry** — **Weak** evidence. Chosen because: Weak, not conflicting, 3/11 L1 recipes without chicken use it (lift 6.5); next: red bell pepper (Weak, 3/11).
L1 = 82 recipes titled 'chicken curry', 11 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 0 candidates rejected.
> Chicken is in the dish name ('Vietnamese Lemon Grass Chicken Curry'): without it, it becomes a different dish. I've shown the evidence below; say 'adapt it anyway' if you still want an adaptation.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2 · Allergic to gluten?
Trace: Voice: template (answer type keeps the template)

---

**> substitue the eggs in this quiche**

`rule parser · high-confidence pattern` · 0 LLM calls · 3756 ms · type=substitute

> I picked `ar:g4UkgqIF0fBgvDURgGSfazeFZ1y6F3a` 'Easiest Zucchini Quiche', the top match for 'quiche' that contains eggs; apart from the lines being replaced, every line is verified free of egg, so the adapted recipe can pass the safety check. Open another recipe to switch.
**Eggs → banana** in **Easiest Zucchini Quiche** — **Weak** evidence. Chosen because: Weak, not conflicting, 0/5 L1 recipes without eggs use it (lift too few to compute); next: flaxseed (Weak, 0/5).
L1 = 232 recipes titled 'quiche', 5 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 0 candidates rejected.
> No adaptation: the best usable option for eggs is banana (Weak). Say 'adapt it anyway' for a heavily caveated version.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

## Hinglish, absent ingredient

**> paneer butter masala recipe**

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 27 ms · type=search · total=7

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

`rule parser · high-confidence pattern` · 0 LLM calls · 3 ms · type=recipe

> 🗣 Here is Paneer Butter Masala, found using your active search filter for that dish. It features sixteen ingredients and three steps.

**Paneer Butter Masala** `ar:ZmVPKvJRYCQq3VZX8o1H4CZgOVTzhLu` — 16 ingredients · 3 steps (opened on the right).

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (voice): cache hit | Voice: ok

---

**> isme makhan nahi chahiye**

`rule parser · high-confidence pattern` · 0 LLM calls · 4769 ms · type=substitute

**Butter → coconut oil** in **Paneer Butter Masala** — **Weak** evidence. Chosen because: Weak, not conflicting, 3/79 L1 recipes without butter use it (lift too few to compute); next: vegetable oil (Weak, 23/79).
L1 = 98 recipes titled 'masala', 79 without the item (the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it) · 0 candidates rejected.
> Butter is in the dish name ('Paneer Butter Masala'): without it, it becomes a different dish. I've shown the evidence below; say 'adapt it anyway' if you still want an adaptation.
_Full evidence and diff in the panel._

Suggestions: Adapt it anyway · Try option 2
Trace: Voice: template (answer type keeps the template)

---

**> remove the eggs**

`rule parser · high-confidence pattern` · 0 LLM calls · 4647 ms · type=substitute

> 'eggs' isn't in this recipe (checked every ingredient line of `ar:ZmVPKvJRYCQq3VZX8o1H4CZgOVTzhLu`).
_Full evidence and diff in the panel._

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
