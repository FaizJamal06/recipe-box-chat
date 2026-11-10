import { useEffect, useRef, useState } from "react";
import type { Planner, State } from "../api";
import { ConstraintBar } from "./ConstraintBar";
import { Markdown } from "./Markdown";

export type Msg = { role: "user"; text: string } | { role: "bot"; md: string; planner: Planner; trace: string[] }
  | { role: "error"; text: string };

export const DEMO_PROMPTS = [
  "Find a penne pasta recipe",
  "How many recipes contain both garlic and onion? What percentage of the dataset is that?",
  "Among recipes containing tomato, which five have the fewest instruction steps?",
  "What's the average number of ingredients in desserts?",
  "I have eggs, onions, tomatoes, and rice. Suggest five recipes using as many as possible, no peanuts, at most six steps, fewest additional ingredients.",
  "I have saffron and marshmallows, no sugar, at most 2 steps",
  "How many recipes are dairy-free?",
];

function PlannerBadge({ p }: { p: Planner }) {
  const secs = (ms: number) => (ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`);
  if (p.kind === "llm")
    return <span className="text-ink-soft" title={`${p.calls} LLM call(s), ${p.prompt_tokens} prompt tokens`}>
      LLM · {p.model} · {secs(p.turn_ms)}</span>;
  const label = { rule: "rule parser", guard: "unsupported-attribute guard", ui: "chip change" }[p.kind];
  const why = p.kind === "rule" ? (p.detail === "rule_direct" ? "high-confidence pattern, LLM skipped" : `LLM unavailable: ${p.reason}`)
    : p.kind === "guard" ? "answered without the LLM" : "state edited in the UI";
  return <span className="inline-flex items-center gap-1.5">
    <span title={why} className="rounded-full border border-tomato/40 bg-tomato-soft px-2 py-px font-medium text-tomato">{label}</span>
    <span className="text-ink-soft">{why} · {secs(p.turn_ms)}</span></span>;
}

function Bubble({ m, onOpen }: { m: Msg; onOpen: (id: string) => void }) {
  if (m.role === "user")
    return <div className="ml-auto w-fit max-w-[78%] rounded-2xl rounded-br-sm bg-ink px-4 py-2.5 text-[14.5px] text-cream">{m.text}</div>;
  if (m.role === "error")
    return <div className="max-w-[88%] rounded-lg border border-bad/30 bg-bad-soft px-4 py-2.5 text-[14px] text-bad">{m.text}</div>;
  return (
    <div className="max-w-[92%]">
      <div className="mb-1 flex items-center gap-2 text-[11.5px]"><span className="font-display font-semibold text-tomato">Recipe Box</span>
        <PlannerBadge p={m.planner} /></div>
      <div className="rounded-2xl rounded-tl-sm border border-rule bg-paper px-4 py-3 text-[14.5px] shadow-[0_1px_0_rgba(43,36,32,0.05)]">
        <Markdown md={m.md} onOpen={onOpen} />
        <details className="mt-2 border-t border-rule/70 pt-1.5 text-[12px] text-ink-soft">
          <summary className="cursor-pointer select-none hover:text-ink">trace · {m.trace.length} steps</summary>
          <ol className="mt-1 list-decimal space-y-0.5 pl-5 font-mono text-[11px]">{m.trace.map((t, i) => <li key={i}>{t}</li>)}</ol>
        </details>
      </div>
    </div>
  );
}

export function ChatPane({ messages, loading, state, onSend, onPatch, onReset, onOpen }: {
  messages: Msg[]; loading: boolean; state: State | null; onSend: (t: string) => void;
  onPatch: (op: "remove" | "set", field: string, value: unknown) => void; onReset: () => void; onOpen: (id: string) => void;
}) {
  const [text, setText] = useState("");
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [messages, loading]);
  const send = () => { const t = text.trim(); if (t && !loading) { onSend(t); setText(""); } };
  return (
    <section className="flex min-h-0 flex-col">
      <div className="scroll-thin min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-6">
        {messages.length === 0 && (
          <div className="mx-auto mt-6 max-w-2xl">
            <h2 className="font-display text-[34px] font-semibold leading-tight">What's cooking?</h2>
            <p className="mt-2 text-[15px] text-ink-soft">Ask about the recipe collection. Every count, ranking and recipe comes
              from the database, with the calculation shown on the right. Try a demo conversation:</p>
            <div className="mt-5 flex flex-wrap gap-2">{DEMO_PROMPTS.map((p) =>
              <button key={p} type="button" onClick={() => onSend(p)}
                      className="rounded-full border border-rule bg-paper px-3.5 py-1.5 text-left text-[13.5px] text-ink shadow-[0_1px_0_rgba(43,36,32,0.05)] transition hover:border-tomato/50 hover:text-tomato cursor-pointer">{p}</button>)}
            </div>
          </div>)}
        {messages.map((m, i) => <Bubble key={i} m={m} onOpen={onOpen} />)}
        {loading && <div className="flex items-center gap-2 text-[13.5px] text-ink-soft" aria-live="polite">
          <span className="font-display font-semibold text-tomato">Recipe Box</span> thinking
          <span><span className="dot">.</span><span className="dot">.</span><span className="dot">.</span></span></div>}
        <div ref={end} />
      </div>
      <ConstraintBar state={state} onPatch={onPatch} onReset={onReset} />
      <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex gap-2 border-t border-rule bg-paper/70 px-5 py-3">
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask about recipes, e.g. “I cannot have dairy”"
               aria-label="Message" className="min-w-0 flex-1 rounded-full border border-rule bg-paper px-4 py-2.5 text-[14.5px] outline-none placeholder:text-ink-soft/70 focus:border-tomato/60 focus:ring-2 focus:ring-tomato/15" />
        <button type="submit" disabled={loading || !text.trim()}
                className="rounded-full bg-tomato px-5 text-[14px] font-semibold text-paper transition hover:bg-tomato/90 disabled:opacity-40 cursor-pointer">Send</button>
      </form>
    </section>
  );
}
