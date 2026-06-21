import { useCallback, useEffect, useState } from "react";
import {
  answerSide,
  Card,
  Decision,
  getDecks,
  getSession,
  importCards,
  postDecision,
  promptSide,
  regenerate,
  ReviewAction,
  SessionState,
} from "./api";

export default function App() {
  const [session, setSession] = useState<SessionState | null>(null);
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [editing, setEditing] = useState<Card | null>(null);
  const [feedback, setFeedback] = useState("");
  const [decks, setDecks] = useState<string[]>([]);
  const [deck, setDeck] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");

  const load = useCallback(async () => {
    const s = await getSession();
    setSession(s);
    setDeck((d) => d || s.deck);
  }, []);

  useEffect(() => {
    load().catch((e) => setToast(String(e)));
    getDecks().then((d) => setDecks(d.decks)).catch(() => {});
  }, [load]);

  const cards = session?.cards ?? [];
  const card = cards[idx];
  const decisions = session?.decisions ?? {};
  const decided = Object.keys(decisions).filter((id) => cards.some((c) => c.id === id)).length;
  const approved = Object.values(decisions).filter(
    (d) => cards.some((c) => c.id === d.card_id) && d.action !== "discard",
  ).length;

  const advance = useCallback(() => {
    setFlipped(false);
    setEditing(null);
    setFeedback("");
    setIdx((i) => Math.min(i + 1, cards.length - 1));
  }, [cards.length]);

  const decide = useCallback(
    async (action: ReviewAction) => {
      if (!card || busy) return;
      setBusy(true);
      try {
        await postDecision({
          card_id: card.id,
          action,
          edited_card: action === "edit" ? editing : null,
          feedback,
        });
        await load();
        advance();
      } catch (e) {
        setToast(String(e));
      } finally {
        setBusy(false);
      }
    },
    [card, busy, editing, feedback, load, advance],
  );

  const onRegenerate = useCallback(async () => {
    setBusy(true);
    setToast("regenerating…");
    try {
      await regenerate();
      await load();
      setIdx(0);
      setToast("new round ready");
    } catch (e) {
      setToast(String(e));
    } finally {
      setBusy(false);
    }
  }, [load]);

  const onImport = useCallback(async () => {
    if (!deck) return setToast("pick a deck name first");
    setBusy(true);
    try {
      const r = await importCards(deck);
      setToast(`imported ${r.added} (${r.duplicates} dup, ${r.failed} failed)`);
    } catch (e) {
      setToast(String(e));
    } finally {
      setBusy(false);
    }
  }, [deck]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (editing || e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)
        return;
      if (e.key === " ") {
        e.preventDefault();
        setFlipped((f) => !f);
      } else if (e.key === "a") decide("accept");
      else if (e.key === "d") decide("discard");
      else if (e.key === "e") setEditing(card ?? null);
      else if (e.key === "ArrowRight") advance();
      else if (e.key === "ArrowLeft") setIdx((i) => Math.max(i - 1, 0));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [decide, advance, editing, card]);

  if (!session) return <main className="wrap"><p className="muted">{toast || "loading…"}</p></main>;
  if (!card)
    return (
      <main className="wrap">
        <p className="muted">No cards in this round.</p>
        <Footer {...{ decks, deck, setDeck, onRegenerate, onImport, busy }} />
      </main>
    );

  const decision: Decision | undefined = decisions[card.id];

  return (
    <main className="wrap">
      <header className="bar">
        <span className="tag">round {session.round}</span>
        <span className="muted">
          card {idx + 1}/{cards.length} · {decided} decided · {approved} approved ·{" "}
          {session.pending} pending
        </span>
        <span className={`tag type-${card.type}`}>{card.type}</span>
      </header>

      {editing ? (
        <CardEditor card={editing} onChange={setEditing} onSave={() => decide("edit")} busy={busy} />
      ) : (
        <section className={`card ${flipped ? "flipped" : ""}`} onClick={() => setFlipped((f) => !f)}>
          <div className="side prompt">{promptSide(card)}</div>
          {flipped && <div className="side answer">{answerSide(card)}</div>}
          {!flipped && <div className="hint">click or press space to flip</div>}
          {decision && <div className={`stamp ${decision.action}`}>{decision.action}</div>}
        </section>
      )}

      {!editing && (
        <>
          <textarea
            className="feedback"
            placeholder="optional feedback for the next round (why this card is off, what to cover instead)…"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
          />
          <div className="actions">
            <button className="accept" onClick={() => decide("accept")} disabled={busy}>
              Accept <kbd>a</kbd>
            </button>
            <button onClick={() => setEditing(card)} disabled={busy}>
              Edit <kbd>e</kbd>
            </button>
            <button className="discard" onClick={() => decide("discard")} disabled={busy}>
              Discard <kbd>d</kbd>
            </button>
          </div>
        </>
      )}

      <Footer {...{ decks, deck, setDeck, onRegenerate, onImport, busy }} />
      {toast && <div className="toast" onClick={() => setToast("")}>{toast}</div>}
    </main>
  );
}

function CardEditor({
  card,
  onChange,
  onSave,
  busy,
}: {
  card: Card;
  onChange: (c: Card) => void;
  onSave: () => void;
  busy: boolean;
}) {
  const set = (patch: Partial<Card>) => onChange({ ...card, ...patch });
  return (
    <section className="card editing">
      {card.type === "cloze" ? (
        <textarea
          value={card.cloze_text}
          onChange={(e) => set({ cloze_text: e.target.value })}
          placeholder="cloze text with {{c1::deletion}}"
        />
      ) : (
        <>
          <textarea value={card.front} onChange={(e) => set({ front: e.target.value })} placeholder="front" />
          <textarea value={card.back} onChange={(e) => set({ back: e.target.value })} placeholder="back" />
        </>
      )}
      <div className="actions">
        <button className="accept" onClick={onSave} disabled={busy}>
          Save &amp; accept
        </button>
      </div>
    </section>
  );
}

function Footer({
  decks,
  deck,
  setDeck,
  onRegenerate,
  onImport,
  busy,
}: {
  decks: string[];
  deck: string;
  setDeck: (d: string) => void;
  onRegenerate: () => void;
  onImport: () => void;
  busy: boolean;
}) {
  return (
    <footer className="footer">
      <button onClick={onRegenerate} disabled={busy}>
        ↻ Regenerate round
      </button>
      <span className="grow" />
      <input
        list="decks"
        value={deck}
        onChange={(e) => setDeck(e.target.value)}
        placeholder="deck name"
      />
      <datalist id="decks">
        {decks.map((d) => (
          <option key={d} value={d} />
        ))}
      </datalist>
      <button className="accept" onClick={onImport} disabled={busy}>
        Import approved → Anki
      </button>
    </footer>
  );
}
