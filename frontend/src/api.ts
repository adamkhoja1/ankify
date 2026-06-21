export type CardType = "basic" | "cloze" | "reversible";
export type ReviewAction = "accept" | "edit" | "discard";

export interface Card {
  id: string;
  type: CardType;
  front: string;
  back: string;
  cloze_text: string;
  extra: string;
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

export interface SessionState {
  round: number;
  deck: string;
  pending: number;
  cards: Card[];
  decisions: Record<string, Decision>;
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

export const getDecks = () => fetch("/api/decks").then(json<{ decks: string[] }>);

export const importCards = (deck: string, tags: string[] = []) =>
  fetch("/api/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ deck, tags }),
  }).then(json<{ added: number; duplicates: number; failed: number; total: number }>);

/** Render the prompt (question) side, hiding cloze deletions. */
export function promptSide(card: Card): string {
  if (card.type === "cloze") return card.cloze_text.replace(/\{\{c\d+::(.*?)(::.*?)?\}\}/g, "[…]");
  return card.front;
}

/** Render the answer side, revealing cloze deletions. */
export function answerSide(card: Card): string {
  if (card.type === "cloze") {
    const revealed = card.cloze_text.replace(/\{\{c\d+::(.*?)(::.*?)?\}\}/g, "$1");
    return card.extra ? `${revealed}\n\n${card.extra}` : revealed;
  }
  return card.back;
}
