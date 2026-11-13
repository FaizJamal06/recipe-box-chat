// Screenshots of the running app through the Chrome DevTools Protocol (no npm deps: Node 22 has fetch + WebSocket).
// Each view replays a conversation with ?q=..., waits for the last reply, and captures it at 1440 px (viewport) and
// 390 px (full page), with developer view off and on.
// Usage: node scripts/screenshots.mjs [outdir]    (server on $BASE, default http://127.0.0.1:8000; $CHROME = browser)
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const BASE = process.env.BASE || "http://127.0.0.1:8000";
const CHROME = process.env.CHROME || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const OUT = process.argv[2] || "docs/screenshots";
const VIEWS = [  // [name, messages, panel tab]
  ["search", ["Find a penne pasta recipe", "I cannot have dairy"], "results"],
  ["match", ["I have eggs, onions, tomatoes, and rice. Suggest five recipes using as many as possible, no peanuts, at most six steps, fewest additional ingredients."], "results"],
  ["stats", ["How many recipes contain both garlic and onion? What percentage of the dataset is that?"], "calc"],
  ["substitute", ["Take this banana bread recipe and remove eggs. Use only ingredients that appear in the dataset. What replacements have evidence from related baked recipes, and how might the texture change?"], "results"],
];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

mkdirSync(OUT, { recursive: true });
const chrome = spawn(CHROME, ["--headless=new", "--remote-debugging-port=9333", "--no-first-run", "--hide-scrollbars",
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "rbshots-"))}`, "about:blank"], { stdio: "ignore" });
let targets;
for (let i = 0; i < 50 && !targets; i++) {
  await sleep(200);
  targets = await fetch("http://127.0.0.1:9333/json").then((r) => r.json()).catch(() => null);
}
const ws = new WebSocket(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let seq = 0;
const waiting = new Map();
ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); waiting.get(m.id)?.(m); waiting.delete(m.id); });
const send = (method, params = {}) => new Promise((resolve) => {
  waiting.set(++seq, (m) => resolve(m.result)); ws.send(JSON.stringify({ id: seq, method, params }));
});
const evaluate = async (expression) => (await send("Runtime.evaluate", { expression, returnByValue: true })).result.value;

for (const [name, msgs, tab] of VIEWS) {
  for (const width of [1440, 390]) {
    for (const dev of [0, 1]) {
      const height = width > 900 ? 900 : 844;
      await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width < 900 });
      const qs = msgs.map((m) => "q=" + encodeURIComponent(m)).join("&");
      await send("Page.navigate", { url: `${BASE}/?${qs}&tab=${tab}&dev=${dev}` });
      const t0 = Date.now();
      while (Date.now() - t0 < 180_000) {  // done: one bot bubble per message and no loader
        await sleep(500);
        if (await evaluate(`document.querySelectorAll('.rounded-tl-sm').length >= ${msgs.length} && !document.querySelector('[aria-live=polite]')`)) break;
      }
      await sleep(800);
      // phones: the full page (the panel stacks under the chat), captured beyond the viewport so 100dvh stays 844 px
      const h = width < 900 ? Math.ceil((await send("Page.getLayoutMetrics")).cssContentSize.height) : height;
      const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: width < 900,
        ...(width < 900 ? { clip: { x: 0, y: 0, width, height: h, scale: 1 } } : {}) });
      const file = join(OUT, `${name}-${width}-${dev ? "dev" : "clean"}.png`);
      writeFileSync(file, Buffer.from(shot.data, "base64"));
      console.log(file);
    }
  }
}
ws.close();
chrome.kill();
