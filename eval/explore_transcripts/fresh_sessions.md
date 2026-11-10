# Exploratory run: fresh sessions

## everyday chat + wheat allergy + references

**> hi there**

`rule parser · high-confidence pattern` · 0 LLM calls · 0 ms · type=text

Hi! I can find recipes, filter them by what you can't eat, rank them by the ingredients you have, and count things across the collection. What are you in the mood for?

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---

**> wat can u do?**

`rule parser · high-confidence pattern` · 0 LLM calls · 0 ms · type=text

I work only from this collection of 122,933 valid recipes. I can find dishes ('penne pasta, no dairy'), suggest recipes for what you have ('I have eggs and rice'), explain why a recipe ranked where it did, and answer counts and rankings ('how many recipes are dairy-free?'), always with the calculation shown.

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---

**> find me a chiken curry recipe**

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 24 ms · type=search · total=752

> 🗣 No recipes match 'chiken curry', so I'm showing results for 'chicken curry' (spelling corrected). With your active search filter for chicken curry, I found options like Chicken Curry Salad, Yogurt Chicken Curry, and Chicken Curry and Potatoes.

> No recipes match 'chiken curry', so I'm showing results for 'chicken curry' (spelling corrected).
**752 recipes** match _matches 'chicken curry'_; showing 10.
_752 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Chicken Curry Salad** `ar:zBiq7xcOb.fQ6EH.GhV9DS8RyoS6GpO` — 5 ingredients · 3 steps
2. **Yogurt Chicken Curry** `ar:WIK1aJaoXm3lWBNkLhldSxsj5MQeGNy` — 5 ingredients · 2 steps
3. **Chicken Curry and Potatoes** `ar:IcSnM3/i0XN5mUY9.JHJ18ul3ZuRARS` — 9 ingredients · 3 steps
4. **Slow Cooker Chicken Curry** `ar:Q7CuuQBik7SePx9c3.sDaXJE5gn0Te6` — 7 ingredients · 3 steps
5. **Chicken Curry Croissants** `ar:2GjVRl88gAKND6WJz7qV9lK2/gul9Mm` — 10 ingredients · 2 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): cache hit | LLM call 2 (voice): cache hit | Voice: ok

---

**> im allergic to wheat**

`rule parser · high-confidence pattern` · 0 LLM calls · 461 ms · type=search · total=472

> 🗣 I found 472 matches for your chicken curry search with the no gluten filter applied. Since you mentioned a wheat allergy, I am excluding the gluten tag, which is stricter than needed as it also excludes barley and rye. Some of the top options include Chicken Curry Salad, Yogurt Chicken Curry, and Chicken Curry and Potatoes.

> Wheat allergy → I'm excluding the gluten tag. That is stricter than needed: it also excludes barley and rye.
**472 recipes** match _matches 'chicken curry'; no gluten (contains)_; showing 10.
_472 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Chicken Curry Salad** `ar:zBiq7xcOb.fQ6EH.GhV9DS8RyoS6GpO` — 5 ingredients · 3 steps
2. **Yogurt Chicken Curry** `ar:WIK1aJaoXm3lWBNkLhldSxsj5MQeGNy` — 5 ingredients · 2 steps
3. **Chicken Curry and Potatoes** `ar:IcSnM3/i0XN5mUY9.JHJ18ul3ZuRARS` — 9 ingredients · 3 steps
4. **Slow Cooker Chicken Curry** `ar:Q7CuuQBik7SePx9c3.sDaXJE5gn0Te6` — 7 ingredients · 3 steps
5. **Wonderful Chicken Curry Salad** `ar:ziehJ1qy0jtRN2AoYgfMd7xYgv6aAfK` — 8 ingredients · 2 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (voice): cache hit | Voice: ok

---

**> show me the 3rd one**

`rule parser · high-confidence pattern` · 0 LLM calls · 65 ms · type=recipe

> 🗣 I found Chicken Curry and Potatoes for your chicken curry search with no gluten. It has 9 ingredients and 3 steps, and the no gluten check passed on all 9 lines.

**Chicken Curry and Potatoes** `ar:IcSnM3/i0XN5mUY9.JHJ18ul3ZuRARS` — 9 ingredients · 3 steps (opened on the right).
- no gluten: 0 gluten-tagged lines; checked 9 lines

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (voice): cache hit | Voice: ok

---

**> why that one?**

`rule parser · high-confidence pattern` · 0 LLM calls · 0 ms · type=text

**Chicken Curry and Potatoes** `ar:IcSnM3/i0XN5mUY9.JHJ18ul3ZuRARS` is #3 of 472 matches (matches 'chicken curry'; no gluten (contains)): its title contains the exact phrase, and those rank first; ties go to recipe id. Checks: no gluten: 0 gluten-tagged lines; checked 9 lines.

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---

**> no nuts either pls**

`rule parser · high-confidence pattern` · 0 LLM calls · 1333 ms · type=search · total=379

> 🗣 I found several great options for chicken curry that fit your filters for no gluten, peanut, and tree nut, including Chicken Curry Salad, Yogurt Chicken Curry, Chicken Curry and Potatoes, Slow Cooker Chicken Curry, and Vietnamese Lemon Grass Chicken Curry. You have Chicken Curry and Potatoes selected right now.

**379 recipes** match _matches 'chicken curry'; no gluten (contains); no peanut (contains); no tree_nut (contains)_; showing 10.
_379 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Chicken Curry Salad** `ar:zBiq7xcOb.fQ6EH.GhV9DS8RyoS6GpO` — 5 ingredients · 3 steps
2. **Yogurt Chicken Curry** `ar:WIK1aJaoXm3lWBNkLhldSxsj5MQeGNy` — 5 ingredients · 2 steps
3. **Chicken Curry and Potatoes** `ar:IcSnM3/i0XN5mUY9.JHJ18ul3ZuRARS` — 9 ingredients · 3 steps
4. **Slow Cooker Chicken Curry** `ar:Q7CuuQBik7SePx9c3.sDaXJE5gn0Te6` — 7 ingredients · 3 steps
5. **Vietnamese Lemon Grass Chicken Curry** `ar:WLHrYUAyL3ST6LnWh62ZJcK4kgG5P76` — 8 ingredients · 2 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (voice): cache hit | Voice: ok

---

**> thanks!**

`rule parser · high-confidence pattern` · 0 LLM calls · 0 ms · type=text

You're welcome! Want me to refine those results, or look for something else?

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---

## pantry

**> i got eggs spinach and feta, what can i make**

`rule parser · high-confidence pattern` · 1 LLM calls · 6247 ms · type=match · total=35156

Your ingredients: **egg, spinach, feta cheese** · staples assumed: salt, black pepper, water
Hard constraints: _uses at least 1 of your ingredients_
**Top 5** of 35,156 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)
1. **Spinach, Tomato, and Feta Egg White Omelette** `ar:LuPRsd3uZDNT/ecut.zOzOvlKDADary` — 6 ingredients · 2 steps · score **3.80** · matched 3, extra 2
2. **Challenge Feel-Good Frittata** `epi:MZzyHBss1.zzCwkNL/GW29z0wNxdQlq` — 5 ingredients · 2 steps · score **3.80** · matched 3, extra 2
3. **Spinach and Feta Turkey Burgers** `ar:wF16LXMBTJAPjEMrE6nO6lOvyNk8ktW` — 5 ingredients · 3 steps · score **3.70** · matched 3, extra 2
4. **Potato, Spinach, and Feta Gratin** `epi:WuhP18FpOn/s.Lzg3QVlDAsu6ciOsWS` — 7 ingredients · 3 steps · score **3.70** · matched 3, extra 2
5. **My Big Fat Greek Omelet** `ar:aX5BX5FpbnXHSK9qjaxJkJUuGCmIA7.` — 8 ingredients · 3 steps · score **2.70** · matched 3, extra 3

Suggestions: Show steps for #1 · Why #1? · Fewer extra ingredients?
Trace: LLM call 1 (voice): 4008 ms, timeout | Voice: template (timeout)

---

**> exclude eggs too**

`rule parser · high-confidence pattern` · 1 LLM calls · 289 ms · type=match · total=3062

Your ingredients: **spinach, feta cheese** · staples assumed: salt, black pepper, water
> Removed from your ingredients because 'no egg' excludes it: egg
Hard constraints: _no egg (contains); uses at least 1 of your ingredients_
**Top 5** of 3,062 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)
1. **Simplistic Pepper Salad** `ar:kDY6w2OqndG6UAdF3yuOmyA1fdln8FK` — 4 ingredients · 3 steps · score **2.70** · matched 2, extra 1
2. **Steamed Baby Spinach** `fn:/hxM4nGEcORulr.SvZl8Koq9TrWGT4O` — 2 ingredients · 2 steps · score **1.80** · matched 1, extra 0
3. **Spinach-Stuffed Flounder with Mushrooms and Feta** `ar:102.I5fcUsJNczOr0ozbU9gek08IupG` — 4 ingredients · 6 steps · score **1.40** · matched 2, extra 2
4. **Greens and Craisins®** `ar:x/NcUYHvlMenxNiC3sZpVez447yDwGm` — 5 ingredients · 1 step · score **0.90** · matched 2, extra 3
5. **Spinach Salad With Ease** `ar:oOJiCPvpi1PUaiVagWsxwpYpLeo50sm` — 6 ingredients · 2 steps · score **0.80** · matched 2, extra 3

Suggestions: Show steps for #1 · Why #1? · Fewer extra ingredients?
Trace: LLM call 1 (voice): 4003 ms, timeout | Voice: template (timeout)

---

**> fewer ingredients??**

`rule parser · LLM timeout` · 1 LLM calls · 6264 ms · type=match · total=3062

Your ingredients: **spinach, feta cheese** · staples assumed: salt, black pepper, water
> Removed from your ingredients because 'no egg' excludes it: egg
Hard constraints: _no egg (contains); uses at least 1 of your ingredients_
**Top 5** of 3,062 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)
1. **Simplistic Pepper Salad** `ar:kDY6w2OqndG6UAdF3yuOmyA1fdln8FK` — 4 ingredients · 3 steps · score **2.20** · matched 2, extra 1
2. **Steamed Baby Spinach** `fn:/hxM4nGEcORulr.SvZl8Koq9TrWGT4O` — 2 ingredients · 2 steps · score **1.80** · matched 1, extra 0
3. **Spinach-Stuffed Flounder with Mushrooms and Feta** `ar:102.I5fcUsJNczOr0ozbU9gek08IupG` — 4 ingredients · 6 steps · score **0.40** · matched 2, extra 2
4. **Wilted Baby Spinach** `epi:fSN2RnHAcCTngvTA9BwadDYAqWJ4jTO` — 2 ingredients · 2 steps · score **0.30** · matched 1, extra 1
5. **Deep Fried Spinach** `ar:W6ot7oceZ.Sylg28GSWvsbCtjQ6FGta` — 3 ingredients · 3 steps · score **0.20** · matched 1, extra 1

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): 6005 ms, timeout | Voice: template (LLM not used this turn)

---

## cuisines + Hinglish

**> Gujarati dishes**

`guard · no LLM needed` · 0 LLM calls · 29 ms · type=search · total=8

> 🗣 I found eight dishes for your search for Gujarati dishes. Please note that recipes are approximated by titles containing terms like gujarati, dhokla, thepla, khandvi, undhiyu, handvo, kadhi, khichdi, fafda, or shrikhand. Top results include Gujarati Kadhi and Gujarati Shrikhand.

> There's no cuisine field in this dataset, so 'gujarati' is approximated by recipe titles containing: gujarati, dhokla, thepla, khandvi, undhiyu, handvo, kadhi, khichdi, fafda, shrikhand; plus dish names suggested by the LLM: gujarati kadhi. Dishes not named that way are missed.
**8 recipes** match _title has any of: gujarati, dhokla, thepla, khandvi, undhiyu, handvo, kadhi, khichdi, fafda, shrikhand, gujarati kadhi_; showing 8.
_8 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Gujarati Kadhi** `ar:EqPvfzr0rK/342K3CgyGS3pj1IlFjIG` — 16 ingredients · 2 steps
2. **Gujarati Shrikhand** `ar:AoMW5GJyhWpZ5J4fD4d7NeNmU891x4i` — 7 ingredients · 2 steps
3. **Microwave Khandvi** `ar:v5GP.yKm2/BeIgrUkfZ145KomocsxWu` — 11 ingredients · 6 steps
4. **Sago Sabudana Khichdi** `ar:f0rUgClihrOp7pNn3eDu.CoYFE3.qWi` — 10 ingredients · 3 steps
5. **Spicy Indian (Gujarati) Green Beans** `ar:ppf.Z5A8oM5aAeykKP1zqcKiSRs/mfe` — 8 ingredients · 2 steps
_… 3 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (cuisine): cache hit | LLM call 2 (voice): cache hit | Voice: ok

---

**> any italian recipes without meat**

`guard · no LLM needed` · 1 LLM calls · 1424 ms · type=search · total=1755

> There's no cuisine field in this dataset, so 'italian' is approximated by recipe titles containing: italian, risotto, lasagna, carbonara, bolognese, pesto, gnocchi, bruschetta, tiramisu, cacciatore, piccata, osso buco, focaccia; plus dish names suggested by the LLM: spaghetti carbonara, margherita pizza, lasagna bolognese, chicken parmigiana, risotto alla milanese. Dishes not named that way are missed.
**1,755 recipes** match _title has any of: italian, risotto, lasagna, carbonara, bolognese, pesto, gnocchi, bruschetta, tiramisu, cacciatore, piccata, osso buco, focaccia, spaghetti carbonara, margherita pizza, lasagna bolognese, chicken parmigiana, risotto alla milanese; no meat (contains)_; showing 10.
_1,755 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Lasagna with Bolognese Meat Sauce** `fn:xLJNHyNU5/M5SqT3TsFlckJFnwLIFqu` — 4 ingredients · 8 steps
2. **Pasticciata Bolognese—Lasagna with Spinach Noodles and Bolognese Sauce** `epi:yz9fOdK0qj36hZqgTHFrytjmh1cP5V.` — 5 ingredients · 28 steps
3. **Hot Italian Pesto Bread** `fn:Tnm7LFuN.nuH6f3CYhlQt1CiacQM/Nu` — 3 ingredients · 3 steps
4. **Gnocchi Cacciatore Soup** `ar:vt/2fc8kmwq2PXAU1Tc6asF037Xhqmi` — 13 ingredients · 3 steps
5. **Italian-Style Bruschetta** `ar:U.FPsEmXuAVCBT1UJPPNGUwdzej4O26` — 9 ingredients · 4 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (cuisine): cache hit | LLM call 2 (voice): 4001 ms, timeout | Voice: template (timeout)

---

**> paneer ki koi recipe batao**

`LLM unavailable, ran as keyword search` · 1 LLM calls · 6550 ms · type=search · total=38

> Kept your restrictions (meat): they're about you, not the dish. Say e.g. 'dairy is fine now' to drop one.
> I couldn't use the language model, so I ran your message as a keyword search for 'paneer' in titles and ingredients.
**38 recipes** match _matches 'paneer'; no meat (contains)_; showing 10.
_38 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Homemade Paneer** `fn:BZ/GlKdZJYmNmWEYt5/0/RjG2wO5BNa` — 2 ingredients · 2 steps
2. **Sweet Corn Subji With Paneer and Cashew Nuts** `ar:gaPJwaBQ29c1NmcefuccAqAyOqpAlnS` — 9 ingredients · 2 steps
3. **Paneer Tikka Sandwich** `ar:u/s6KRCpExE7mkYX/lbAHdgT0lXU2nC` — 11 ingredients · 3 steps
4. **Palak Paneer (Spinach Curry)** `ar:BA.VxUUY3ghornOATh4lsqtfcnlrpoS` — 12 ingredients · 3 steps
5. **Quick Paneer Makhani** `ar:sR2muE1pkAy0eneqXMcDemvQrbhVAQy` — 12 ingredients · 2 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): 6007 ms, timeout | Voice: template (LLM not used this turn)

---

## diets + contradictions

**> something vegan for dinner**

`rule parser · high-confidence pattern` · 1 LLM calls · 5116 ms · type=search · total=22648

**22,648 recipes** match _no dairy (contains); no egg (contains); no fish (contains); no meat (contains); no shellfish (contains)_; showing 10.
_22,648 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Best Lemonade Ever** `ar:..3M3xsVPQLnncQ2oYzCyhGjNe/6EB2` — 3 ingredients · 2 steps
2. **Sicilian Lentil Pasta Sauce** `ar:..6gl/0GIzSugrbvy6kHyxEHMMP4h9K` — 11 ingredients · 3 steps
3. **Salsa de Tomatillos Como Las Asadas y Big Star** `ar:..G2iuRLT7oseNmkKbjqAgbdB1G5IBC` — 11 ingredients · 5 steps
4. **Minty Mint Chutney** `ar:..hYtxdDoy5Rp..pLgIj2mKKfvp1jPa` — 5 ingredients · 1 step
5. **Bok Choy Salad** `ar:./5SXkxSheUGnXwzE.JEWAq6sts0hEC` — 7 ingredients · 4 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (voice): 4011 ms, timeout | Voice: template (timeout)

---

**> vegan chicken curry**

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 3 ms · type=text

> Kept your restrictions (dairy, egg, fish, meat, shellfish): they're about you, not the dish. Say e.g. 'dairy is fine now' to drop one.
“vegan chicken curry” clashes with your restriction “no meat” (chicken contains meat). Should I look for a version without chicken, or drop the “no meat” restriction?

Suggestions: Drop “no meat” · Vegan curry without chicken
Trace: LLM call 1 (planner): cache hit | Voice: template (answer type keeps the template)

---

**> im allergic to shellfish, find a paella recipe**

`rule parser · LLM timeout` · 1 LLM calls · 8027 ms · type=search · total=8

**8 recipes** match _matches 'paella'; no dairy (contains); no egg (contains); no fish (contains); no meat (contains); no shellfish (contains)_; showing 8.
_8 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Easy Mushroom Vegetable Paella** `fn:jVxhyTUi6j/Geq1Rnx0DbqAC9j8i1g2` — 7 ingredients · 3 steps
2. **Paella Style Rice** `fn:1lnaKFQ9Gz3Gxz6b16KbjiKYJrbaRRq` — 6 ingredients · 5 steps
3. **Vegetable Paella** `ar:UY6e5bgJQ0/mJKOZlDPy3RH1zsN6PzK` — 10 ingredients · 2 steps
4. **Vegetable Paella** `fn:Qtx.uRJG7Zf03JO2c0VTyjp3Zv3sYda` — 18 ingredients · 5 steps
5. **Paella Rice Salad** `fn:HMSFFYRr6YRzlj7fGSTmsPoAOoxo5ya` — 11 ingredients · 2 steps
_… 3 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): 6008 ms, timeout | Voice: template (LLM not used this turn)

---

**> gluten free pasta recipes**

`rule parser · LLM timeout` · 1 LLM calls · 9201 ms · type=search · total=24

**24 recipes** match _matches 'pasta'; no dairy (contains); no egg (contains); no fish (contains); no meat (contains); no shellfish (contains); no gluten (contains)_; showing 10.
_24 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Spaghetti Pasta Sauce** `ar:dmg1NI9QFfZ/Ol3ijXZZlXEmMAhXCOu` — 6 ingredients · 5 steps
2. **Ruffle-Edged Pasta with Cauliflower and Parsley Sauce** `epi:M1FxbRvWuSGZ26HO7U7ZysZuASc4Tk2` — 5 ingredients · 2 steps
3. **Low-Carb Zucchini Pasta** `ar:c8lKQEPnadVNuPshzVQwe4U1z.AfDHa` — 4 ingredients · 2 steps
4. **Veggie Pasta Minus the Pasta** `ar:pelkTlLxVl8SYKs2Wd/ngf39nBiBwaq` — 13 ingredients · 4 steps
5. **Simple Delicious Pasta Sauce** `ar:AlRT92kHplnxIe/I7LMm0rZjpCNqlQS` — 4 ingredients · 3 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): 6006 ms, timeout | Voice: template (LLM not used this turn)

---

## vague + off-topic

**> something quick for dinner**

`rule parser · high-confidence pattern` · 0 LLM calls · 0 ms · type=text

There's no cook-time field, but I can keep it short: want recipes with at most four steps, or do you have a dish in mind?

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---

**> whats the weather like today**

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 2 ms · type=text

I can only help with the recipes in this collection, so I'll leave that one. Try something like 'find a quick pasta recipe' or 'I have eggs and spinach'.

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: LLM call 1 (planner): cache hit | Voice: template (answer type keeps the template)

---

**> tell me a joke**

`LLM unavailable, ran as keyword search` · 1 LLM calls · 6021 ms · type=search · total=0

> I couldn't use the language model, so I ran your message as a keyword search for 'tell joke' in titles and ingredients.
> No recipe matches those words, and without the language model I can't tell what you meant. I can only help with recipes: try 'find a pasta recipe' or 'I have eggs and rice'.
**0 recipes** match _matches 'tell joke'_; showing 0.
_0 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
No recipe satisfies every restriction; none were relaxed.

Suggestions: 
Trace: LLM call 1 (planner): 6015 ms, timeout | Voice: template (LLM not used this turn)

---

**> how many calories in a big mac**

`guard · no LLM needed` · 0 LLM calls · 0 ms · type=unsupported

Not in the dataset: there are no nutrition fields (no calories, macros, sodium, sugar or fibre), so I can't compute or estimate them from this data.
I can list a recipe's ingredient lines instead; pick one from a search first.

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---

## stats

**> how many recipes have garlic but no onion**

`LLM · gemini-3.5-flash-lite` · 1 LLM calls · 8091 ms · type=stats

Recipes where: _contains garlic AND no onion_
- **strict**: **16,762** of 122,933 valid recipes = **13.64%**
- **broad**: **13,638** of 122,933 valid recipes = **11.09%**
_16,762 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
Normalization: strict garlic = the 'garlic' family (garlic, cloves garlic, garlic paste, bulb garlic, pureed garlic, garlic bulb, ...); broad adds dried garlic, garlic flake, garlic powder, garlic salt, granulated garlic | strict onion = the 'onion' family (onion, red onion, sweet onion, pearl onion, maui onion, cipollini onion, ...); broad adds dried onion, french-fried onion, fried onion, green onion, onion flake, onion powder, onion salt, shallot
Method: Counted valid recipes matching all filters (strict); percentage = count / valid recipes. A recipe contains X when one of its required ingredient items is X (an 'or' alternative alone does not count).
_SQL: see the Calculation tab._

Suggestions: Fewest steps? · Top ingredients?
Trace: LLM call 1 (planner): cache hit | LLM call 2 (voice): 4014 ms, timeout | Voice: template (timeout)

---

**> which 3 recipes have the most ingredients**

`LLM · gemini-3.5-flash-lite` · 2 LLM calls · 64772 ms · type=stats

**3 recipes** (all valid recipes), ingredients descending:
1. **Eggplant Lasagna with Marinated Red Pepper and Arugula Salad** `fn:VyOSR27DV9/2XWc04AaULLRHh4go0C.` — 82 ingredients · 25 steps
2. **Pizza Four Ways** `fn:39v09iqRtZlSrp6sB93u7RM2RORZOUa` — 78 ingredients · 28 steps
3. **Rebuilt Louisiana Seafood Platter** `fn:M37ZUEX5jp0z5ZXvGyuplXGzos2slMy` — 76 ingredients · 11 steps
_Analyzed: 122,933 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
Method: Sorted all 122,933 matching valid recipes by n_ingredients desc, ties broken by n_steps ascending, then recipe id ascending.
_SQL: see the Calculation tab._

Suggestions: Show steps for #1 · Dairy-free count? · Top ingredients?
Trace: LLM call 1 (planner): 6904 ms, 471 prompt tok, ok | LLM call 2 (voice): 4029 ms, timeout | Voice: template (timeout)

---

**> average steps for recipes with chicken**

`LLM · gemini-3.5-flash-lite` · 1 LLM calls · 120454 ms · type=stats

Mean number of steps (contains chicken): **4.85**
_Analyzed: 8,770 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
Normalization: strict chicken = the 'chicken' family (chicken breast, chicken, chicken thigh, chicken wing, rotisserie chicken, chicken leg, ...); broad adds chicken bouillon, chicken broth, ground chicken
> Note: Ingredient filters use the strict definition; the broad definition would match 16,497 recipes.
Method: mean of n_steps over 8,770 matching valid recipes. Steps = effective n_steps: non-empty newline-separated steps, except when the instructions are one paragraph of 2+ sentences, where sentences are counted instead (PRD 4.4).
_SQL: see the Calculation tab._

Suggestions: Fewest steps? · Top ingredients?
Trace: LLM call 1 (planner): cache hit | LLM call 2 (voice): 4005 ms, timeout | Voice: template (timeout)

---

**> how many recipes are nut free**

`LLM · gemini-3.5-flash-lite` · 1 LLM calls · 9272 ms · type=stats

Recipes where: _peanut/tree_nut-free recipes_
- **lenient**: **104,333** of 122,933 valid recipes = **84.87%**
- **strict**: **103,419** of 122,933 valid recipes = **84.13%**
_104,333 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
Normalization: Tag levels (recipe_tags): contains = a required item has it; may_contain = label-dependent (e.g. margarine, chocolate chips); alt = only in an 'or' option that has a tag-free alternative, so the recipe can be made without it (counted as free).
Method: lenient = valid recipes with no peanut/tree_nut line at level 'contains' (may_contain and alt count as free); strict = no peanut/tree_nut line at 'contains' or 'may_contain'; percentage = count / valid recipes.
_SQL: see the Calculation tab._

Suggestions: Dairy-free count? · Top ingredients?
Trace: LLM call 1 (planner): cache hit | LLM call 2 (voice): 4030 ms, timeout | Voice: template (timeout)

---

## multi-constraint follow-ups

**> find a soup recipe**

`LLM · gemini-3.5-flash-lite` · 1 LLM calls · 3570 ms · type=search · total=5541

> 🗣 I found several soup recipes for you, including Mushroom-Leek-Pea Soup with Lemon-Ginger Creme Fraiche, Chicken Soup Casserole, and Creamy Soup Steaks. There are many more matches available with your current soup filter.

**5,541 recipes** match _matches 'soup'_; showing 10.
_5,541 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Mushroom-Leek-Pea Soup with Lemon-Ginger Creme Fraiche** `fn:3/k69SAF5EKed5P42zjZyPYtlM9mU8O` — 7 ingredients · 3 steps
2. **Chicken Soup Casserole** `ar:fQ0XqiG86ncmmZqKsawKAGIRbsoJEdK` — 7 ingredients · 4 steps
3. **Creamy Soup Steaks** `ar:1q93DC577c8ErAdOb8gBMsh.rPpX.gK` — 3 ingredients · 2 steps
4. **Grilled Cheese Dippers with Spicy Tomato-Cheese Soup** `fn:SD7P/x9UbxPas7jSjwpiYPZyGRJFVY.` — 9 ingredients · 4 steps
5. **Easy Tomato and Eggplant Soup** `ar:n2tu.ZCecCqXhf08h4jaAxr/BSZBTe2` — 3 ingredients · 2 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): cache hit | LLM call 2 (voice): 2626 ms, 470 prompt tok, ok | Voice: ok

---

**> no dairy**

`rule parser · high-confidence pattern` · 0 LLM calls · 7732 ms · type=search · total=1940

> 🗣 I found 1940 soup recipes with your active filters for no dairy. Some options include Easy Tomato and Eggplant Soup, Pasta with Lentil Soup Sauce, and Onion Soup Pork Chops. You might also like Ramen Noodle Bratwurst Soup or Shrimp and Spinach Noodle Soup.

**1,940 recipes** match _matches 'soup'; no dairy (contains)_; showing 10.
_1,940 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Easy Tomato and Eggplant Soup** `ar:n2tu.ZCecCqXhf08h4jaAxr/BSZBTe2` — 3 ingredients · 2 steps
2. **Pasta with Lentil Soup Sauce** `ar:Jmsh.A0i63y6Zi11UM7lksx6zpVMuhO` — 3 ingredients · 4 steps
3. **Onion Soup Pork Chops** `ar:SElFIO.OYAHFyoKc.ZsQZYFtu2PYYlW` — 4 ingredients · 2 steps
4. **Ramen Noodle Bratwurst Soup** `fn:EHnJBr9Z8D2niILWYnUPY1sWg2fRrJ6` — 4 ingredients · 3 steps
5. **Shrimp and Spinach Noodle Soup** `fn:/VK2/JQEslSIBM99qKIMO2zqr/Zdb5W` — 5 ingredients · 3 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (voice): cache hit | Voice: ok

---

**> also at most 4 steps**

`rule parser · high-confidence pattern` · 0 LLM calls · 3730 ms · type=search · total=1397

> 🗣 I found some great soup recipes that fit your active filters of no dairy and at most four steps. You might enjoy Easy Tomato and Eggplant Soup, Pasta with Lentil Soup Sauce, Onion Soup Pork Chops, Ramen Noodle Bratwurst Soup, or Shrimp and Spinach Noodle Soup.

**1,397 recipes** match _matches 'soup'; no dairy (contains); at most 4 steps_; showing 10.
_1,397 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Easy Tomato and Eggplant Soup** `ar:n2tu.ZCecCqXhf08h4jaAxr/BSZBTe2` — 3 ingredients · 2 steps
2. **Pasta with Lentil Soup Sauce** `ar:Jmsh.A0i63y6Zi11UM7lksx6zpVMuhO` — 3 ingredients · 4 steps
3. **Onion Soup Pork Chops** `ar:SElFIO.OYAHFyoKc.ZsQZYFtu2PYYlW` — 4 ingredients · 2 steps
4. **Ramen Noodle Bratwurst Soup** `fn:EHnJBr9Z8D2niILWYnUPY1sWg2fRrJ6` — 4 ingredients · 3 steps
5. **Shrimp and Spinach Noodle Soup** `fn:/VK2/JQEslSIBM99qKIMO2zqr/Zdb5W` — 5 ingredients · 3 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · Also no gluten?
Trace: LLM call 1 (voice): cache hit | Voice: ok

---

**> dairy is fine now**

`rule parser · high-confidence pattern` · 1 LLM calls · 638 ms · type=search · total=3926

> 🗣 I found several soup recipes for you while keeping the active filter for a maximum of 4 steps, noting that dairy restrictions were removed. You might enjoy Mushroom-Leek-Pea Soup with Lemon-Ginger Creme Fraiche, Chicken Soup Casserole, Creamy Soup Steaks, Grilled Cheese Dippers with Spicy Tomato-Cheese Soup, or Easy Tomato and Eggplant Soup.

> Removed restriction(s): dairy.
**3,926 recipes** match _matches 'soup'; at most 4 steps_; showing 10.
_3,926 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Mushroom-Leek-Pea Soup with Lemon-Ginger Creme Fraiche** `fn:3/k69SAF5EKed5P42zjZyPYtlM9mU8O` — 7 ingredients · 3 steps
2. **Chicken Soup Casserole** `ar:fQ0XqiG86ncmmZqKsawKAGIRbsoJEdK` — 7 ingredients · 4 steps
3. **Creamy Soup Steaks** `ar:1q93DC577c8ErAdOb8gBMsh.rPpX.gK` — 3 ingredients · 2 steps
4. **Grilled Cheese Dippers with Spicy Tomato-Cheese Soup** `fn:SD7P/x9UbxPas7jSjwpiYPZyGRJFVY.` — 9 ingredients · 4 steps
5. **Easy Tomato and Eggplant Soup** `ar:n2tu.ZCecCqXhf08h4jaAxr/BSZBTe2` — 3 ingredients · 2 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · Also no dairy?
Trace: LLM call 1 (voice): 1503 ms, 548 prompt tok, ok | Voice: ok

---

**> the second one**

`rule parser · high-confidence pattern` · 1 LLM calls · 4 ms · type=recipe

> 🗣 I found Chicken Soup Casserole matching your search for soup with a maximum of four steps. Enjoy making this recipe!

**Chicken Soup Casserole** `ar:fQ0XqiG86ncmmZqKsawKAGIRbsoJEdK` — 7 ingredients · 4 steps (opened on the right).
- 4 steps (limit 4)

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (voice): 2320 ms, 267 prompt tok, ok | Voice: ok

---

**> why did you pick this one?**

`rule parser · high-confidence pattern` · 0 LLM calls · 0 ms · type=text

**Chicken Soup Casserole** `ar:fQ0XqiG86ncmmZqKsawKAGIRbsoJEdK` is #2 of 3,926 matches (matches 'soup'; at most 4 steps): its title contains the exact phrase, and those rank first; ties go to recipe id. Checks: 4 steps (limit 4).

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---
