import { useCallback, useEffect, useRef, useState } from "react";
import { api, type ChatResponse, type State } from "./api";
import { ChatPane, type Msg } from "./components/ChatPane";
import { EvidencePanel, type Tab } from "./components/EvidencePanel";
import { RecipeDrawer } from "./components/RecipeDrawer";

// ?q=...&q=... replays those messages in order on load (demo sessions); ?tab=calc picks the panel tab.
const params = new URLSearchParams(location.search);

export default function App() {
  const [sid, setSid] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [resp, setResp] = useState<ChatResponse | null>(null);
  const [state, setState] = useState<State | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>((params.get("tab") as Tab) || "results");
  const [drawer, setDrawer] = useState<string | null>(null);
  const [health, setHealth] = useState<{ valid: number; llm: string } | null>(null);
  const sidRef = useRef<string | null>(null);

  useEffect(() => { api.health().then((h) => setHealth({ valid: h.valid, llm: h.llm.status })).catch(() => {}); }, []);

  const show = useCallback((r: ChatResponse, keepTab = false) => {
    sidRef.current = r.session_id; setSid(r.session_id);
    setResp(r); setState(r.state);
    setMessages((m) => [...m, { role: "bot", md: r.reply_md, voice: r.voice, planner: r.planner, trace: r.trace,
                                suggestions: r.suggestions ?? [] }]);
    setDrawer(r.payload.type === "recipe" && r.payload.recipe ? r.payload.recipe.id : null);
    if (!keepTab) setTab(r.payload.cards.length || r.payload.type === "match" ? "results" : r.payload.calc?.length ? "calc" : "trace");
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
    setMessages([]); setResp(null); setState(null); setDrawer(null);
  };

  const replayed = useRef(false);
  useEffect(() => {  // demo replay (ref guard: StrictMode runs effects twice in dev)
    const qs = params.getAll("q");
    if (replayed.current || !qs.length) return;
    replayed.current = true;
    (async () => { for (const q of qs) await send(q); if (params.get("tab")) setTab(params.get("tab") as Tab); })();
  }, [send]);

  const closeDrawer = useCallback(() => setDrawer(null), []);
  return (
    <div className="flex h-full flex-col">
      <header className="flex items-baseline gap-3 border-b border-rule bg-paper/60 px-6 py-3">
        <h1 className="font-display text-[24px] font-bold tracking-tight">Recipe <span className="text-tomato">Box</span></h1>
        <p className="text-[13px] text-ink-soft">grounded answers from {health ? health.valid.toLocaleString() : "…"} valid recipes</p>
        <span className="ml-auto inline-flex items-center gap-1.5 text-[12px] text-ink-soft" title="LLM planner status">
          <span className={`h-2 w-2 rounded-full ${health?.llm === "ready" ? "bg-ok" : health?.llm === "warming up" ? "bg-amber" : "bg-grey"}`} />
          LLM {health?.llm ?? "…"}</span>
      </header>
      <main className="grid min-h-0 flex-1 grid-cols-[3fr_2fr]">
        <ChatPane messages={messages} loading={loading} state={state} onSend={send} onPatch={patch} onReset={reset} onOpen={setDrawer} />
        <EvidencePanel resp={resp} tab={tab} setTab={setTab} onOpen={setDrawer}
                       onStrict={() => patch("set", "strict_may_contain", true)} />
      </main>
      <RecipeDrawer id={drawer} onClose={closeDrawer} />
    </div>
  );
}
