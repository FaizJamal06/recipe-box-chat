import { useState } from "react";
import type { Calc, ChatResponse } from "../api";
import { DiffView } from "./DiffView";
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

function CalcBlock({ c }: { c: Calc }) {
  const [copied, setCopied] = useState(false);
  const value = Array.isArray(c.value) ? `${c.value.length} rows` : typeof c.value === "number" ? c.value.toLocaleString() : String(c.value);
  return (
    <section className="rounded-lg border border-rule bg-paper p-4">
      <div className="mb-1 flex items-baseline justify-between">
        <h3 className="font-display text-base font-semibold capitalize">{c.label}</h3>
        <span className="font-display text-2xl text-tomato">{value}</span>
      </div>
      <dl className="divide-y divide-rule/70">
        <Field k="Filters">{c.filters}</Field>
        <Field k="N analyzed">{c.n_analyzed.toLocaleString()}</Field>
        <Field k="Denominator">{c.denominator.toLocaleString()} valid recipes</Field>
        <Field k="Method">{c.method}</Field>
        {c.normalization_note && <Field k="Normalization">{c.normalization_note}</Field>}
        {c.notes.map((n, i) => <Field key={i} k="Note">{n}</Field>)}
      </dl>
      <div className="mt-2">
        <div className="mb-1 flex items-center justify-between text-[11px] uppercase tracking-[0.12em] text-ink-soft">
          <span>SQL (exact query)</span>
          <button type="button" className="normal-case tracking-normal hover:text-tomato cursor-pointer"
                  onClick={() => navigator.clipboard?.writeText(c.sql).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1200); })}>
            {copied ? "copied ✓" : "copy"}</button>
        </div>
        <pre className="scroll-thin max-h-56 overflow-auto whitespace-pre-wrap break-all rounded bg-ink px-3 py-2 font-mono text-[11.5px] leading-relaxed text-cream">{c.sql}</pre>
      </div>
    </section>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="mt-10 text-center text-[13px] text-ink-soft">{children}</p>;
}

/** Right panel: Results (cards) · Calculation (filters, N, denominator, method, SQL, normalization) ·
 *  Evidence (per-recipe proof lines; T3 table in M5) · Trace (pipeline steps). */
export function EvidencePanel({ resp, tab, setTab, onOpen }: { resp: ChatResponse | null; tab: Tab;
                                                              setTab: (t: Tab) => void; onOpen: (id: string) => void }) {
  const p = resp?.payload;
  return (
    <aside className="flex min-h-0 flex-col border-l border-rule bg-cream/60">
      <nav className="flex gap-1 border-b border-rule px-4 pt-3" role="tablist">
        {TABS.map(([t, label]) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
                  className={`-mb-px rounded-t-md border-b-2 px-3 pb-2 pt-1 text-[13.5px] cursor-pointer ${tab === t
                    ? "border-tomato font-semibold text-ink" : "border-transparent text-ink-soft hover:text-ink"}`}>{label}</button>
        ))}
      </nav>
      <div className="scroll-thin min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {!p && <Empty>Results, calculations and evidence for each answer appear here.</Empty>}
        {p && tab === "results" && <>
          {p.cards.length > 0 && <div className="flex items-center justify-between gap-2">
            <span className="text-[12px] text-ink-soft">{p.total !== undefined ? `${p.total.toLocaleString()} eligible · showing ${p.cards.length}` : `${p.cards.length} shown`}</span>
            <Legend /></div>}
          {p.cards.map((c, i) => <RecipeCard key={c.id} card={c} rank={p.cards.length > 1 ? i + 1 : undefined} onOpen={onOpen} />)}
          {p.rows && p.rows.length > 0 && <ol className="space-y-1 rounded-lg border border-rule bg-paper p-4 text-[13.5px]">
            {p.rows.map((r) => <li key={r.name} className="flex justify-between"><span>{r.name}</span>
              <span className="font-mono text-ink-soft">{r.recipes.toLocaleString()}</span></li>)}</ol>}
          {p.type === "match" && p.cards.length === 0 && <>
            <div className="rounded-lg border-2 border-bad/50 bg-bad-soft p-3 text-[13.5px] font-semibold text-bad">
              No recipe satisfies all hard constraints</div>
            {(p.alternatives ?? []).map((a) => (
              <section key={a.violates} className="rounded-lg border border-dashed border-bad/50 p-3">
                <h3 className="mb-2 text-[12.5px] font-semibold text-bad">⚠ NOT a match — violates “{a.violates}”</h3>
                <div className="space-y-2">{a.cards.length ? a.cards.map((c) => <RecipeCard key={c.id} card={c} onOpen={onOpen} flagged />)
                  : <p className="text-[12.5px] text-ink-soft">None, even with this constraint relaxed.</p>}</div>
              </section>))}
          </>}
          {p.cards.length === 0 && !p.rows?.length && p.type !== "match" && <Empty>No recipes in this answer.</Empty>}
        </>}
        {p && tab === "calc" && ((p.calc ?? []).length ? p.calc!.map((c, i) => <CalcBlock key={i} c={c} />)
          : <Empty>This answer ran no calculation.</Empty>)}
        {p && tab === "evidence" && <>
          {p.cards.filter((c) => c.chips.length).map((c) => (
            <section key={c.id} className="rounded-lg border border-rule bg-paper p-3">
              <button type="button" onClick={() => onOpen(c.id)} className="font-display font-semibold hover:text-tomato cursor-pointer">{c.title.trim()}</button>
              <ul className="mt-1.5 space-y-1 text-[12.5px]">{c.chips.map((ch, i) =>
                <li key={i} className="flex gap-2"><span className={`mt-1 h-2 w-2 shrink-0 rounded-full border ${CHIP_STYLE[ch.kind]}`} />
                  <span><span className="font-medium">{ch.label}</span>{ch.detail !== ch.label && <span className="text-ink-soft"> — {ch.detail}</span>}</span></li>)}</ul>
            </section>))}
          <DiffView />
        </>}
        {p && tab === "trace" && resp && (
          <ol className="relative space-y-3 border-l-2 border-rule pl-4 text-[13px]">
            {resp.trace.map((t, i) => <li key={i} className="relative"><span className="absolute -left-[1.4rem] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-cream bg-tomato" />
              <span className="font-medium">{t.split(":")[0]}</span><span className="text-ink-soft">{t.slice(t.indexOf(":"))}</span></li>)}
          </ol>)}
      </div>
    </aside>
  );
}
