import type { State } from "../api";

const TAG_LABEL: Record<string, string> = { tree_nut: "tree nuts", root_veg: "onion/garlic/root veg" };
const label = (t: string) => TAG_LABEL[t] ?? t;

type Patch = (op: "remove" | "set", field: string, value: unknown) => void;

const PREF_LABEL: Record<string, string> = { use_most: "use as many as possible", fewest_extra: "fewest extra",
                                             fewest_steps: "fewest steps", no_staples: "no staples assumed" };

// phone: one row that scrolls sideways, every chip and its × at least 44 px tall
const PHONE = "phone:min-h-11 phone:shrink-0 phone:whitespace-nowrap phone:text-[14px]";

function Removable({ label, onRemove, tone = "ink" }: { label: string; onRemove: () => void; tone?: "ink" | "tomato" }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border py-0.5 pl-2.5 pr-1 text-[12.5px] ${PHONE} ${tone === "tomato"
      ? "border-tomato/30 bg-tomato-soft text-tomato" : "border-rule bg-paper text-ink"}`}>
      {label}
      <button type="button" onClick={onRemove} aria-label={`Remove ${label}`}
              className="grid h-4.5 w-4.5 place-items-center rounded-full text-[13px] leading-none opacity-60 hover:bg-ink/10 hover:opacity-100 cursor-pointer phone:h-10 phone:w-8 phone:text-[17px]">×</button>
    </span>
  );
}

function Toggle({ label, on, onChange, title, warn }: { label: string; on: boolean; onChange: (v: boolean) => void;
                                                       title: string; warn?: boolean }) {
  const onCls = warn ? "border-warn/40 bg-warn-soft text-warn" : "border-ok/30 bg-ok-soft text-ok";
  return (
    <button type="button" onClick={() => onChange(!on)} title={title} aria-pressed={on}
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[12.5px] cursor-pointer ${PHONE} ${on
              ? onCls : "border-rule bg-transparent text-ink-soft hover:bg-paper"}`}>
      <span className={`h-2 w-2 rounded-full ${on ? (warn ? "bg-warn" : "bg-ok") : "bg-grey/40"}`} />{label}
    </button>
  );
}

/** Sticky chips for the session's active state. Removing / toggling PATCHes the state and re-runs the task.
 *  On a phone the reset link lives in the header's ⋯ menu instead. */
export function ConstraintBar({ state, onPatch, onReset, mobile = false }: { state: State | null; onPatch: Patch;
  onReset: () => void; mobile?: boolean }) {
  if (!state || !state.active_task) return null;
  const covered = new Set((state.diets ?? []).flatMap((d) => d.tags));  // shown inside their preset chip
  return (
    <div className="chip-row flex flex-wrap items-center gap-1.5 border-t border-rule px-5 py-2.5 phone:flex-nowrap phone:overflow-x-auto phone:px-3 phone:py-1.5"
         aria-label="Active restrictions and filters">
      <span className="mr-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-soft phone:shrink-0">Active</span>
      {state.query_text && <Removable label={`dish: ${state.query_text}`} onRemove={() => onPatch("remove", "query_text", null)} />}
      {(state.diets ?? []).map((d) => <Removable key={d.name} tone="tomato" label={mobile ? d.name : `${d.name}: no ${d.tags.map(label).join(", ")}`}
                                                onRemove={() => onPatch("remove", "diets", d.name)} />)}
      {state.exclude_tags.filter((t) => !covered.has(t)).map((t) => <Removable key={t} tone="tomato" label={`no ${label(t)}`} onRemove={() => onPatch("remove", "exclude_tags", t)} />)}
      {state.exclude.map((t) => <Removable key={t} tone="tomato" label={`no ${t}`} onRemove={() => onPatch("remove", "exclude", t)} />)}
      {state.max_steps !== null && <Removable tone="tomato" label={`≤ ${state.max_steps} step${state.max_steps === 1 ? "" : "s"}`} onRemove={() => onPatch("remove", "max_steps", null)} />}
      {state.have.map((h) => <Removable key={h} label={`have: ${h}`} onRemove={() => onPatch("remove", "have", h)} />)}
      {state.prefs.filter((p) => p !== "no_staples").map((p) => <Removable key={p} label={PREF_LABEL[p] ?? p} onRemove={() => onPatch("remove", "prefs", p)} />)}
      <span className="mx-1 h-4 w-px bg-rule phone:shrink-0" />
      <Toggle warn label={mobile ? "strict" : "strict: may-contain + unverified"} on={state.strict_may_contain} onChange={(v) => onPatch("set", "strict_may_contain", v)}
              title="Also exclude recipes whose lines only MAY contain an excluded allergen (e.g. margarine, chocolate), and recipes with an ingredient that couldn't be verified (unknown is not safe)" />
      {state.active_task === "match" && <Toggle label="pantry staples" on={state.staples} onChange={(v) => onPatch("set", "staples", v)}
              title="Assume salt, black pepper and water are available" />}
      {!mobile && <button type="button" onClick={onReset} className="ml-auto text-[12px] text-ink-soft underline-offset-2 hover:text-tomato hover:underline cursor-pointer">
        reset conversation</button>}
    </div>
  );
}
