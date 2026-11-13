import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Payload } from "../api";

// Phone-only pieces (below 900 px): the hook that switches the layout, the compact header with its ⋯ menu, the
// results bottom sheet and the label of the bar that opens it. Desktop never renders these.

const QUERY = "(max-width: 899px)";

export function useMobile(): boolean {
  const [m, setM] = useState(() => window.matchMedia(QUERY).matches);
  useEffect(() => {
    const mq = window.matchMedia(QUERY);
    const on = () => setM(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return m;
}

/** 'View 495 results', 'View calculation', 'View adapted recipe', or null when the answer has nothing to show. */
export function sheetLabel(p: Payload | undefined): string | null {
  if (!p) return null;
  if (p.type === "search" || p.type === "match") {
    const n = (p.total ?? 0) - (p.n_unverified ?? 0);
    return p.total ? `View ${n.toLocaleString()} result${n === 1 ? "" : "s"}` : p.alternatives?.length ? "View alternatives" : null;
  }
  if (p.type === "substitute") return p.adaptation ? "View adapted recipe" : "View evidence";
  if (p.type === "stats") return p.cards.length ? `View ${p.cards.length} recipes` : "View calculation";
  if (p.cards.length) return "View recipe details";
  return p.calc?.length ? "View calculation" : null;
}

/** Compact header: the logo, and a ⋯ menu with developer view, reset and the LLM status. */
export function MobileHeader({ dev, setDev, onReset, llm }: { dev: boolean; setDev: (v: boolean) => void;
  onReset: () => void; llm: string }) {
  const [open, setOpen] = useState(false);
  return (
    <header className="relative z-20 flex h-12 shrink-0 items-center border-b border-rule bg-paper/80 px-3">
      <h1 className="font-display text-[21px] font-bold tracking-tight">Recipe <span className="text-tomato">Box</span></h1>
      <button type="button" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(!open)}
              className="ml-auto grid h-11 w-11 place-items-center rounded-full text-[22px] leading-none text-ink-soft hover:bg-grey-soft cursor-pointer">⋯</button>
      {open && <>
        <button type="button" aria-label="Close menu" className="fixed inset-0 z-10 cursor-default" onClick={() => setOpen(false)} />
        <div role="menu" className="absolute right-2 top-11 z-20 w-64 rounded-xl border border-rule bg-paper p-1.5 shadow-xl">
          <button type="button" role="menuitemcheckbox" aria-checked={dev} onClick={() => setDev(!dev)}
                  className="flex min-h-11 w-full items-center justify-between rounded-lg px-3 text-left text-[15px] hover:bg-grey-soft cursor-pointer">
            Developer view
            <span className={`relative h-5 w-9 rounded-full border transition ${dev ? "border-tomato bg-tomato" : "border-rule bg-grey-soft"}`}>
              <span className={`absolute top-0.5 h-3.5 w-3.5 rounded-full bg-paper shadow transition-all ${dev ? "left-[18px]" : "left-0.5"}`} /></span>
          </button>
          <button type="button" role="menuitem" onClick={() => { setOpen(false); onReset(); }}
                  className="flex min-h-11 w-full items-center rounded-lg px-3 text-left text-[15px] hover:bg-grey-soft cursor-pointer">
            Reset conversation</button>
          <p className="flex min-h-11 items-center gap-2 px-3 text-[13px] text-ink-soft">
            <span className={`h-2 w-2 rounded-full ${llm === "ready" ? "bg-ok" : llm === "warming up" ? "bg-amber" : "bg-grey"}`} />
            Language model: {llm}</p>
        </div>
      </>}
    </header>
  );
}

/** Bottom sheet over the chat (still visible above it): tap the backdrop or ▼, or swipe the handle down, to close. */
export function Sheet({ onClose, children }: { onClose: () => void; children: ReactNode }) {
  const [dy, setDy] = useState(0);
  const start = useRef<number | null>(null);
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-20">
      <button type="button" aria-label="Close results" onClick={onClose} className="absolute inset-0 bg-ink/30 cursor-default" />
      <div role="dialog" aria-modal aria-label="Results" style={{ transform: `translateY(${dy}px)` }}
           className={`absolute inset-x-0 bottom-0 flex h-[86dvh] flex-col overflow-hidden rounded-t-2xl bg-cream shadow-2xl ${dy ? "" : "transition-transform"}`}>
        <div className="flex shrink-0 touch-none items-center px-2 pt-1"
             onTouchStart={(e) => { start.current = e.touches[0].clientY; }}
             onTouchMove={(e) => { if (start.current !== null) setDy(Math.max(0, e.touches[0].clientY - start.current)); }}
             onTouchEnd={() => { if (dy > 80) onClose(); setDy(0); start.current = null; }}>
          <span className="w-11" />
          <span className="mx-auto h-1.5 w-12 rounded-full bg-rule" aria-hidden />
          <button type="button" aria-label="Close results" onClick={onClose}
                  className="grid h-11 w-11 place-items-center rounded-full text-[15px] text-ink-soft hover:bg-grey-soft cursor-pointer">▼</button>
        </div>
        {children}
      </div>
    </div>
  );
}
