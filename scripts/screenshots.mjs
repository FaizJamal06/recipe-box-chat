// Screenshots of the running app through the Chrome DevTools Protocol (no npm deps: Node 22 has fetch + WebSocket).
// Each view replays a conversation with ?q=..., waits for the last reply, optionally taps buttons, and captures it.
//   node scripts/screenshots.mjs [outdir]            desktop set: 4 views at 1440 and 390 px, developer view off/on
//   node scripts/screenshots.mjs --mobile [outdir]   phone set: 9 views at 360, 390, 430 and 768 px, plus the overflow
//     check on every view: document scrollWidth <= clientWidth, and no element reaching past the viewport edge outside
//     an intentional sideways scroller (chip rows, tabs). Exits 1 if anything overflows.
// Server on $BASE (default http://127.0.0.1:8000); $CHROME = the browser binary.
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const BASE = process.env.BASE || "http://127.0.0.1:8000";
const CHROME = process.env.CHROME || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const MOBILE = process.argv.includes("--mobile");
const OUT = process.argv.filter((a) => !a.startsWith("--"))[2] || (MOBILE ? "docs/screenshots/mobile" : "docs/screenshots");
const PENNE = ["Find a penne pasta recipe", "I cannot have dairy"];
const MATCH = ["I have eggs, onions, tomatoes, and rice. Suggest five recipes using as many as possible, no peanuts, at most six steps, fewest additional ingredients."];
const DEMO7 = ["Take this banana bread recipe and remove eggs. Use only ingredients that appear in the dataset. What replacements have evidence from related baked recipes, and how might the texture change?"];
const tap = (label) => `[...document.querySelectorAll('button')].find((b) => b.textContent.trim().startsWith(${JSON.stringify(label)}))?.click()`;
const DESKTOP = [  // [name, messages, panel tab]
  ["search", PENNE, "results"], ["match", MATCH, "results"],
  ["stats", ["How many recipes contain both garlic and onion? What percentage of the dataset is that?"], "calc"],
  ["substitute", DEMO7, "results"],
];
const PHONE = [  // [name, messages, taps after the reply, wait-for expression]
  ["empty", [], []],
  ["search", PENNE, []],
  ["search-sheet", PENNE, ["View "]],
  ["match", MATCH, []],
  ["match-sheet", MATCH, ["View "]],
  ["substitute-adapted", DEMO7, ["View "]],
  ["substitute-original", DEMO7, ["View ", "original"]],
  ["substitute-evidence", DEMO7, ["View ", "Evidence"]],
  ["drawer", ["Find a penne pasta recipe", "show me the first one"], [],
   "document.querySelector('[role=dialog] ol li') !== null"],
];
const OVERFLOW = `(() => {
  const d = document.documentElement, w = d.clientWidth, bad = [];
  if (d.scrollWidth > w) bad.push('document scrollWidth ' + d.scrollWidth + ' > ' + w);
  const scroller = (el) => { for (let p = el.parentElement; p; p = p.parentElement) {
    const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll') return true; } return false; };
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width && r.height && (r.right > w + 1 || r.left < -1) && !scroller(el) && getComputedStyle(el).position !== 'fixed')
      bad.push(el.tagName.toLowerCase() + '.' + String(el.className).slice(0, 40) + ' "' + (el.textContent || '').trim().slice(0, 40) + '" right=' + Math.round(r.right));
  }
  return bad.slice(0, 8);
})()`;
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

/** Load a conversation at this size, wait for the last reply (and `ready`), then perform the taps. */
async function load(width, height, msgs, query, taps = [], ready = "true") {
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width < 900 });
  const qs = msgs.map((m) => "q=" + encodeURIComponent(m)).join("&");
  await send("Page.navigate", { url: `${BASE}/?${qs}${qs ? "&" : ""}${query}` });
  const t0 = Date.now();
  while (Date.now() - t0 < 180_000) {  // done: one bot bubble per message, no loader, and the view's own condition
    await sleep(500);
    if (await evaluate(`document.querySelectorAll('.rounded-tl-sm').length >= ${msgs.length} && ` +
                       `!document.querySelector('[aria-live=polite]') && (${ready})`)) break;
  }
  for (const label of taps) { await sleep(400); await evaluate(tap(label)); }
  await sleep(900);
}

async function shot(file, clip) {
  const s = await send("Page.captureScreenshot", { format: "png", ...(clip ? { captureBeyondViewport: true, clip } : {}) });
  writeFileSync(file, Buffer.from(s.data, "base64"));
  console.log(file);
}

let failed = 0;
if (MOBILE) {
  for (const [name, msgs, taps, ready] of PHONE) {
    for (const [width, height] of [[360, 780], [390, 844], [430, 932], [768, 1024]]) {
      await load(width, height, msgs, "dev=0", taps, ready);
      const bad = await evaluate(OVERFLOW);
      if (bad.length) { failed++; console.log(`OVERFLOW ${name} @ ${width}: ${bad.join(" | ")}`); }
      await shot(join(OUT, `${name}-${width}.png`));
    }
  }
  console.log(failed ? `${failed} view(s) overflow` : "overflow check: every view fits (scrollWidth <= clientWidth, nothing past the edge)");
} else {
  for (const [name, msgs, tab] of DESKTOP) {
    for (const width of [1440, 390]) {
      for (const dev of [0, 1]) {
        const height = width > 900 ? 900 : 844;
        await load(width, height, msgs, `tab=${tab}&dev=${dev}`);
        await shot(join(OUT, `${name}-${width}-${dev ? "dev" : "clean"}.png`));
      }
    }
  }
}
ws.close();
chrome.kill();
process.exit(failed ? 1 : 0);
