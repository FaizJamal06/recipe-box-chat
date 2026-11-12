// Types mirror backend/app/api.py + web.py. Every number shown in the UI comes from these payloads.

export type ChipKind = "matched" | "extra" | "unused" | "violation" | "may_contain" | "ok";
export type Chip = { kind: ChipKind; label: string; detail: string };

export type Card = {
  id: string;
  title: string;
  source: string;
  n_ingredients: number;
  n_steps: number;
  chips: Chip[];
  evidence?: string[];
  score?: number;
  parts?: Record<string, number>;
  staples?: string[];
};

export type Calc = {
  label: string;
  value: unknown;
  filters: string;
  n_analyzed: number;
  denominator: number;
  method: string;
  sql: string | null;
  normalization_note: string;
  notes: string[];
};

export type Recipe = {
  id: string;
  source: string;
  title: string;
  ingredients: string[];
  steps: string[];
  paragraph: boolean;
  n_ingredients: number;
  n_steps: number;
  tags: Record<string, string>;
  unverified: Record<string, string[]>;
  parsed: { line_no: number; raw: string; canonical: string | null; qty: number | null; unit: string | null;
            is_alt: number; is_header: number; is_not_food: number }[];
};

export type TierCounts = { n_with: number; in_with: number; n_without: number; support: number; lift: number };
export type Candidate = { name: string; kind: string; label: string; roles: string[]; strength: Strength;
                          conflicting: boolean; explicit: string[]; ids: string[]; quantity: string;
                          snippets: { id: string; text: string }[]; tiers: Record<"L1" | "L2" | "L3", TierCounts> };
export type Strength = "Strong" | "Moderate" | "Weak" | "None";
export type SubPart = { item: string; affected: string[]; roles: string[]; target_qty: string;
                        conflicting: boolean; strength: Strength; chosen: string | null; candidates: Candidate[];
                        rejected: { name: string; reason: string }[] };
export type Adaptation = { ingredients: { op: "keep" | "remove" | "add"; text: string }[];
                           steps: { n: number; old: string; text: string; changed: boolean; reason: string }[];
                           prep: string[]; source: "model" | "fallback"; gate: { what: string; reason: string }[];
                           verified: string[]; predicted: string | null; predicted_status: string;
                           safety_line: string | null; caveat: string };

export type Payload = {
  type: "search" | "match" | "stats" | "recipe" | "unsupported" | "text" | "substitute";
  cards: Card[];
  calc?: Calc[];
  total?: number;
  alternatives?: { violates: string; cards: Card[] }[];
  have?: string[];
  rows?: { name: string; recipes: number }[];
  recipe?: Recipe;
  more_cards?: Card[];  // lenient mode: recipes with an ingredient that couldn't be verified, ranked last
  n_unverified?: number;
  postcheck: { ids_in_reply: number; stripped: string[] };
  // substitution (type "substitute")
  target?: { id: string; title: string };
  context?: string;
  dish?: string;
  tiers?: Record<string, number>;
  restrictions?: string[];
  question?: string;
  notes?: string[];
  parts?: SubPart[];
  adaptation?: Adaptation | null;
};

export type State = {
  active_task: string | null;
  query_text: string | null;
  include: string[];
  exclude: string[];
  exclude_tags: string[];
  diets: { name: string; tags: string[] }[];
  max_steps: number | null;
  have: string[];
  prefs: string[];
  staples: boolean;
  strict_may_contain: boolean;
  selected_recipe_id: string | null;
};

export type Planner = { kind: "llm" | "rule" | "guard" | "ui"; detail: string; label: string; reason: string;
                        calls: number; ms: number; prompt_tokens: number; errors: string[]; turn_ms: number;
                        model: string | null };
export type Suggestion = { label: string; message: string };

export type ChatResponse = { session_id: string; reply_md: string; voice: string | null; payload: Payload;
                             state: State; trace: string[]; planner: Planner; suggestions: Suggestion[] };

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { headers: { "Content-Type": "application/json" }, ...init });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || body.detail || `HTTP ${r.status}`);
  return body as T;
}

export const api = {
  chat: (session_id: string | null, message: string) =>
    call<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify({ session_id, message }) }),
  patch: (sid: string, op: "remove" | "set", field: string, value: unknown) =>
    call<ChatResponse>(`/api/session/${sid}/state`, { method: "PATCH", body: JSON.stringify({ op, field, value }) }),
  reset: (sid: string) => call<{ state: State }>(`/api/session/${sid}/reset`, { method: "POST" }),
  // ids contain '/' and '.': encode it whole so the browser never normalizes a '..' segment
  recipe: (id: string) => call<Recipe>(`/api/recipe/${encodeURIComponent(id)}`),
  health: () => call<{ valid: number; total: number; llm: { model: string | null; status: string } }>("/api/health"),
};
