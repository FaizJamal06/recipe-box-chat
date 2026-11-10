"""Exploratory run of eval/explore.txt through the real API (TestClient over data/recipes.db; the real LLM when
GEMINI_API_KEY is set). Writes eval/explore_transcripts/one_session.md (every message in one session) and
fresh_sessions.md (one session per '## ' block), plus a one-line-per-turn summary to stdout.
Run: python eval/explore.py   (the per-session rate limit is lifted for the run)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from fastapi.testclient import TestClient  # noqa: E402

from app import api  # noqa: E402

OUT = ROOT / "eval" / "explore_transcripts"


def blocks() -> list[tuple[str, list[str]]]:
    """[(block title, messages)] from explore.txt."""
    out = []
    for line in (ROOT / "eval" / "explore.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            out.append((line[3:].strip(), []))
        elif line.strip() and not line.startswith("#"):
            out[-1][1].append(line.strip())
    return out


def run(c: TestClient, title: str, msgs: list[str]) -> list[str]:
    """One session; markdown transcript lines. Prints a summary line per turn."""
    md, sid = [f"## {title}", ""], None
    for m in msgs:
        r = c.post("/api/chat", json={"session_id": sid, "message": m})
        j = r.json()
        if r.status_code != 200:
            md += [f"**> {m}**", f"HTTP {r.status_code}: {j}", ""]
            continue
        sid, p, pl = j["session_id"], j["payload"], j["planner"]
        md += [f"**> {m}**", "", f"`{pl['label']}` · {pl['calls']} LLM calls · {pl['turn_ms']} ms · "
               f"type={p['type']}" + (f" · total={p['total']}" if "total" in p else "")
               + (f" · STRIPPED {p['postcheck']['stripped']}" if p["postcheck"]["stripped"] else ""), ""]
        if j["voice"]:
            md += [f"> 🗣 {j['voice']}", ""]
        md += [j["reply_md"], "", "Suggestions: " + " · ".join(s["label"] for s in j["suggestions"]),
               f"Trace: {' | '.join(t for t in j['trace'] if t.startswith(('LLM call', 'Voice')))}", "", "---", ""]
        print(f"{title[:14]:14} | {m[:42]:42} | {pl['label'][:34]:34} | {p['type']:11} | "
              f"{p.get('total', ''):>6} | voice={'yes' if j['voice'] else 'no '} | {j['reply_md'].splitlines()[0][:70]}")
    return md


def main() -> None:
    """Run all messages as one session, then each block as a fresh session."""
    api.RATE = 10_000
    OUT.mkdir(parents=True, exist_ok=True)
    bs = blocks()
    with TestClient(api.app) as c:
        one = run(c, "one session (all messages)", [m for _, ms in bs for m in ms])
        fresh = [line for t, ms in bs for line in run(c, t, ms)]
    (OUT / "one_session.md").write_text("# Exploratory run: one session\n\n" + "\n".join(one), encoding="utf-8")
    (OUT / "fresh_sessions.md").write_text("# Exploratory run: fresh sessions\n\n" + "\n".join(fresh), encoding="utf-8")


if __name__ == "__main__":
    main()
