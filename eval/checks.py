"""Every assertion key of eval/cases.yaml (used by eval/run.py). Each check re-reads the DB with its own SQL
(recipe_tags, ingredient_lines, unverified), never with the code under test, and returns '' or a failure message.
"""


class Checker:
    """Every assertion key of cases.yaml: check(key, value, response, ctx) -> '' or a failure message."""

    def __init__(self, con, ds, stats, substitute, oracle):
        self.con, self.ds, self.stats, self.sub, self.oracle = con, ds, stats, substitute, oracle

    def ids(self, p):
        return [c["id"] for c in p.get("cards", [])]

    def q(self, sql, args=()):
        return {r for r, in self.con.execute(sql, args)}

    def tagged(self, ids, tag, levels=("contains",)):
        ph = ",".join("?" * len(ids))
        return self.q(f"SELECT recipe_id FROM recipe_tags WHERE tag = ? AND level IN ({','.join('?' * len(levels))}) "
                      f"AND recipe_id IN ({ph})", (tag, *levels, *ids)) if ids else set()

    def unverified(self, ids, tag):
        ph = ",".join("?" * len(ids))
        return self.q(f"SELECT recipe_id FROM unverified WHERE tag = ? AND recipe_id IN ({ph})", (tag, *ids)) if ids else set()

    def check(self, key, v, r, ctx) -> str:
        p, ids = r["payload"], self.ids(r["payload"])
        parts = p.get("parts") or []
        part = parts[0] if parts else {}
        a = p.get("adaptation")
        tags = lambda: v if isinstance(v, list) else [v]
        if key == "type":
            return "" if p["type"] == v else f"type is {p['type']}, expected {v}"
        if key == "total_gt":
            return "" if p.get("total", 0) > v else f"total {p.get('total')} is not > {v}"
        if key == "total_eq":
            return "" if p.get("total") == v else f"total {p.get('total')} != {v}"
        if key == "n_cards_ge":
            return "" if len(ids) >= v else f"{len(ids)} cards < {v}"
        if key == "ids_exist":
            rid = [p["recipe"]["id"]] if p["type"] == "recipe" else []
            got = ids + rid
            ok = self.q(f"SELECT id FROM recipes WHERE valid = 1 AND id IN ({','.join('?' * len(got))})", got) if got else set()
            return "" if got and ok == set(got) else f"ids not valid recipes: {sorted(set(got) - ok)[:3]}"
        if key == "max_steps_le":
            bad = [c["id"] for c in p["cards"] if c["n_steps"] > v]
            return "" if not bad else f"{len(bad)} results have more than {v} steps"
        if key == "all_results_lack_tag":
            bad = {t: self.tagged(ids, t) for t in tags()}
            bad = {t: b for t, b in bad.items() if b}
            return "" if not bad else f"results contain {', '.join(bad)} (e.g. {next(iter(next(iter(bad.values()))))})"
        if key == "strict_results_lack_tag":
            bad = self.tagged(ids, v, ("contains", "may_contain")) | self.unverified(ids, v)
            return "" if not bad else f"{len(bad)} results contain, may contain or can't be verified for {v}"
        if key == "verified_before_unverified":
            unv = self.unverified(ids, v)
            flags = [i in unv for i in ids]
            return "" if flags == sorted(flags) else "an unverified result is ranked above a verified one"
        if key == "all_results_lack_ingredient":
            t = self.stats.term(v, self.ds)
            ph = ",".join("?" * len(ids))
            bad = self.q(f"SELECT recipe_id FROM ingredient_lines WHERE is_alt = 0 AND is_header = 0 AND "
                         f"(canonical = ? OR family = ?) AND recipe_id IN ({ph})", (t.canonical, t.family, *ids)) if ids else set()
            return "" if not bad else f"{len(bad)} results contain {v}"
        if key == "all_results_lack_ingredient_broad":  # family + its broad list ('no sugar' also drops marshmallow)
            from app.normalize import BROAD
            t = self.stats.term(v, self.ds)
            names = [t.family, *BROAD.get(t.family, [])]
            ph, nh = ",".join("?" * len(ids)), ",".join("?" * len(names))
            bad = self.q(f"SELECT recipe_id FROM ingredient_lines WHERE is_alt = 0 AND is_header = 0 AND (family IN ({nh}) "
                         f"OR canonical IN ({nh})) AND recipe_id IN ({ph})", (*names, *names, *ids)) if ids else set()
            return "" if not bad else f"{len(bad)} results contain {v} (broad)"
        if key == "dropped":
            got = [d["item"] for d in p.get("dropped", [])]
            miss = [x for x in v if not any(x in g for g in got)]
            return "" if not miss else f"{miss} not dropped (dropped: {got})"
        if key == "recipe_is_result":
            prev = ctx.get("last_cards") or []
            want = prev[v - 1] if len(prev) >= v else None
            got = p.get("recipe", {}).get("id")
            return "" if want and got == want else f"opened {got}, result #{v} was {want}"
        if key == "stat_equals_oracle":
            got = {c["label"]: c["value"] for c in p.get("calc", [])}
            bad = []
            for mode, path in v.items():
                exp = self.oracle
                for k in path.split("."):
                    exp = exp[k]
                if got.get(mode) != exp:
                    bad.append(f"{mode} {got.get(mode)} != oracle {exp}")
            return "; ".join(bad)
        if key == "rank_equals_oracle":
            return "" if ids == self.oracle[v] else f"ids {ids} != oracle {self.oracle[v]}"
        if key == "no_match":
            return "" if (p.get("total") == 0) == v else f"total is {p.get('total')}"
        if key == "alternatives_flagged":
            alts = p.get("alternatives") or []
            return "" if alts and all(x["violates"] for x in alts) else "no flagged alternatives"
        if key == "match_has_qty_chip":
            return "" if any(ch["kind"] in ("ok", "violation") for c in p["cards"] for ch in c["chips"]) else \
                "no quantity check on any result"
        if key == "refusal":
            return "" if (p["type"] == "unsupported") == v else f"type is {p['type']}, not a refusal"
        if key == "reply_contains":
            text = (r["reply_md"] + " " + (r.get("voice") or "")).lower()
            miss = [w for w in v if w.lower() not in text]
            return "" if not miss else f"reply lacks {miss}"
        if key == "state_tags_include":
            miss = [t for t in v if t not in r["state"]["exclude_tags"]]
            return "" if not miss else f"restrictions lack {miss} (have {r['state']['exclude_tags']})"
        if key == "state_tags_exclude":
            extra = [t for t in v if t in r["state"]["exclude_tags"]]
            return "" if not extra else f"restrictions still have {extra}"
        if key == "sub_strength_in":
            return "" if part.get("strength") in v else f"strength {part.get('strength')} not in {v}"
        if key == "sub_chosen_not":
            return "" if part.get("chosen") not in v else f"chose {part.get('chosen')}"
        if key == "sub_rejected":
            names = [x["name"] for x in part.get("rejected", [])]
            miss = [n for n in v if n not in names]
            return "" if not miss else f"{miss} not rejected (rejected: {names[:5]})"
        if key == "sub_cited_ids_valid":
            return self.cited(parts)
        if key == "sub_dataset_only":
            vocab = self.q("SELECT canonical FROM vocab WHERE recipe_count >= ?", (self.ds_min,))
            bad = [c["name"] for pt in parts for c in pt["candidates"]
                   if c["kind"] != "user" and c["name"] not in vocab and c["name"] not in self.sub.DECLARED]
            return "" if not bad else f"not dataset ingredients: {bad}"
        if key == "sub_steps_valid":
            if not a:
                return "no adaptation"
            bad = [s["n"] for s in a["steps"] if not s["changed"] and s["text"] != s["old"]]
            return "" if not bad else f"steps {bad} changed but not marked"
        if key == "sub_gate_fails":
            return "" if a and a["gate"] else "the final gate passed (expected a failure)"
        if key == "sub_gate_passes":
            return "" if a and not a["gate"] else f"gate: {(a or {}).get('gate')}"
        if key == "sub_question":
            return "" if bool(p.get("question")) == v else f"question: {p.get('question')!r}"
        if key == "sub_adapted":
            return "" if bool(a) == v else f"adaptation {'missing' if v else 'built'}"
        if key == "llm_calls_le":
            n = r["planner"]["calls"] + r["planner"]["cache_hits"]
            return "" if n <= v else f"{n} LLM calls"
        if key == "state_eq":  # {field: value}: query_text, max_steps, have, ...
            bad = [f"{f} is {r['state'][f]!r}, expected {x!r}" for f, x in v.items() if r["state"][f] != x]
            return "; ".join(bad)
        if key == "state_diets_exclude":
            got = [d["name"] for d in r["state"]["diets"]]
            return "" if not set(v) & set(got) else f"diets still have {sorted(set(v) & set(got))}"
        if key == "suggestions_ge":
            return "" if len(r["suggestions"]) >= v else f"{len(r['suggestions'])} suggestion chips < {v}"
        if key == "suggestion_contains":
            labels = [s["label"].lower() for s in r["suggestions"]]
            return "" if any(v.lower() in x for x in labels) else f"no chip with '{v}' (chips: {labels})"
        if key == "reply_lacks":
            text = r["reply_md"].lower()
            bad = [w for w in v if w.lower() in text]
            return "" if not bad else f"reply has {bad}"
        if key == "sub_chosen_eq":
            return "" if part.get("chosen") == v else f"chose {part.get('chosen')}, expected {v}"
        if key == "sub_steps_lack":  # adapted steps and kept/added lines never mention the omitted item
            if not a:
                return "no adaptation"
            import re
            rx = re.compile(rf"\b{re.escape(v)}", re.I)
            bad = [f"step {s['n']}" for s in a["steps"] if rx.search(s["text"])]
            bad += [d["text"] for d in a["ingredients"] if d["op"] != "remove" and rx.search(d["text"])]
            return "" if not bad else f"still mentions {v}: {bad[:3]}"
        return f"unknown assertion {key}"

    def cited(self, parts) -> str:
        """Every cited id (chosen candidate's supporting + explicit ids) is valid, lacks the removed item and
        contains the candidate: own SQL, not evidence.cited."""
        bad = []
        for pt in parts:
            c = next((x for x in pt["candidates"] if x["name"] == pt["chosen"]), None)
            if not c:
                continue
            spec = self.sub.spec_for(pt["item"], self.ds)
            for rid in set(c["ids"] + c["explicit"]):
                if spec.tag:
                    has = self.q("SELECT recipe_id FROM recipe_tags WHERE recipe_id = ? AND tag = ? AND level = "
                                 "'contains'", (rid, spec.tag))
                else:
                    col, val = ("family", spec.family) if spec.canonical == spec.family else ("canonical", spec.canonical)
                    has = self.q(f"SELECT recipe_id FROM ingredient_lines WHERE recipe_id = ? AND is_alt = 0 AND "
                                 f"{col} = ?", (rid, val))
                uses = {rid} if c["kind"] == "omit" else self.q(  # 'omit it': the recipe only has to lack the item
                    "SELECT recipe_id FROM ingredient_lines WHERE recipe_id = ? AND is_alt = 0 AND (canonical "
                    "= ? OR family = ? OR canonical LIKE ?)", (rid, c["name"], c["name"], f"% {c['name']}"))
                if has or not uses:
                    bad.append(rid)
        return "" if not bad else f"{len(bad)} cited ids fail the re-check: {bad[:3]}"
