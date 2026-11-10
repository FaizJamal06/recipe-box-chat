import { Fragment, type ReactNode } from "react";
import { IdPill } from "./RecipeCard";

// Renders the backend's templated markdown subset (web.py): one block per line; '- ' and '1. ' list items,
// '> ' callouts; inline **bold**, _italic_, `code`. A code span holding a recipe id becomes a clickable IdPill.
// Builds React elements only (no innerHTML), so recipe text can't inject markup.
const ID = /^(ar|epi|fn):\S+$/;

function inline(text: string, onOpen: (id: string) => void): ReactNode[] {
  // _italic_ only at word edges, so tag names like may_contain stay literal
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`|(?<!\w)_[^_]+_(?!\w))/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) {
      const code = part.slice(1, -1);
      return ID.test(code) ? <IdPill key={i} id={code} onOpen={onOpen} /> :
        <code key={i} className="font-mono text-[0.85em] bg-grey-soft px-1 rounded">{code}</code>;
    }
    if (part.length > 2 && part.startsWith("_") && part.endsWith("_")) return <em key={i} className="text-ink-soft">{part.slice(1, -1)}</em>;
    return <Fragment key={i}>{part}</Fragment>;
  });
}

export function Markdown({ md, onOpen }: { md: string; onOpen: (id: string) => void }) {
  const blocks: ReactNode[] = [];
  let list: { ordered: boolean; items: ReactNode[] } | null = null;
  const flush = () => {
    if (!list) return;
    const cls = "my-1.5 space-y-1 pl-5 " + (list.ordered ? "list-decimal" : "list-disc");
    blocks.push(list.ordered ? <ol key={blocks.length} className={cls}>{list.items}</ol>
                             : <ul key={blocks.length} className={cls}>{list.items}</ul>);
    list = null;
  };
  md.split("\n").forEach((raw, i) => {
    const line = raw.trimEnd();
    const m = line.match(/^(\d+)\.\s+(.*)$/) || line.match(/^-\s+(.*)$/);
    if (m) {
      const ordered = /^\d/.test(line);
      if (!list || list.ordered !== ordered) { flush(); list = { ordered, items: [] }; }
      list.items.push(<li key={i} className="marker:text-ink-soft">{inline(m[m.length - 1], onOpen)}</li>);
      return;
    }
    flush();
    if (!line) return;
    if (line.startsWith("> ")) {
      const warn = line.includes("⚠");
      blocks.push(<div key={i} className={`my-2 border-l-4 px-3 py-1.5 rounded-r text-[0.92em] ${warn
        ? "border-bad bg-bad-soft text-bad" : "border-tomato/40 bg-paper text-ink-soft"}`}>{inline(line.slice(2), onOpen)}</div>);
    } else {
      blocks.push(<p key={i} className="my-1">{inline(line, onOpen)}</p>);
    }
  });
  flush();
  return <div className="leading-relaxed">{blocks}</div>;
}
