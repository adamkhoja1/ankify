export type CardType = "basic" | "cloze" | "reversible";
export type ReviewAction = "accept" | "edit" | "discard";

export interface Card {
  id: string;
  type: CardType;
  front: string;
  back: string;
  cloze_text: string;
  extra: string;
  subdeck: string;
  tags: string[];
  source_ref: string;
  rationale: string;
}

export interface Decision {
  card_id: string;
  action: ReviewAction;
  edited_card: Card | null;
  feedback: string;
}

export interface Subdeck {
  name: string;
  count: number;
}

export interface SessionState {
  round: number;
  deck: string;
  pending: number;
  accepted: number;
  export_path: string;
  cards: Card[];
  decisions: Record<string, Decision>;
  requests: string[];
  subdecks: Subdeck[];
}

export interface ModelConfig {
  provider: "openai" | "anthropic";
  model: string;
  reasoning_effort: string;
  has_key: boolean;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? res.statusText);
  return res.json() as Promise<T>;
}

export const getSession = () => fetch("/api/session").then(json<SessionState>);

export const postDecision = (body: {
  card_id: string;
  action: ReviewAction;
  edited_card?: Card | null;
  feedback?: string;
}) =>
  fetch("/api/decision", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(json<{ pending: number; approved: number }>);

export const regenerate = () =>
  fetch("/api/regenerate", { method: "POST" }).then(json<{ round: number; cards: Card[] }>);

export const postRequests = (requests: string[]) =>
  fetch("/api/requests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ requests }),
  }).then(json<{ requests: string[] }>);

export const getDecks = () => fetch("/api/decks").then(json<{ decks: string[] }>);

export const importCards = (deck: string, tags: string[] = []) =>
  fetch("/api/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ deck, tags }),
  }).then(json<{ added: number; duplicates: number; failed: number; total: number }>);

export const getConfig = () => fetch("/api/config").then(json<ModelConfig>);

export const saveConfig = (body: {
  provider: string;
  model: string;
  reasoning_effort: string;
  api_key?: string;
}) =>
  fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(json<ModelConfig>);

export const setSubdeck = (card_id: string, subdeck: string) =>
  fetch("/api/subdeck", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ card_id, subdeck }),
  }).then(json<{ subdecks: Subdeck[] }>);

export const renameSubdeck = (oldName: string, newName: string) =>
  fetch("/api/subdeck/rename", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old: oldName, new: newName }),
  }).then(json<{ renamed: number; subdecks: Subdeck[] }>);

const CLOZE_RE = /\{\{c\d+::([\s\S]*?)\}\}/g;

/** Hide ([…] / [hint]) or reveal cloze deletions. */
function renderCloze(text: string, reveal: boolean): string {
  return text.replace(CLOZE_RE, (_m, inner: string) => {
    const [answer, hint] = inner.split("::");
    const shown = reveal ? answer : `[${hint ?? "…"}]`;
    return `<span class="cloze">${shown}</span>`;
  });
}

/** Normalize Anki's LaTeX delimiters to the MathJax forms the renderer is configured for. */
function ankiMath(html: string): string {
  return html
    .replace(/\[\$\$\]([\s\S]*?)\[\$\$\]/g, "\\[$1\\]")
    .replace(/\[\$\]([\s\S]*?)\[\$\]/g, "\\($1\\)")
    .replace(/\[latex\]([\s\S]*?)\[\/latex\]/g, "\\[$1\\]")
    .replace(/\[mathjax\]([\s\S]*?)\[\/mathjax\]/g, "\\($1\\)");
}

/** Point bare Anki-style <img src="file.png"> at the media server for preview. */
function withMedia(html: string): string {
  return html.replace(/(<img\b[^>]*?\ssrc=")(?!https?:|data:|\/)([^"]+)(")/gi, "$1/media/$2$3");
}

/** Final HTML for the question side (cloze hidden), Anki math + media resolved. */
export function promptSide(card: Card): string {
  const raw = card.type === "cloze" ? renderCloze(card.cloze_text, false) : card.front;
  return withMedia(ankiMath(raw));
}

/** Final HTML for the answer side (cloze revealed), Anki math + media resolved. */
export function answerSide(card: Card): string {
  let raw: string;
  if (card.type === "cloze") {
    raw = renderCloze(card.cloze_text, true);
    if (card.extra) raw += `<div class="extra">${card.extra}</div>`;
  } else {
    raw = card.back;
  }
  return withMedia(ankiMath(raw));
}
