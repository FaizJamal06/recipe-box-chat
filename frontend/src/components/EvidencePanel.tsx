import { useEffect, useState } from "react";
import type { Calc, ChatResponse } from "../api";
import { DiffView, EvidenceTable } from "./DiffView";
import { CHIP_STYLE, RecipeCard } from "./RecipeCard";

export type Tab = "results" | "calc" | "evidence" | "trace";
const TABS: [Tab, string][] = [["results", "Results"], ["calc", "Calculation"], ["evidence", "Evidence"], ["trace", "Trace"]];

function Legend() {
  const items: [keyof typeof CHIP_STYLE, string][] = [["matched", "matched"], ["extra", "extra"], ["unused", "unused"],
    ["violation", "violation"], ["may_contain", "⚠ may contain"]];
  return <div className="flex flex-wrap gap-1.5 text-[11px]">{items.map(([k, l]) =>
    <span key={k} className={`rounded-full border px-2 py-px ${CHIP_STYLE[k]}`}>{l}</span>)}</div>;
}

function Field({ k, children }: { k: string; children: React.ReactNode }) {
  return <div className="grid grid-cols-[7.5rem_1fr] gap-3 py-1.5 text-[13px]">
    <dt className="text-ink-soft">{k}</dt><dd className="min-w-0">{children}</dd></div>;
}

/** One sentence first: what was computed, over what. */
function summary(c: Calc): string {
  const n = (x: number) => x.toLocaleString();
  if (typeof c.value === "number" && (c.label === "strict" || c.label === "broad"))
    return `${n(c.value)} of ${n(c.denominator)} recipes (${(100 * c.value / c.denominator).toFixed(2)}%), counting ${c.label === "strict" ? "the ingredient itself" : "its processed forms too"}.`;
  if (c.label === "search" || c.label === "match")
    return `${n(c.value as number)} recipes pass every filter, out of ${n(c.denominator)}.`;
  if (c.label === "substitution") return `${n(c.value as number)} usable replacement candidates, graded on ${n(c.n_analyzed)} recipes.`;
  const v = Array.isArray(c.value) ? `${c.value.length} recipes` : typeof c.value === "number" ? n(c.value) : String(c.value);
  return `${c.label[0].toUpperCase() + c.label.slice(1)}: ${v}, computed over ${n(c.n_analyzed)} recipes.`;
}

function CalcBlock({ c, dev }: { c: Calc; dev: boolean }) {
  const [copied, setCopied] = useState(false);
  const value = Array.isArray(c.value) ? `${c.value.length} rows` : typeof c.value === "number" ? c.value.toLocaleString() : String(c.value);
  return (
    <section className="rounded-lg border border-rule bg-paper p-4">
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <h3 className="font-display text-base font-semibold capitalize">{c.label}</h3>
        <span className="font-display text-2xl text-tomato">{value}</span>
      </div>
      <p className="text-[13.5px] text-ink">{summary(c)}</p>
      <dl className="mt-1 divide-y divide-rule/70">
        <Field k="How">{c.method}</Field>
        {c.notes.map((n, i) => <Field key={i} k="Note">{n}</Field>)}
        {dev && <Field k="Filters">{c.filters}</Field>}
        {dev && <Field k="N analyzed">{c.n_analyzed.toLocaleString()}</Field>}
        {dev && <Field k="Denominator">{c.denominator.toLocaleString()} valid recipes</Field>}
        {dev && c.normalization_note && <Field k="Normalization">{c.normalization_note}</Field>}
      </dl>
      {dev && c.sql && <details className="mt-2">
        <summary className="cursor-pointer text-[11px] uppercase tracking-[0.12em] text-ink-soft hover:text-ink">Show query</summary>
        <div className="mt-1 flex justify-end text-[11px] text-ink-soft">
          <button type="button" className="hover:text-tomato cursor-pointer"
                  onClick={() => navigator.clipboard?.writeText(c.sql!).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1200); })}>
            {copied ? "copied ✓" : "copy"}</button>
        </div>
        <pre className="scroll-thin max-h-56 overflow-auto whitespace-pre-wrap break-all rounded bg-ink px-3 py-2 font-mono text-[11.5px] leading-relaxed text-cream">{c.sql}</pre>
      </details>}
    </section>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="mt-10 text-center text-[13px] text-ink-soft">{children}</p>;
}

/** Right panel: Results (cards) · Calculation (filters, N, denominator, method, SQL, normalization) ·
 *  Evidence (per-recipe proof lines; substitution evidence table) · Trace (pipeline steps). */
export function EvidencePanel({ resp, tab, setTab, dev, onOpen, onStrict, mobile = false }: { resp: ChatResponse | null;
  tab: Tab; setTab: (t: Tab) => void; dev: boolean; onOpen: (id: string) => void; onStrict: () => void; mobile?: boolean }) {
  const p = resp?.payload;
  const [showMore, setShowMore] = useState(false);
  useEffect(() => { setShowMore(false); }, [resp]);  // fold again for every new answer
  const nUnv = p?.n_unverified ?? 0;
  return (
    <aside className={mobile ? "flex min-h-0 flex-1 flex-col" : "flex min-h-0 flex-col border-l border-rule bg-cream/60"}>
      <nav className="chip-row flex gap-1 overflow-x-auto border-b border-rule px-4 pt-3 phone:px-2 phone:pt-0" role="tablist">
        {TABS.filter(([t]) => dev || t !== "trace").map(([t, label]) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
                  className={`-mb-px shrink-0 rounded-t-md border-b-2 px-3 pb-2 pt-1 text-[13.5px] cursor-pointer phone:min-h-11 phone:text-[15px] ${tab === t
                    ? "border-tomato font-semibold text-ink" : "border-transparent text-ink-soft hover:text-ink"}`}>{label}</button>
        ))}
      </nav>
      <div className="scroll-thin min-h-0 flex-1 space-y-3 overflow-y-auto p-4 phone:p-3 phone:pb-[calc(1.5rem+env(safe-area-inset-bottom))]">
        {!p && <Empty>Results, calculations and evidence for each answer appear here.</Empty>}
        {p && tab === "results" && <>
          {p.type === "substitute" && <DiffView p={p} mobile={mobile} />}
          {p.cards.length > 0 && p.type !== "substitute" && <div className="flex items-center justify-between gap-2">
            <span className="text-[12px] text-ink-soft">{p.total !== undefined ? `${(p.total - nUnv).toLocaleString()} ${nUnv ? "fully verified" : "eligible"} · showing ${p.cards.length}` : `${p.cards.length} shown`}</span>
            <Legend /></div>}
          {(p.type === "substitute" ? p.cards.slice(0, 1) : p.cards).map((c, i) =>
            <RecipeCard key={c.id} card={c} rank={p.cards.length > 1 && p.type !== "substitute" ? i + 1 : undefined} onOpen={onOpen} dev={dev} />)}
          {nUnv > 0 && <div className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg border border-warn/30 bg-warn-soft px-3 py-2 text-[12.5px] text-warn"
                            title="Unknown is not safe: these recipes name an ingredient the allergen lexicon doesn't know">
            <span>⚠ {nUnv.toLocaleString()} more recipe{nUnv === 1 ? " matches" : "s match"} but {nUnv === 1 ? "has" : "have"} an ingredient I couldn't verify.</span>
            <button type="button" onClick={onStrict} className="underline-offset-2 hover:underline cursor-pointer">Turn on strict to hide them</button>
            {(p.more_cards ?? []).length > 0 && <><span aria-hidden>·</span>
              <button type="button" aria-expanded={showMore} onClick={() => setShowMore(!showMore)}
                      className="font-semibold underline-offset-2 hover:underline cursor-pointer">
                {showMore ? "hide them" : `show ${p.more_cards!.length === nUnv ? "them" : `the top ${p.more_cards!.length}`}`}</button></>}
          </div>}
          {showMore && (p.more_cards ?? []).map((c, i) =>
            <RecipeCard key={c.id} card={c} rank={p.cards.length + i + 1} onOpen={onOpen} warned dev={dev} />)}
          {p.rows && p.rows.length > 0 && <ol className="space-y-1 rounded-lg border border-rule bg-paper p-4 text-[13.5px]">
            {p.rows.map((r) => <li key={r.name} className="flex justify-between"><span>{r.name}</span>
              <span className="font-mono text-ink-soft">{r.recipes.toLocaleString()}</span></li>)}</ol>}
          {p.type === "match" && p.total === 0 && <>
            <div className="rounded-lg border-2 border-bad/50 bg-bad-soft p-3 text-[13.5px] font-semibold text-bad">
              No recipe satisfies all hard constraints</div>
            {(p.alternatives ?? []).map((a) => (
              <section key={a.violates} className="rounded-lg border border-dashed border-bad/50 p-3">
                <h3 className="mb-2 text-[12.5px] font-semibold text-bad">⚠ NOT a match — violates “{a.violates}”</h3>
                <div className="space-y-2">{a.cards.length ? a.cards.map((c) => <RecipeCard key={c.id} card={c} onOpen={onOpen} flagged dev={dev} />)
                  : <p className="text-[12.5px] text-ink-soft">None, even with this constraint relaxed.</p>}</div>
              </section>))}
          </>}
          {p.cards.length === 0 && !nUnv && !p.rows?.length && p.type !== "match" && <Empty>No recipes in this answer.</Empty>}
        </>}
        {p && tab === "calc" && ((p.calc ?? []).length ? p.calc!.map((c, i) => <CalcBlock key={i} c={c} dev={dev} />)
          : <Empty>This answer ran no calculation.</Empty>)}
        {p && tab === "evidence" && <>
          {p.cards.filter((c) => c.chips.length).map((c) => (
            <section key={c.id} className="rounded-lg border border-rule bg-paper p-3">
              <button type="button" onClick={() => onOpen(c.id)} className="font-display font-semibold hover:text-tomato cursor-pointer">{c.title.trim()}</button>
              <ul className="mt-1.5 space-y-1 text-[12.5px]">{c.chips.map((ch, i) =>
                <li key={i} className="flex gap-2"><span className={`mt-1 h-2 w-2 shrink-0 rounded-full border ${CHIP_STYLE[ch.kind]}`} />
                  <span><span className="font-medium">{ch.label}</span>{ch.detail !== ch.label && <span className="text-ink-soft"> — {ch.detail}</span>}</span></li>)}</ul>
            </section>))}
          {p.type === "substitute" && <EvidenceTable p={p} onOpen={onOpen} mobile={mobile} />}
        </>}
        {p && dev && tab === "trace" && resp && (
          <ol className="relative space-y-3 border-l-2 border-rule pl-4 text-[13px]">
            {resp.trace.map((t, i) => <li key={i} className="relative"><span className="absolute -left-[1.4rem] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-cream bg-tomato" />
              <span className="font-medium">{t.split(":")[0]}</span><span className="text-ink-soft">{t.slice(t.indexOf(":"))}</span></li>)}
          </ol>)}
      </div>
    </aside>
  );
}
