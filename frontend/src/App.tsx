import { useCallback, useEffect, useRef, useState } from "react";
import { api, type ChatResponse, type State } from "./api";
import { ChatPane, type Msg } from "./components/ChatPane";
import { EvidencePanel, type Tab } from "./components/EvidencePanel";
import { MobileHeader, Sheet, sheetLabel, useMobile } from "./components/Mobile";
import { RecipeDrawer } from "./components/RecipeDrawer";

// ?q=...&q=... replays those messages in order on load (demo sessions); ?tab=calc picks the panel tab;
// ?dev=1 / ?dev=0 forces developer view (screenshots). Below 900 px the phone layout renders instead
// (useMobile): one 100dvh column, results in a bottom sheet.
const params = new URLSearchParams(location.search);
const DEV_KEY = "recipebox.devView";

/** Developer view (SQL, planner badges, timings, trace, raw filters): off by default, remembered per browser.
 *  Storage can be blocked (private mode, previews), so every access is wrapped and the default still works. */
function useDevView(): [boolean, (v: boolean) => void] {
  const [dev, setDev] = useState(() => {
    if (params.has("dev")) return params.get("dev") === "1";
    try { return localStorage.getItem(DEV_KEY) === "1"; } catch { return false; }
  });
  const set = (v: boolean) => { setDev(v); try { localStorage.setItem(DEV_KEY, v ? "1" : "0"); } catch { /* not saved */ } };
  return [dev, set];
}

export default function App() {
  const [sid, setSid] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [resp, setResp] = useState<ChatResponse | null>(null);
  const [state, setState] = useState<State | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>((params.get("tab") as Tab) || "results");
  const [drawer, setDrawer] = useState<string | null>(null);
  const [health, setHealth] = useState<{ valid: number; llm: string } | null>(null);
  const [dev, setDev] = useDevView();
  const mobile = useMobile();
  const [sheet, setSheet] = useState(false);
  const sidRef = useRef<string | null>(null);

  useEffect(() => { api.health().then((h) => setHealth({ valid: h.valid, llm: h.llm.status })).catch(() => {}); }, []);
  useEffect(() => { if (!dev && tab === "trace") setTab("results"); }, [dev, tab]);

  const show = useCallback((r: ChatResponse, keepTab = false) => {
    sidRef.current = r.session_id; setSid(r.session_id);
    setResp(r); setState(r.state);
    setMessages((m) => [...m, { role: "bot", md: r.reply_md, voice: r.voice, planner: r.planner, trace: r.trace,
                                suggestions: r.suggestions ?? [], dev: r.payload.dev_md ?? [] }]);
    setDrawer(r.payload.type === "recipe" && r.payload.recipe ? r.payload.recipe.id : null);
    if (!keepTab) setSheet(false);
    if (!keepTab) setTab(r.payload.cards.length || r.payload.type === "match" ? "results" : r.payload.calc?.length ? "calc" : "results");
  }, []);

  const fail = (e: unknown) => setMessages((m) => [...m, { role: "error", text: String((e as Error).message || e) }]);

  const send = useCallback(async (text: string) => {
    setMessages((m) => [...m, { role: "user", text }]);
    setLoading(true);
    try { show(await api.chat(sidRef.current, text)); } catch (e) { fail(e); } finally { setLoading(false); }
  }, [show]);

  const patch = async (op: "remove" | "set", field: string, value: unknown) => {
    if (!sid) return;
    setLoading(true);
    try { show(await api.patch(sid, op, field, value), true); } catch (e) { fail(e); } finally { setLoading(false); }
  };

  const reset = async () => {
    if (sid) await api.reset(sid).catch(() => {});
    setMessages([]); setResp(null); setState(null); setDrawer(null); setSheet(false);
  };

  const replayed = useRef(false);
  useEffect(() => {  // demo replay (ref guard: StrictMode runs effects twice in dev)
    const qs = params.getAll("q");
    if (replayed.current || !qs.length) return;
    replayed.current = true;
    (async () => { for (const q of qs) await send(q); if (params.get("tab")) setTab(params.get("tab") as Tab); })();
  }, [send]);

  const closeDrawer = useCallback(() => setDrawer(null), []);
  const closeSheet = useCallback(() => setSheet(false), []);
  const panel = (inSheet: boolean) => <EvidencePanel resp={resp} tab={tab} setTab={setTab} dev={dev} onOpen={setDrawer}
                                                     mobile={inSheet} onStrict={() => patch("set", "strict_may_contain", true)} />;
  if (mobile) {
    const label = sheetLabel(resp?.payload);
    return (
      <div className="flex h-[100dvh] flex-col overflow-hidden">
        <MobileHeader dev={dev} setDev={setDev} onReset={reset} llm={health?.llm ?? "…"} />
        <ChatPane messages={messages} loading={loading} state={state} dev={dev} mobile onSend={send} onPatch={patch}
                  onReset={reset} onOpen={setDrawer}
                  bar={label && !loading ? <button type="button" onClick={() => setSheet(true)} aria-haspopup="dialog"
                    className="flex min-h-11 w-full items-center justify-between border-t border-rule bg-ink px-4 text-[15px] font-semibold text-cream cursor-pointer">
                    {label}<span aria-hidden>▲</span></button> : null} />
        {sheet && <Sheet onClose={closeSheet}>{panel(true)}</Sheet>}
        <RecipeDrawer id={drawer} onClose={closeDrawer} mobile />
      </div>
    );
  }
  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-3 border-b border-rule bg-paper/60 px-6 py-2.5">
        <h1 className="font-display text-[24px] font-bold tracking-tight">Recipe <span className="text-tomato">Box</span></h1>
        <p className="text-[13px] text-ink-soft">grounded answers from {health ? health.valid.toLocaleString() : "…"} recipes</p>
        <div className="ml-auto flex items-center gap-3">
          {dev && <span className="inline-flex items-center gap-1.5 text-[12px] text-ink-soft" title="LLM planner status">
            <span className={`h-2 w-2 rounded-full ${health?.llm === "ready" ? "bg-ok" : health?.llm === "warming up" ? "bg-amber" : "bg-grey"}`} />
            LLM {health?.llm ?? "…"}</span>}
          <label className="inline-flex cursor-pointer select-none items-center gap-2 text-[12.5px] text-ink-soft"
                 title="Show SQL, planner and timings, the trace, raw filters and the dataset breakdown">
            <span>Developer view</span>
            <button type="button" role="switch" aria-checked={dev} aria-label="Developer view" onClick={() => setDev(!dev)}
                    className={`relative h-5 w-9 rounded-full border transition cursor-pointer ${dev ? "border-tomato bg-tomato" : "border-rule bg-grey-soft"}`}>
              <span className={`absolute top-0.5 h-3.5 w-3.5 rounded-full bg-paper shadow transition-all ${dev ? "left-[18px]" : "left-0.5"}`} />
            </button>
          </label>
        </div>
      </header>
      <main className="grid min-h-0 flex-1 grid-cols-[3fr_2fr]">
        <ChatPane messages={messages} loading={loading} state={state} dev={dev} onSend={send} onPatch={patch} onReset={reset} onOpen={setDrawer} />
        {panel(false)}
      </main>
      <RecipeDrawer id={drawer} onClose={closeDrawer} />
    </div>
  );
}
