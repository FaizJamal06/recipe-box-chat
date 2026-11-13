import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Planner, State, Suggestion } from "../api";
import { ConstraintBar } from "./ConstraintBar";
import { Markdown } from "./Markdown";

export type Msg = { role: "user"; text: string }
  | { role: "bot"; md: string; voice: string | null; planner: Planner; trace: string[]; suggestions: Suggestion[];
      dev: string[] }
  | { role: "error"; text: string };

export const DEMO_PROMPTS = [
  "Find a penne pasta recipe",
  "How many recipes contain both garlic and onion? What percentage of the dataset is that?",
  "Among recipes containing tomato, which five have the fewest instruction steps?",
  "What's the average number of ingredients in desserts?",
  "I have eggs, onions, tomatoes, and rice. Suggest five recipes using as many as possible, no peanuts, at most six steps, fewest additional ingredients.",
  "I have saffron and marshmallows, no sugar, at most 2 steps",
  "How many recipes are dairy-free?",
  "Take this banana bread recipe and remove eggs. Use only ingredients that appear in the dataset. What replacements have evidence from related baked recipes, and how might the texture change?",
  "Replace cream in this pasta recipe without dairy. Prefer examples from the database.",
  "Remove the egg whites from this meringue / angel food cake",
];

const secs = (ms: number) => (ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`);
const fallback = (p: Planner) => p.detail === "rule" || p.label.includes("keyword");

/** Developer view: planner, LLM calls and time, all in grey (a fallback is information, not an error). */
function PlannerBadge({ p }: { p: Planner }) {
  const calls = `${p.calls} LLM call${p.calls === 1 ? "" : "s"}`;
  return <span className="text-ink-soft" title={p.reason || `${calls}, ${p.prompt_tokens} prompt tokens`}>
    {p.label} · {calls} · {secs(p.turn_ms)}</span>;
}

/** Normal view: nothing when the LLM planned the turn; a subtle grey dot when the rule parser stood in for it. */
function FallbackDot({ p }: { p: Planner }) {
  if (!fallback(p)) return null;
  return <span className="inline-block h-1.5 w-1.5 rounded-full bg-grey/60" role="img" aria-label="Answered without the language model"
               title={`Answered by the rule parser: the language model was unavailable (${p.reason || p.label}). Every number still comes from the database.`} />;
}

/** The templated answer under a voice reply: folded by default ("Show exact numbers"). */
function Exact({ md, onOpen }: { md: string; onOpen: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  return <div className="mt-2 border-t border-rule/70 pt-1.5 text-[13px] text-ink-soft">
    <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="cursor-pointer select-none text-[12px] hover:text-ink">
      {open ? "▾ Hide exact numbers" : "▸ Show exact numbers"}</button>
    {open && <div className="mt-1"><Markdown md={md} onOpen={onOpen} /></div>}
  </div>;
}

/** Collapsed by default and rendered only when opened (a closed <details> list leaked empty "1. 2. 3." markers). */
function Trace({ steps }: { steps: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2 border-t border-rule/70 pt-1.5 text-[12px] text-ink-soft">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="cursor-pointer select-none hover:text-ink">
        {open ? "▾" : "▸"} trace · {steps.length} steps</button>
      {open && <div className="mt-1 space-y-0.5 font-mono text-[11px]">{steps.map((t, i) =>
        <div key={i} className="flex gap-2"><span className="w-4 shrink-0 text-right text-ink-soft/70">{i + 1}.</span><span>{t}</span></div>)}</div>}
    </div>
  );
}

function Bubble({ m, dev, onOpen }: { m: Msg; dev: boolean; onOpen: (id: string) => void }) {
  if (m.role === "user")
    return <div className="ml-auto w-fit max-w-[78%] break-words rounded-2xl rounded-br-sm bg-ink px-4 py-2.5 text-[14.5px] text-cream phone:max-w-[85%] phone:text-[15px]">{m.text}</div>;
  if (m.role === "error")
    return <div className="max-w-[92%] rounded-lg border border-bad/30 bg-bad-soft px-4 py-2.5 text-[14px] text-bad">{m.text}</div>;
  return (
    <div className="max-w-[92%] phone:max-w-full">
      <div className="mb-1 flex items-center gap-2 text-[11.5px]"><span className="font-display font-semibold text-tomato">Recipe Box</span>
        {dev ? <PlannerBadge p={m.planner} /> : <FallbackDot p={m.planner} />}</div>
      <div className="break-words rounded-2xl rounded-tl-sm border border-rule bg-paper px-4 py-3 text-[14.5px] shadow-[0_1px_0_rgba(43,36,32,0.05)] phone:px-3.5 phone:text-[15px]">
        {m.voice && <p className="text-[15px] leading-relaxed text-ink">{m.voice}</p>}
        {m.voice ? <Exact md={m.md} onOpen={onOpen} /> : <Markdown md={m.md} onOpen={onOpen} />}
        {dev && m.dev.length > 0 && <div className="mt-2 space-y-0.5 border-t border-rule/70 pt-1.5 font-mono text-[11px] text-ink-soft">
          {m.dev.map((d, i) => <div key={i} className="break-words">{d}</div>)}</div>}
        {dev && <Trace steps={m.trace} />}
      </div>
    </div>
  );
}

const SEND_ICON = <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden fill="none" stroke="currentColor" strokeWidth="2.4"
                        strokeLinecap="round" strokeLinejoin="round"><path d="M12 19V5M5 12l7-7 7 7" /></svg>;

/** The conversation column. Phone (`mobile`): demo prompts as a list, chip rows that scroll sideways instead of
 *  wrapping, the results bar (`bar`) above an input fixed at the bottom (16 px text so iOS doesn't zoom). */
export function ChatPane({ messages, loading, state, dev, mobile = false, bar = null, onSend, onPatch, onReset, onOpen }: {
  messages: Msg[]; loading: boolean; state: State | null; dev: boolean; mobile?: boolean; bar?: ReactNode;
  onSend: (t: string) => void; onPatch: (op: "remove" | "set", field: string, value: unknown) => void; onReset: () => void;
  onOpen: (id: string) => void;
}) {
  const [text, setText] = useState("");
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { if (messages.length) end.current?.scrollIntoView({ block: "end" }); }, [messages, loading]);  // empty state stays at the top
  const send = () => { const t = text.trim(); if (t && !loading) { onSend(t); setText(""); } };
  const last = messages[messages.length - 1];
  const lastUser = [...messages].reverse().find((m) => m.role === "user");
  const rewriting = state?.active_task === "substitute" || (lastUser?.role === "user" &&
    /\b(remove|replace|substitut\w*|swap|instead of|take out|leave out|make it|adapt)\b/i.test(lastUser.text));
  return (
    <section className="flex min-h-0 flex-1 flex-col">
      <div className="scroll-thin min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-6 phone:px-3 phone:py-4">
        {messages.length === 0 && (
          <div className="mx-auto mt-6 max-w-2xl phone:mt-1">
            <h2 className="font-display text-[34px] font-semibold leading-tight phone:text-[26px]">What's cooking?</h2>
            <p className="mt-2 text-[15px] text-ink-soft">Ask about the recipe collection. Every count, ranking and recipe comes
              from the database, with the calculation one tap away. Try a demo conversation:</p>
            {mobile
              ? <ul className="mt-3 divide-y divide-rule overflow-hidden rounded-xl border border-rule bg-paper">{DEMO_PROMPTS.map((p) =>
                  <li key={p}><button type="button" onClick={() => onSend(p)}
                    className="flex min-h-12 w-full items-center gap-3 px-3.5 py-2.5 text-left text-[15px] leading-snug text-ink active:bg-tomato-soft cursor-pointer">
                    <span className="min-w-0 flex-1">{p}</span><span aria-hidden className="text-tomato">›</span></button></li>)}</ul>
              : <div className="mt-5 flex flex-wrap gap-2">{DEMO_PROMPTS.map((p) =>
                  <button key={p} type="button" onClick={() => onSend(p)}
                          className="rounded-full border border-rule bg-paper px-3.5 py-1.5 text-left text-[13.5px] text-ink shadow-[0_1px_0_rgba(43,36,32,0.05)] transition hover:border-tomato/50 hover:text-tomato cursor-pointer">{p}</button>)}
                </div>}
          </div>)}
        {messages.map((m, i) => <Bubble key={i} m={m} dev={dev} onOpen={onOpen} />)}
        {!loading && last?.role === "bot" && last.suggestions.length > 0 && (
          <div className="chip-row flex flex-wrap gap-2 pl-1 phone:-mx-3 phone:flex-nowrap phone:overflow-x-auto phone:px-3" aria-label="Suggested follow-ups">
            {last.suggestions.map((s) =>
            <button key={s.message} type="button" onClick={() => onSend(s.message)} title={s.message}
                    className="rounded-full border border-tomato/30 bg-paper px-3 py-1 text-[13px] text-tomato transition hover:bg-tomato-soft cursor-pointer phone:min-h-11 phone:shrink-0 phone:whitespace-nowrap phone:px-4 phone:text-[14.5px]">
              {s.label}</button>)}</div>)}
        {loading && <div className="flex items-center gap-2 text-[13.5px] text-ink-soft" aria-live="polite">
          <span className="font-display font-semibold text-tomato">Recipe Box</span> {rewriting ? "rewriting steps" : "thinking"}
          <span><span className="dot">.</span><span className="dot">.</span><span className="dot">.</span></span></div>}
        <div ref={end} />
      </div>
      <ConstraintBar state={state} onPatch={onPatch} onReset={onReset} mobile={mobile} />
      {bar}
      <form onSubmit={(e) => { e.preventDefault(); send(); }}
            className="flex gap-2 border-t border-rule bg-paper/70 px-5 py-3 phone:bg-paper phone:px-3 phone:pt-2 phone:pb-[calc(0.5rem+env(safe-area-inset-bottom))]">
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder={mobile ? "Ask about recipes…" : "Ask about recipes, e.g. “I cannot have dairy”"}
               aria-label="Message" enterKeyHint="send"
               className="min-w-0 flex-1 rounded-full border border-rule bg-paper px-4 py-2.5 text-[14.5px] outline-none placeholder:text-ink-soft/70 focus:border-tomato/60 focus:ring-2 focus:ring-tomato/15 phone:min-h-11 phone:text-[16px]" />
        {mobile
          ? <button type="submit" disabled={loading || !text.trim()} aria-label="Send"
                    className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-tomato text-paper transition disabled:opacity-40 cursor-pointer">{SEND_ICON}</button>
          : <button type="submit" disabled={loading || !text.trim()}
                    className="rounded-full bg-tomato px-5 text-[14px] font-semibold text-paper transition hover:bg-tomato/90 disabled:opacity-40 cursor-pointer">Send</button>}
      </form>
    </section>
  );
}
