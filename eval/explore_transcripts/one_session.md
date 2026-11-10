# Exploratory run: one session

## one session (all messages)

**> hi there**

`rule parser · high-confidence pattern` · 0 LLM calls · 0 ms · type=text

Hi! I can find recipes, filter them by what you can't eat, rank them by the ingredients you have, and count things across the collection. What are you in the mood for?

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---

**> wat can u do?**

`rule parser · high-confidence pattern` · 0 LLM calls · 1 ms · type=text

I work only from this collection of 122,933 valid recipes. I can find dishes ('penne pasta, no dairy'), suggest recipes for what you have ('I have eggs and rice'), explain why a recipe ranked where it did, and answer counts and rankings ('how many recipes are dairy-free?'), always with the calculation shown.

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---

**> find me a chiken curry recipe**

`LLM · gemini-3.5-flash-lite` · 0 LLM calls · 66 ms · type=search · total=752

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

`rule parser · high-confidence pattern` · 0 LLM calls · 1327 ms · type=search · total=472

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

`rule parser · high-confidence pattern` · 0 LLM calls · 114 ms · type=recipe

> 🗣 I found Chicken Curry and Potatoes for your chicken curry search with no gluten. It has 9 ingredients and 3 steps, and the no gluten check passed on all 9 lines.

**Chicken Curry and Potatoes** `ar:IcSnM3/i0XN5mUY9.JHJ18ul3ZuRARS` — 9 ingredients · 3 steps (opened on the right).
- no gluten: 0 gluten-tagged lines; checked 9 lines

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (voice): cache hit | Voice: ok

---

**> why that one?**

`rule parser · high-confidence pattern` · 0 LLM calls · 1 ms · type=text

**Chicken Curry and Potatoes** `ar:IcSnM3/i0XN5mUY9.JHJ18ul3ZuRARS` is #3 of 472 matches (matches 'chicken curry'; no gluten (contains)): its title contains the exact phrase, and those rank first; ties go to recipe id. Checks: no gluten: 0 gluten-tagged lines; checked 9 lines.

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---

**> no nuts either pls**

`rule parser · high-confidence pattern` · 0 LLM calls · 2093 ms · type=search · total=379

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

**> i got eggs spinach and feta, what can i make**

`rule parser · high-confidence pattern` · 1 LLM calls · 2734 ms · type=match · total=7251

> Kept your restrictions (gluten, peanut, tree_nut): they're about you, not the dish. Say e.g. 'dairy is fine now' to drop one.
Your ingredients: **egg, spinach, feta cheese** · staples assumed: salt, black pepper, water
Hard constraints: _no gluten (contains); no peanut (contains); no tree_nut (contains); uses at least 1 of your ingredients_
**Top 5** of 7,251 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)
1. **Spinach, Tomato, and Feta Egg White Omelette** `ar:LuPRsd3uZDNT/ecut.zOzOvlKDADary` — 6 ingredients · 2 steps · score **3.80** · matched 3, extra 2
2. **Challenge Feel-Good Frittata** `epi:MZzyHBss1.zzCwkNL/GW29z0wNxdQlq` — 5 ingredients · 2 steps · score **3.80** · matched 3, extra 2
3. **Spinach and Feta Turkey Burgers** `ar:wF16LXMBTJAPjEMrE6nO6lOvyNk8ktW` — 5 ingredients · 3 steps · score **3.70** · matched 3, extra 2
4. **Potato, Spinach, and Feta Gratin** `epi:WuhP18FpOn/s.Lzg3QVlDAsu6ciOsWS` — 7 ingredients · 3 steps · score **3.70** · matched 3, extra 2
5. **My Big Fat Greek Omelet** `ar:aX5BX5FpbnXHSK9qjaxJkJUuGCmIA7.` — 8 ingredients · 3 steps · score **2.70** · matched 3, extra 3

Suggestions: Show steps for #1 · Why #1? · Fewer extra ingredients?
Trace: LLM call 1 (voice): 4013 ms, timeout | Voice: template (timeout)

---

**> exclude eggs too**

`rule parser · high-confidence pattern` · 1 LLM calls · 406 ms · type=match · total=1413

Your ingredients: **spinach, feta cheese** · staples assumed: salt, black pepper, water
> Removed from your ingredients because 'no egg' excludes it: egg
Hard constraints: _no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); uses at least 1 of your ingredients_
**Top 5** of 1,413 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)
1. **Simplistic Pepper Salad** `ar:kDY6w2OqndG6UAdF3yuOmyA1fdln8FK` — 4 ingredients · 3 steps · score **2.70** · matched 2, extra 1
2. **Steamed Baby Spinach** `fn:/hxM4nGEcORulr.SvZl8Koq9TrWGT4O` — 2 ingredients · 2 steps · score **1.80** · matched 1, extra 0
3. **Spinach-Stuffed Flounder with Mushrooms and Feta** `ar:102.I5fcUsJNczOr0ozbU9gek08IupG` — 4 ingredients · 6 steps · score **1.40** · matched 2, extra 2
4. **Greens and Craisins®** `ar:x/NcUYHvlMenxNiC3sZpVez447yDwGm` — 5 ingredients · 1 step · score **0.90** · matched 2, extra 3
5. **Spinach Salad With Ease** `ar:oOJiCPvpi1PUaiVagWsxwpYpLeo50sm` — 6 ingredients · 2 steps · score **0.80** · matched 2, extra 3

Suggestions: Show steps for #1 · Why #1? · Fewer extra ingredients?
Trace: LLM call 1 (voice): 4008 ms, timeout | Voice: template (timeout)

---

**> fewer ingredients??**

`rule parser · LLM timeout` · 1 LLM calls · 6400 ms · type=match · total=1413

Your ingredients: **spinach, feta cheese** · staples assumed: salt, black pepper, water
> Removed from your ingredients because 'no egg' excludes it: egg
Hard constraints: _no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); uses at least 1 of your ingredients_
**Top 5** of 1,413 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)
1. **Simplistic Pepper Salad** `ar:kDY6w2OqndG6UAdF3yuOmyA1fdln8FK` — 4 ingredients · 3 steps · score **2.20** · matched 2, extra 1
2. **Steamed Baby Spinach** `fn:/hxM4nGEcORulr.SvZl8Koq9TrWGT4O` — 2 ingredients · 2 steps · score **1.80** · matched 1, extra 0
3. **Spinach-Stuffed Flounder with Mushrooms and Feta** `ar:102.I5fcUsJNczOr0ozbU9gek08IupG` — 4 ingredients · 6 steps · score **0.40** · matched 2, extra 2
4. **Wilted Baby Spinach** `epi:fSN2RnHAcCTngvTA9BwadDYAqWJ4jTO` — 2 ingredients · 2 steps · score **0.30** · matched 1, extra 1
5. **Bacon-Wrapped Feta** `ar:x6Tl5BeH/b8/tFc/uV44oiBdOuWIXI2` — 2 ingredients · 3 steps · score **0.20** · matched 1, extra 1

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): 6001 ms, timeout | Voice: template (LLM not used this turn)

---

**> Gujarati dishes**

`guard · no LLM needed` · 1 LLM calls · 536 ms · type=search · total=2

> There's no cuisine field in this dataset, so 'gujarati' is approximated by recipe titles containing: gujarati, dhokla, thepla, khandvi, undhiyu, handvo, kadhi, khichdi, fafda, shrikhand; plus dish names suggested by the LLM: gujarati kadhi. Dishes not named that way are missed.
**2 recipes** match _title has any of: gujarati, dhokla, thepla, khandvi, undhiyu, handvo, kadhi, khichdi, fafda, shrikhand, gujarati kadhi; no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains)_; showing 2.
_2 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Gujarati Kadhi** `ar:EqPvfzr0rK/342K3CgyGS3pj1IlFjIG` — 16 ingredients · 2 steps
2. **Spicy Indian (Gujarati) Green Beans** `ar:ppf.Z5A8oM5aAeykKP1zqcKiSRs/mfe` — 8 ingredients · 2 steps

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (cuisine): cache hit | LLM call 2 (voice): 4041 ms, timeout | Voice: template (timeout)

---

**> any italian recipes without meat**

`guard · no LLM needed` · 1 LLM calls · 6169 ms · type=search · total=369

> There's no cuisine field in this dataset, so 'italian' is approximated by recipe titles containing: italian, risotto, lasagna, carbonara, bolognese, pesto, gnocchi, bruschetta, tiramisu, cacciatore, piccata, osso buco, focaccia; plus dish names suggested by the LLM: spaghetti carbonara, margherita pizza, lasagna bolognese, chicken parmigiana, risotto alla milanese. Dishes not named that way are missed.
**369 recipes** match _title has any of: italian, risotto, lasagna, carbonara, bolognese, pesto, gnocchi, bruschetta, tiramisu, cacciatore, piccata, osso buco, focaccia, spaghetti carbonara, margherita pizza, lasagna bolognese, chicken parmigiana, risotto alla milanese; no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); no meat (contains)_; showing 10.
_369 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Poaching Pate a Choux to Form Gnocchi** `fn:RZYwi68KkxmPlDcLyUstIBXA/D361tS` — 1 ingredient · 2 steps
2. **Tiramisu Bon Bons** `fn:mUa05iGww9Jq7KdjTh5UeU0IX2lEDsq` — 2 ingredients · 2 steps
3. **Mustard-Mascarpone Bruschetta** `epi:v6fi7lc9RcRaecdXze7NoPC6ylGkPRK` — 5 ingredients · 2 steps
4. **Easy Foil Packet Baked Fish Piccata** `ar:Gk6CkP7T9gL.4gxUMo05NScBYXITvHK` — 8 ingredients · 3 steps
5. **Piccata Mustard** `fn:1uyaC7mEbza8zkYXyoRgsdkijHa6FSG` — 7 ingredients · 2 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (cuisine): cache hit | LLM call 2 (voice): 4001 ms, timeout | Voice: template (timeout)

---

**> paneer ki koi recipe batao**

`LLM unavailable, ran as keyword search` · 1 LLM calls · 8268 ms · type=search · total=25

> I couldn't use the language model, so I ran your message as a keyword search for 'paneer' in titles and ingredients.
**25 recipes** match _matches 'paneer'; no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); no meat (contains)_; showing 10.
_25 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Homemade Paneer** `fn:BZ/GlKdZJYmNmWEYt5/0/RjG2wO5BNa` — 2 ingredients · 2 steps
2. **Palak Paneer (Spinach Curry)** `ar:BA.VxUUY3ghornOATh4lsqtfcnlrpoS` — 12 ingredients · 3 steps
3. **Quick Paneer Makhani** `ar:sR2muE1pkAy0eneqXMcDemvQrbhVAQy` — 12 ingredients · 2 steps
4. **Shahi Paneer** `ar:QPUMY5mFY16c5gZlIA3RD3K1hpFolPO` — 14 ingredients · 2 steps
5. **Shahi Paneer (Royal Cheese)** `ar:yFDIurV1Pgp.BS9ZgBJKfn7FWY7Zh5i` — 13 ingredients · 3 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): 6011 ms, timeout | Voice: template (LLM not used this turn)

---

**> something vegan for dinner**

`rule parser · high-confidence pattern` · 1 LLM calls · 4196 ms · type=search · total=16205

**16,205 recipes** match _no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); no meat (contains); no dairy (contains); no fish (contains); no shellfish (contains)_; showing 10.
_16,205 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Best Lemonade Ever** `ar:..3M3xsVPQLnncQ2oYzCyhGjNe/6EB2` — 3 ingredients · 2 steps
2. **Sicilian Lentil Pasta Sauce** `ar:..6gl/0GIzSugrbvy6kHyxEHMMP4h9K` — 11 ingredients · 3 steps
3. **Salsa de Tomatillos Como Las Asadas y Big Star** `ar:..G2iuRLT7oseNmkKbjqAgbdB1G5IBC` — 11 ingredients · 5 steps
4. **Minty Mint Chutney** `ar:..hYtxdDoy5Rp..pLgIj2mKKfvp1jPa` — 5 ingredients · 1 step
5. **7UP Cherry Merry Mint Punch** `ar:.0/AfXAViFvl4QESfOPdR7lN4y.ru/i` — 4 ingredients · 2 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (voice): 4009 ms, timeout | Voice: template (timeout)

---

**> vegan chicken curry**

`rule parser · LLM timeout` · 1 LLM calls · 6022 ms · type=text

“chicken curry” clashes with your restriction “no meat” (chicken contains meat). Should I look for a version without chicken, or drop the “no meat” restriction?

Suggestions: Drop “no meat” · Curry without chicken
Trace: LLM call 1 (planner): 6002 ms, timeout | Voice: template (LLM not used this turn)

---

**> im allergic to shellfish, find a paella recipe**

`rule parser · LLM timeout` · 1 LLM calls · 9369 ms · type=search · total=7

**7 recipes** match _matches 'paella'; no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); no meat (contains); no dairy (contains); no fish (contains); no shellfish (contains)_; showing 7.
_7 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Easy Mushroom Vegetable Paella** `fn:jVxhyTUi6j/Geq1Rnx0DbqAC9j8i1g2` — 7 ingredients · 3 steps
2. **Paella Style Rice** `fn:1lnaKFQ9Gz3Gxz6b16KbjiKYJrbaRRq` — 6 ingredients · 5 steps
3. **Vegetable Paella** `ar:UY6e5bgJQ0/mJKOZlDPy3RH1zsN6PzK` — 10 ingredients · 2 steps
4. **Vegetable Paella** `fn:Qtx.uRJG7Zf03JO2c0VTyjp3Zv3sYda` — 18 ingredients · 5 steps
5. **Paella Rice Salad** `fn:HMSFFYRr6YRzlj7fGSTmsPoAOoxo5ya` — 11 ingredients · 2 steps
_… 2 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): 6011 ms, timeout | Voice: template (LLM not used this turn)

---

**> gluten free pasta recipes**

`rule parser · LLM timeout` · 1 LLM calls · 10890 ms · type=search · total=22

**22 recipes** match _matches 'pasta'; no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); no meat (contains); no dairy (contains); no fish (contains); no shellfish (contains)_; showing 10.
_22 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Spaghetti Pasta Sauce** `ar:dmg1NI9QFfZ/Ol3ijXZZlXEmMAhXCOu` — 6 ingredients · 5 steps
2. **Ruffle-Edged Pasta with Cauliflower and Parsley Sauce** `epi:M1FxbRvWuSGZ26HO7U7ZysZuASc4Tk2` — 5 ingredients · 2 steps
3. **Low-Carb Zucchini Pasta** `ar:c8lKQEPnadVNuPshzVQwe4U1z.AfDHa` — 4 ingredients · 2 steps
4. **Veggie Pasta Minus the Pasta** `ar:pelkTlLxVl8SYKs2Wd/ngf39nBiBwaq` — 13 ingredients · 4 steps
5. **Simple Delicious Pasta Sauce** `ar:AlRT92kHplnxIe/I7LMm0rZjpCNqlQS` — 4 ingredients · 3 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): 6013 ms, timeout | Voice: template (LLM not used this turn)

---

**> something quick for dinner**

`rule parser · high-confidence pattern` · 0 LLM calls · 0 ms · type=text

There's no cook-time field, but I can keep it short: want recipes with at most four steps, or do you have a dish in mind?

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---

**> whats the weather like today**

`LLM unavailable, ran as keyword search` · 1 LLM calls · 7306 ms · type=search · total=2

> I couldn't use the language model, so I ran your message as a keyword search for 'weather' in titles and ingredients.
**2 recipes** match _matches 'weather'; no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); no meat (contains); no dairy (contains); no fish (contains); no shellfish (contains)_; showing 2.
_2 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Damn the Weather I** `epi:POB7DGmjFTcdEuLoeAh.itcdMu4s.7W` — 5 ingredients · 2 steps
2. **Damn the Weather II** `epi:Jpa2OpLtvv32.WH4sVrAn03oWpnYf9S` — 6 ingredients · 2 steps

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): 6010 ms, timeout | Voice: template (LLM not used this turn)

---

**> tell me a joke**

`LLM unavailable, ran as keyword search` · 1 LLM calls · 6013 ms · type=search · total=0

> I couldn't use the language model, so I ran your message as a keyword search for 'tell joke' in titles and ingredients.
> No recipe matches those words, and without the language model I can't tell what you meant. I can only help with recipes: try 'find a pasta recipe' or 'I have eggs and rice'.
**0 recipes** match _matches 'tell joke'; no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); no meat (contains); no dairy (contains); no fish (contains); no shellfish (contains)_; showing 0.
_0 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
No recipe satisfies every restriction; none were relaxed.

Suggestions: 
Trace: LLM call 1 (planner): 6008 ms, timeout | Voice: template (LLM not used this turn)

---

**> how many calories in a big mac**

`guard · no LLM needed` · 0 LLM calls · 0 ms · type=unsupported

Not in the dataset: there are no nutrition fields (no calories, macros, sodium, sugar or fibre), so I can't compute or estimate them from this data.
I can list a recipe's ingredient lines instead; pick one from a search first.

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---

**> how many recipes have garlic but no onion**

`rule parser · LLM timeout` · 1 LLM calls · 7977 ms · type=stats

Recipes where: _contains garlic AND no onion_
- **strict**: **16,762** of 122,933 valid recipes = **13.64%**
- **broad**: **13,638** of 122,933 valid recipes = **11.09%**
_16,762 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
Normalization: strict garlic = the 'garlic' family (garlic, cloves garlic, garlic paste, bulb garlic, pureed garlic, garlic bulb, ...); broad adds dried garlic, garlic flake, garlic powder, garlic salt, granulated garlic | strict onion = the 'onion' family (onion, red onion, sweet onion, pearl onion, maui onion, cipollini onion, ...); broad adds dried onion, french-fried onion, fried onion, green onion, onion flake, onion powder, onion salt, shallot
Method: Counted valid recipes matching all filters (strict); percentage = count / valid recipes. A recipe contains X when one of its required ingredient items is X (an 'or' alternative alone does not count).
_SQL: see the Calculation tab._

Suggestions: Fewest steps? · Top ingredients?
Trace: LLM call 1 (planner): 6001 ms, timeout | Voice: template (LLM not used this turn)

---

**> which 3 recipes have the most ingredients**

`rule parser · LLM timeout` · 1 LLM calls · 6890 ms · type=stats

**3 recipes** (all valid recipes), ingredients descending:
1. **Eggplant Lasagna with Marinated Red Pepper and Arugula Salad** `fn:VyOSR27DV9/2XWc04AaULLRHh4go0C.` — 82 ingredients · 25 steps
2. **Pizza Four Ways** `fn:39v09iqRtZlSrp6sB93u7RM2RORZOUa` — 78 ingredients · 28 steps
3. **Rebuilt Louisiana Seafood Platter** `fn:M37ZUEX5jp0z5ZXvGyuplXGzos2slMy` — 76 ingredients · 11 steps
_Analyzed: 122,933 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
Method: Sorted all 122,933 matching valid recipes by n_ingredients desc, ties broken by n_steps ascending, then recipe id ascending.
_SQL: see the Calculation tab._

Suggestions: Show steps for #1 · Dairy-free count? · Top ingredients?
Trace: LLM call 1 (planner): 6006 ms, timeout | Voice: template (LLM not used this turn)

---

**> average steps for recipes with chicken**

`rule parser · LLM timeout` · 1 LLM calls · 6567 ms · type=stats

Mean number of steps (contains chicken): **4.85**
_Analyzed: 8,770 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
Normalization: strict chicken = the 'chicken' family (chicken breast, chicken, chicken thigh, chicken wing, rotisserie chicken, chicken leg, ...); broad adds chicken bouillon, chicken broth, ground chicken
> Note: Ingredient filters use the strict definition; the broad definition would match 16,497 recipes.
Method: mean of n_steps over 8,770 matching valid recipes. Steps = effective n_steps: non-empty newline-separated steps, except when the instructions are one paragraph of 2+ sentences, where sentences are counted instead (PRD 4.4).
_SQL: see the Calculation tab._

Suggestions: Fewest steps? · Top ingredients?
Trace: LLM call 1 (planner): 6002 ms, timeout | Voice: template (LLM not used this turn)

---

**> how many recipes are nut free**

`rule parser · LLM timeout` · 1 LLM calls · 7198 ms · type=stats

Recipes where: _tree_nut/peanut-free recipes_
- **lenient**: **104,333** of 122,933 valid recipes = **84.87%**
- **strict**: **103,419** of 122,933 valid recipes = **84.13%**
_104,333 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
Normalization: Tag levels (recipe_tags): contains = a required item has it; may_contain = label-dependent (e.g. margarine, chocolate chips); alt = only in an 'or' option that has a tag-free alternative, so the recipe can be made without it (counted as free).
Method: lenient = valid recipes with no tree_nut/peanut line at level 'contains' (may_contain and alt count as free); strict = no tree_nut/peanut line at 'contains' or 'may_contain'; percentage = count / valid recipes.
_SQL: see the Calculation tab._

Suggestions: Dairy-free count? · Top ingredients?
Trace: LLM call 1 (planner): 6013 ms, timeout | Voice: template (LLM not used this turn)

---

**> find a soup recipe**

`rule parser · LLM timeout` · 1 LLM calls · 11192 ms · type=search · total=306

**306 recipes** match _matches 'soup'; no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); no meat (contains); no dairy (contains); no fish (contains); no shellfish (contains)_; showing 10.
_306 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Diet Soup** `ar:PWL.N9Je5VqX34xbR6K3yHqlXYpR1Ge` — 8 ingredients · 3 steps
2. **Favorite Lentil Soup** `ar:nS3wSrHSeLnFM0qwtKEzmRkA7O1Lkfa` — 8 ingredients · 4 steps
3. **Spiced Tomato Soup** `ar:R/6ar6KuCtMGBrT/kkawO2g3jd4Q6rS` — 8 ingredients · 2 steps
4. **Italian Zucchini Soup** `ar:AeT7sjnn6nPtJsHNAMGWMAO5GPJvmBW` — 9 ingredients · 2 steps
5. **Nobu's Miso Soup** `fn:fLJsH2kJmGQXSNcGdU9fX9Mto.qkkWu` — 3 ingredients · 7 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (planner): 6012 ms, timeout | Voice: template (LLM not used this turn)

---

**> no dairy**

`rule parser · high-confidence pattern` · 1 LLM calls · 3606 ms · type=search · total=306

**306 recipes** match _matches 'soup'; no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); no meat (contains); no dairy (contains); no fish (contains); no shellfish (contains)_; showing 10.
_306 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Diet Soup** `ar:PWL.N9Je5VqX34xbR6K3yHqlXYpR1Ge` — 8 ingredients · 3 steps
2. **Favorite Lentil Soup** `ar:nS3wSrHSeLnFM0qwtKEzmRkA7O1Lkfa` — 8 ingredients · 4 steps
3. **Spiced Tomato Soup** `ar:R/6ar6KuCtMGBrT/kkawO2g3jd4Q6rS` — 8 ingredients · 2 steps
4. **Italian Zucchini Soup** `ar:AeT7sjnn6nPtJsHNAMGWMAO5GPJvmBW` — 9 ingredients · 2 steps
5. **Nobu's Miso Soup** `fn:fLJsH2kJmGQXSNcGdU9fX9Mto.qkkWu` — 3 ingredients · 7 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · At most 5 steps?
Trace: LLM call 1 (voice): 4008 ms, timeout | Voice: template (timeout)

---

**> also at most 4 steps**

`rule parser · high-confidence pattern` · 1 LLM calls · 4342 ms · type=search · total=224

**224 recipes** match _matches 'soup'; no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); no meat (contains); no dairy (contains); no fish (contains); no shellfish (contains); at most 4 steps_; showing 10.
_224 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Diet Soup** `ar:PWL.N9Je5VqX34xbR6K3yHqlXYpR1Ge` — 8 ingredients · 3 steps
2. **Favorite Lentil Soup** `ar:nS3wSrHSeLnFM0qwtKEzmRkA7O1Lkfa` — 8 ingredients · 4 steps
3. **Spiced Tomato Soup** `ar:R/6ar6KuCtMGBrT/kkawO2g3jd4Q6rS` — 8 ingredients · 2 steps
4. **Italian Zucchini Soup** `ar:AeT7sjnn6nPtJsHNAMGWMAO5GPJvmBW` — 9 ingredients · 2 steps
5. **Strawberry Champagne Soup** `ar:VL7o0LWNGtoV.XxHY7SCktOnkT1UU/y` — 4 ingredients · 4 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1?
Trace: LLM call 1 (voice): 4012 ms, timeout | Voice: template (timeout)

---

**> dairy is fine now**

`rule parser · high-confidence pattern` · 1 LLM calls · 3751 ms · type=search · total=574

> Removed restriction(s): dairy.
**574 recipes** match _matches 'soup'; no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); no meat (contains); no fish (contains); no shellfish (contains); at most 4 steps_; showing 10.
_574 of 122,933 valid recipes (125,164 records; invalid: no_ingredients 1,629, empty_record 517, no_title 52, no_instructions 33)_
1. **Mushroom-Leek-Pea Soup with Lemon-Ginger Creme Fraiche** `fn:3/k69SAF5EKed5P42zjZyPYtlM9mU8O` — 7 ingredients · 3 steps
2. **Slow Cooker Cream of Broccoli Soup** `ar:I/ngk2scxu0wil/N.roIjR3GHl9ypLu` — 7 ingredients · 4 steps
3. **Instant Creamy Onion Soup** `ar:HmqDJRCTgVOTAIDBrBmKqT1CxrhBzoq` — 5 ingredients · 3 steps
4. **Best Broccoli Cheddar Soup** `ar:iTtz9ADqhtihIIscOU7k0pHiblAA8.O` — 5 ingredients · 4 steps
5. **Jazzed-Up Tomato Soup** `fn:URy2Gfl7q9mTOG3AUbQoHqO8KpWxL9q` — 5 ingredients · 4 steps
_… 5 more in the Results panel._

Suggestions: Show steps for #1 · Why #1? · Also no dairy?
Trace: LLM call 1 (voice): 4006 ms, timeout | Voice: template (timeout)

---

**> the second one**

`rule parser · high-confidence pattern` · 1 LLM calls · 248 ms · type=recipe

**Slow Cooker Cream of Broccoli Soup** `ar:I/ngk2scxu0wil/N.roIjR3GHl9ypLu` — 7 ingredients · 4 steps (opened on the right).
- no gluten: '1 (10.75 ounce) can condensed cream of mushroom soup' may contain gluten (check the label)
- no peanut: 0 peanut-tagged lines; checked 7 lines
- no tree_nut: 0 tree_nut-tagged lines; checked 7 lines
- no egg: 0 egg-tagged lines; checked 7 lines
- no meat: 0 meat-tagged lines; checked 7 lines
- no fish: 0 fish-tagged lines; checked 7 lines
- no shellfish: 0 shellfish-tagged lines; checked 7 lines
- 4 steps (limit 4)

Suggestions: Why this one? · Next recipe
Trace: LLM call 1 (voice): 4015 ms, timeout | Voice: template (timeout)

---

**> why did you pick this one?**

`rule parser · high-confidence pattern` · 0 LLM calls · 0 ms · type=text

**Slow Cooker Cream of Broccoli Soup** `ar:I/ngk2scxu0wil/N.roIjR3GHl9ypLu` is #2 of 574 matches (matches 'soup'; no gluten (contains); no peanut (contains); no tree_nut (contains); no egg (contains); no meat (contains); no fish (contains); no shellfish (contains); at most 4 steps): its title contains the exact phrase, and those rank first; ties go to recipe id. Checks: no gluten: '1 (10.75 ounce) can condensed cream of mushroom soup' may contain gluten (check the label); no peanut: 0 peanut-tagged lines; checked 7 lines; no tree_nut: 0 tree_nut-tagged lines; checked 7 lines; no egg: 0 egg-tagged lines; checked 7 lines; no meat: 0 meat-tagged lines; checked 7 lines; no fish: 0 fish-tagged lines; checked 7 lines; no shellfish: 0 shellfish-tagged lines; checked 7 lines; 4 steps (limit 4).

Suggestions: Find a pasta recipe · Cook with what I have · Dairy-free count
Trace: Voice: template (answer type keeps the template)

---
