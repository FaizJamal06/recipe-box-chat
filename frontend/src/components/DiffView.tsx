import type { Candidate, Payload, Strength, TierCounts } from "../api";

/** Substitution view (PRD 8): the evidence table (Evidence tab) and the side-by-side diff (Results tab).
 *  Every count, lift and id comes from the payload; the only model text is the labelled "Predicted" block. */

const STRENGTH_STYLE: Record<Strength, string> = {
  Strong: "border-ok/40 bg-ok-soft text-ok", Moderate: "border-amber/40 bg-amber-soft text-amber",
  Weak: "border-grey/40 bg-grey-soft text-grey", None: "border-bad/30 bg-bad-soft text-bad" };

function Badge({ s }: { s: Strength }) {
  return <span className={`rounded-full border px-2 py-px text-[11px] font-semibold ${STRENGTH_STYLE[s]}`}>{s}</span>;
}

function IdLink({ id, onOpen }: { id: string; onOpen: (id: string) => void }) {
  return <button type="button" onClick={() => onOpen(id)} title={id}
                 className="rounded bg-grey-soft px-1 font-mono text-[10.5px] hover:text-tomato cursor-pointer">{id.slice(0, 9)}…</button>;
}

/** The tier that drives the grade (L1 for Strong, L2 for Moderate, else the first tier with any support). */
function tierOf(c: Candidate): ["L1" | "L2" | "L3", TierCounts] | null {
  const k = c.strength === "Strong" ? "L1" : c.strength === "Moderate" ? "L2"
    : (["L1", "L2", "L3"] as const).find((t) => c.tiers[t].support > 0);
  return k ? [k, c.tiers[k]] : null;
}

const rate = (k: number, n: number) => <>{k}/{n}<span className="text-ink-soft"> ({n ? (100 * k / n).toFixed(1) : 0}%)</span></>;

export function EvidenceTable({ p, onOpen }: { p: Payload; onOpen: (id: string) => void }) {
  const tiers = p.tiers ?? {};
  return <>
    <p className="text-[12px] text-ink-soft">{p.l1_note} · L2 {tiers.L2?.toLocaleString()} similar ·
      L3 {tiers.L3?.toLocaleString()} {p.context} recipes. Method: Calculation tab.</p>
    {(p.parts ?? []).map((part) => (
      <section key={part.item} className="rounded-lg border border-rule bg-paper p-3">
        <h3 className="font-display text-[14px] font-semibold">Removing {part.item}
          <span className="ml-2 text-[12px] font-normal text-ink-soft">{part.affected.join("; ")} · role: {part.roles.join(", ") ||
            "unknown (model reasoning, not dataset evidence)"}</span></h3>
        <div className="scroll-thin mt-2 overflow-x-auto">
          <table className="w-full min-w-[40rem] text-left text-[12px]">
            <thead className="text-[10.5px] uppercase tracking-[0.08em] text-ink-soft">
              <tr>{["Candidate", "Role", "Tier", "Rate without", "Rate with", "Lift", "Strength", "Supporting"].map((h) =>
                <th key={h} className="py-1 pr-2 font-semibold">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-rule/70">{part.candidates.map((c) => {
              const t = tierOf(c);
              return <tr key={c.name} className={c.name === part.chosen ? "bg-ok-soft/40" : ""}>
                <td className="py-1.5 pr-2"><b>{c.name}</b>{c.name === part.chosen && <span className="ml-1 text-ok">✓ chosen</span>}
                  <div className="text-[10.5px] text-ink-soft">{c.label}{c.conflicting && " · ⚠ conflicting"}</div></td>
                <td className="pr-2">{c.roles.join(", ") || "—"}</td>
                <td className="pr-2">{t ? t[0] + (c.explicit.length && t[0] === "L1" ? " (explicit)" : "") : "—"}</td>
                {c.kind === "omit" ? <td colSpan={3} className="pr-2 text-[11px]">{t ? <>{rate(t[1].n_without, t[1].n_without + t[1].n_with)} go without it</> : "—"}</td> : <>
                <td className="pr-2 font-mono text-[11px]">{t ? rate(t[1].support, t[1].n_without) : "0"}</td>
                <td className="pr-2 font-mono text-[11px]">{t ? rate(t[1].in_with, t[1].n_with) : "—"}</td>
                <td className="pr-2 font-mono text-[11px]">{t ? t[1].lift : "—"}</td></>}
                <td className="pr-2"><Badge s={c.strength} /></td>
                <td><div className="flex flex-wrap gap-1">{c.ids.slice(0, 3).map((id) => <IdLink key={id} id={id} onOpen={onOpen} />)}</div></td>
              </tr>;
            })}</tbody>
          </table>
        </div>
        {part.because && <p className="mt-1.5 text-[12px]">{part.because}</p>}
        {part.candidates.filter((c) => c.name === part.chosen).flatMap((c) => c.snippets).map((s) =>
          <p key={s.id} className="mt-1.5 text-[12px] text-ink-soft">“{s.text}” <IdLink id={s.id} onOpen={onOpen} /></p>)}
        {part.rejected.length > 0 && <details className="mt-2 text-[12px]">
          <summary className="cursor-pointer text-ink-soft hover:text-ink">Rejected candidates ({part.rejected.length})</summary>
          <ul className="mt-1 space-y-0.5">{part.rejected.map((r) => <li key={r.name}><b>{r.name}</b> <span className="text-bad">— {r.reason}</span></li>)}</ul>
        </details>}
      </section>))}
  </>;
}

function Col({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="min-w-0"><h4 className="mb-1 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-ink-soft">{title}</h4>
    <ul className="space-y-1">{children}</ul></div>;
}

export function DiffView({ p }: { p: Payload }) {
  const a = p.adaptation;
  if (!a) return <section className="rounded-lg border border-dashed border-rule bg-paper p-3 text-[13px]">
    <h3 className="font-display font-semibold">No adaptation</h3>
    {[p.question, ...(p.notes ?? [])].filter(Boolean).map((n, i) => <p key={i} className="mt-1 text-ink-soft">{n}</p>)}
  </section>;
  const del = "rounded bg-bad-soft px-1 text-bad line-through decoration-bad/70";
  const add = "rounded bg-ok-soft px-1 text-ok";
  return (
    <section className="space-y-3 rounded-lg border border-rule bg-paper p-3 text-[12.5px]">
      <h3 className="font-display text-[14px] font-semibold">Adapted: {p.target?.title}</h3>
      {a.caveat && <p className="rounded border border-warn/30 bg-warn-soft px-2 py-1 text-warn">⚠ {a.caveat}</p>}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Col title="Original ingredients">{a.ingredients.filter((d) => d.op !== "add").map((d, i) =>
          <li key={i}><span className={d.op === "remove" ? del : ""}>{d.text}</span></li>)}</Col>
        <Col title="Adapted ingredients">{a.ingredients.filter((d) => d.op !== "remove").map((d, i) =>
          <li key={i}><span className={d.op === "add" ? add : ""}>{d.text}</span></li>)}</Col>
        <Col title="Original steps">{a.steps.map((s) =>
          <li key={s.n}><span className={s.changed ? del : ""}>{s.n}. {s.old}</span></li>)}</Col>
        <Col title={`Adapted steps (${a.source === "model" ? "model, validated" : "deterministic swap"})`}>{a.steps.map((s) =>
          <li key={s.n}><span className={s.changed ? add : ""}>{s.n}. {s.text}</span>
            {s.changed && s.reason && <div className="text-[11px] text-ink-soft">↳ {s.reason}</div>}</li>)}</Col>
      </div>
      {a.prep.length > 0 && <p><b>Prep:</b> {a.prep.join(" ")}</p>}
      <div className="rounded border border-ok/30 p-2"><h4 className="mb-1 font-semibold text-ok">Verified from dataset</h4>
        <ul className="list-disc space-y-0.5 pl-4">{a.verified.map((v, i) => <li key={i}>{v}</li>)}</ul></div>
      <div className="rounded border border-amber/30 p-2"><h4 className="mb-1 font-semibold text-amber">Predicted (not verifiable from recipe text)</h4>
        <p>{a.predicted ?? <span className="text-ink-soft">{a.predicted_status}</span>}</p></div>
      {a.gate.length ? <p className="rounded border-2 border-bad/50 bg-bad-soft p-2 font-semibold text-bad">
        ✗ Not safe for your restrictions: {a.gate.map((g) => `${g.what} (${g.reason})`).join("; ")}</p>
        : (p.restrictions ?? []).length > 0 && <p className="text-ok">✓ Every adapted ingredient verified free of: {p.restrictions!.join(", ")}</p>}
      {a.safety_line && <p className="text-[11.5px] text-ink-soft">{a.safety_line}</p>}
    </section>
  );
}
