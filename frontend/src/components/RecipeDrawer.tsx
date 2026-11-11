import { useEffect, useState } from "react";
import { api, type Recipe } from "../api";
import { IdPill, plural, SourceBadge } from "./RecipeCard";

const label = (t: string) => ({ tree_nut: "tree nuts", root_veg: "onion/garlic/root veg" } as Record<string, string>)[t] ?? t;
const TAG_TONE: Record<string, string> = { contains: "bg-bad-soft text-bad", may_contain: "bg-warn-soft text-warn",
                                          alt: "bg-grey-soft text-grey" };

/** Slide-over with the original recipe (verbatim lines and steps), its tags and the parsed view. */
export function RecipeDrawer({ id, onClose }: { id: string | null; onClose: () => void }) {
  const [r, setR] = useState<Recipe | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (!id) return;
    setR(null); setErr("");
    api.recipe(id).then(setR).catch((e) => setErr(String(e.message || e)));
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [id, onClose]);
  if (!id) return null;
  return (
    <div className="fixed inset-0 z-30 flex justify-end">
      <button type="button" aria-label="Close recipe" onClick={onClose} className="absolute inset-0 bg-ink/25 backdrop-blur-[1px]" />
      <article role="dialog" aria-modal className="scroll-thin relative h-full w-[min(560px,92vw)] overflow-y-auto border-l border-rule bg-paper px-7 py-6 shadow-2xl">
        <button type="button" onClick={onClose} className="absolute right-4 top-4 rounded-full px-2 text-xl text-ink-soft hover:bg-grey-soft hover:text-ink cursor-pointer" aria-label="Close">×</button>
        {err && <p className="text-bad">Couldn't load the recipe: {err}</p>}
        {!r && !err && <p className="text-ink-soft">Loading…</p>}
        {r && <>
          <div className="flex items-center gap-2 text-[12px]"><SourceBadge source={r.source} /><IdPill id={r.id} /></div>
          <h2 className="mt-2 pr-8 font-display text-[28px] font-semibold leading-tight">{r.title.trim()}</h2>
          <p className="mt-1 text-[13px] text-ink-soft">{plural(r.n_ingredients, "ingredient")} · {plural(r.n_steps, "step")}
            {r.paragraph && " (one paragraph; steps counted as sentences)"}</p>
          {Object.keys(r.tags).length > 0 && <div className="mt-3 flex flex-wrap gap-1">{Object.entries(r.tags).map(([t, lv]) =>
            <span key={t} className={`rounded-full px-2 py-px text-[11.5px] ${TAG_TONE[lv] ?? ""}`}>{t}: {lv.replace("_", " ")}</span>)}</div>}
          {Object.keys(r.unverified ?? {}).length > 0 && <p className="mt-2 rounded border border-warn/30 bg-warn-soft px-2.5 py-1.5 text-[12px] text-warn"
            title="Unknown is not safe: these lines name nothing the allergen lexicon knows, so strict mode excludes the recipe for these tags.">
            ⚠ Couldn't verify for {Object.keys(r.unverified).map(label).join(", ")}: {[...new Set(Object.values(r.unverified).flat())].map((x) => `'${x}'`).join(", ")}</p>}
          <h3 className="mt-6 border-b border-rule pb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-tomato">Ingredients (original)</h3>
          <ul className="mt-2 space-y-1.5 text-[14.5px]">{r.ingredients.map((x, i) => <li key={i} className="flex gap-2"><span className="text-tomato">·</span>{x}</li>)}</ul>
          <h3 className="mt-6 border-b border-rule pb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-tomato">Steps</h3>
          <ol className="mt-2 space-y-3 text-[14.5px] leading-relaxed">{r.steps.map((s, i) =>
            <li key={i} className="flex gap-3"><span className="font-display text-lg leading-6 text-tomato">{i + 1}</span><span>{s}</span></li>)}</ol>
          <details className="mt-6 text-[12.5px]">
            <summary className="cursor-pointer text-ink-soft hover:text-ink">Parsed view ({r.parsed.length} rows)</summary>
            <table className="mt-2 w-full border-collapse font-mono text-[11.5px]">
              <thead><tr className="text-left text-ink-soft"><th className="py-1">#</th><th>canonical</th><th>qty</th><th>unit</th><th>flags</th></tr></thead>
              <tbody>{r.parsed.map((p, i) => <tr key={i} className="border-t border-rule/70" title={p.raw}>
                <td className="py-1 pr-2 text-ink-soft">{p.line_no}</td><td className="pr-2">{p.canonical ?? "—"}</td>
                <td className="pr-2">{p.qty ?? ""}</td><td className="pr-2">{p.unit ?? ""}</td>
                <td className="text-ink-soft">{[p.is_alt && "alt", p.is_header && "header", p.is_not_food && "not food"].filter(Boolean).join(", ")}</td></tr>)}</tbody>
            </table>
          </details>
        </>}
      </article>
    </div>
  );
}
