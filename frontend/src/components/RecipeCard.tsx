import { useState } from "react";
import type { Card, Chip, ChipKind } from "../api";

export const CHIP_STYLE: Record<ChipKind, string> = {
  matched: "bg-ok-soft text-ok border-ok/25",
  ok: "bg-ok-soft/60 text-ok border-ok/20",
  extra: "bg-amber-soft text-amber border-amber/25",
  unused: "bg-grey-soft text-grey border-grey/25",
  violation: "bg-bad-soft text-bad border-bad/30",
  may_contain: "bg-warn-soft text-warn border-warn/30",
};
const PREFIX: Partial<Record<ChipKind, string>> = { ok: "✓ ", may_contain: "⚠ " };
const SOURCE: Record<string, string> = { ar: "AR", epi: "EPI", fn: "FN" };
export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

export function ChipView({ chip }: { chip: Chip }) {
  return (
    <span title={chip.detail}
          className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11.5px] leading-4 ${CHIP_STYLE[chip.kind]}`}>
      {PREFIX[chip.kind]}{chip.label}
    </span>
  );
}

/** Mono recipe id: click opens the recipe, the small button copies the id. */
export function IdPill({ id, onOpen }: { id: string; onOpen?: (id: string) => void }) {
  const [copied, setCopied] = useState(false);
  const copy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard?.writeText(id).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1200); });
  };
  return (
    <span className="inline-flex items-center gap-0.5 align-baseline rounded bg-grey-soft/70 font-mono text-[11.5px] text-ink-soft">
      <button type="button" onClick={(e) => { e.stopPropagation(); onOpen?.(id); }}
              className="px-1.5 py-px hover:text-tomato hover:underline cursor-pointer" title="Open recipe">{id}</button>
      <button type="button" onClick={copy} title="Copy id" aria-label={`Copy ${id}`}
              className="px-1 py-px border-l border-rule hover:text-tomato cursor-pointer">{copied ? "✓" : "⧉"}</button>
    </span>
  );
}

export function SourceBadge({ source }: { source: string }) {
  return <span className="rounded border border-ink/15 px-1.5 text-[10px] font-semibold tracking-wider text-ink-soft">
    {SOURCE[source] ?? source.toUpperCase()}</span>;
}

/** Score breakdown as a small signed bar (match results). */
function ScoreBar({ parts }: { parts: Record<string, number> }) {
  const total = Object.values(parts).reduce((a, b) => a + Math.abs(b), 0) || 1;
  return (
    <div className="mt-2">
      <div className="flex h-1.5 overflow-hidden rounded-full bg-grey-soft">
        {Object.entries(parts).filter(([, v]) => v).map(([k, v]) => (
          <div key={k} title={`${k} ${v > 0 ? "+" : ""}${v.toFixed(1)}`} style={{ width: `${(Math.abs(v) / total) * 100}%` }}
               className={v > 0 ? "bg-ok" : k === "extra" ? "bg-amber" : k === "short" ? "bg-bad" : "bg-grey"} />
        ))}
      </div>
      <div className="mt-1 flex gap-3 text-[11px] text-ink-soft font-mono">
        {Object.entries(parts).map(([k, v]) => <span key={k}>{k} {v > 0 ? "+" : ""}{v.toFixed(1)}</span>)}
      </div>
    </div>
  );
}

export function RecipeCard({ card, rank, onOpen, flagged }: { card: Card; rank?: number; onOpen: (id: string) => void;
                                                              flagged?: boolean }) {
  return (
    <article onClick={() => onOpen(card.id)}
             className={`group cursor-pointer rounded-lg border bg-paper p-3.5 shadow-[0_1px_0_rgba(43,36,32,0.06)] transition
                         hover:-translate-y-px hover:shadow-md ${flagged ? "border-bad/40" : "border-rule hover:border-tomato/40"}`}>
      <div className="flex items-start gap-2">
        {rank !== undefined && <span className="font-display text-lg leading-6 text-tomato">{rank}</span>}
        <div className="min-w-0 flex-1">
          <h3 className="font-display text-[17px] font-semibold leading-snug text-ink group-hover:text-tomato">
            {card.title.trim()}</h3>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-ink-soft">
            <IdPill id={card.id} onOpen={onOpen} />
            <SourceBadge source={card.source} />
            <span>{plural(card.n_ingredients, "ingredient")}</span><span aria-hidden>·</span><span>{plural(card.n_steps, "step")}</span>
            {card.score !== undefined && <span className="ml-auto font-mono text-ink">score {card.score.toFixed(2)}</span>}
          </div>
        </div>
      </div>
      {card.chips.length > 0 && <div className="mt-2.5 flex flex-wrap gap-1">
        {card.chips.map((c, i) => <ChipView key={i} chip={c} />)}</div>}
      {card.parts && <ScoreBar parts={card.parts} />}
    </article>
  );
}
