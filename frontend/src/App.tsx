import { type ReactNode, type RefObject, useCallback, useEffect, useRef, useState } from "react";
import DOMPurify from "dompurify";
import { MathJax } from "better-react-mathjax";
import {
  answerSide,
  Card,
  Decision,
  getConfig,
  getDecks,
  getSession,
  importCards,
  ModelConfig,
  postDecision,
  postRequests,
  promptSide,
  regenerate,
  renameSubdeck,
  ReviewAction,
  saveConfig,
  SessionState,
  setSubdeck,
  Subdeck,
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
  const [requests, setRequests] = useState<string[]>([]);
  const [reqInput, setReqInput] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [manageOpen, setManageOpen] = useState(false);
  const [subdeckInput, setSubdeckInput] = useState("");
  const feedbackRef = useRef<HTMLTextAreaElement>(null);
  const reqRef = useRef<HTMLTextAreaElement>(null);

  const load = useCallback(async () => {
    const s = await getSession();
    setSession(s);
    setDeck((d) => d || s.deck);
    setRequests(s.requests);
  }, []);

  const addRequest = useCallback(async () => {
    const r = reqInput.trim();
    if (!r) return;
    const next = [...requests, r];
    setRequests(next);
    setReqInput("");
    try {
      await postRequests(next);
    } catch (e) {
      setToast(String(e));
    }
  }, [reqInput, requests]);

  const removeRequest = useCallback(
    async (i: number) => {
      const next = requests.filter((_, j) => j !== i);
      setRequests(next);
      try {
        await postRequests(next);
      } catch (e) {
        setToast(String(e));
      }
    },
    [requests],
  );

  useEffect(() => {
    load().catch((e) => setToast(String(e)));
    getDecks().then((d) => setDecks(d.decks)).catch(() => {});
  }, [load]);

  // On first load, resume at the first card you haven't decided yet.
  const resumed = useRef(false);
  useEffect(() => {
    if (session && !resumed.current) {
      resumed.current = true;
      const firstPending = session.cards.findIndex((c) => !session.decisions[c.id]);
      if (firstPending > 0) setIdx(firstPending);
    }
  }, [session]);

  const cards = session?.cards ?? [];
  const card = cards[idx];
  const decisions = session?.decisions ?? {};
  const decided = Object.keys(decisions).filter((id) => cards.some((c) => c.id === id)).length;
  const approved = Object.values(decisions).filter(
    (d) => cards.some((c) => c.id === d.card_id) && d.action !== "discard",
  ).length;

  const subdecks = session?.subdecks ?? [];

  // Keep the inline subdeck input in sync with whichever card is showing.
  useEffect(() => {
    setSubdeckInput(card?.subdeck ?? "");
  }, [card?.id, card?.subdeck]);

  const commitSubdeck = useCallback(async () => {
    if (!card) return;
    const value = subdeckInput.trim();
    if (value === (card.subdeck ?? "")) return; // no change
    try {
      await setSubdeck(card.id, value);
      await load();
    } catch (e) {
      setToast(String(e));
    }
  }, [card, subdeckInput, load]);

  const onRenameSubdeck = useCallback(
    async (oldName: string, newName: string) => {
      try {
        await renameSubdeck(oldName, newName);
        await load();
      } catch (e) {
        setToast(String(e));
      }
    },
    [load],
  );

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
      // Never hijack browser/OS shortcuts (Cmd+R reload, Cmd+W, Cmd+C, …).
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      // A modal owns the keyboard while it's open (it handles its own Escape).
      if (settingsOpen || manageOpen) return;
      // While editing, Escape cancels back to the card without deciding; ignore other keys.
      if (editing) {
        if (e.key === "Escape") {
          e.preventDefault();
          setEditing(null);
        }
        return;
      }
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === " ") {
        e.preventDefault();
        setFlipped((f) => !f);
      } else if (e.key === "a") decide("accept");
      else if (e.key === "d") decide("discard");
      else if (e.key === "e") setEditing(card ?? null);
      else if (e.key === "w") {
        e.preventDefault();
        feedbackRef.current?.focus();
      } else if (e.key === "r") {
        e.preventDefault();
        reqRef.current?.focus();
      } else if (e.key === "ArrowRight") advance();
      else if (e.key === "ArrowLeft") setIdx((i) => Math.max(i - 1, 0));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [decide, advance, editing, card, settingsOpen, manageOpen]);

  if (!session) return <main className="wrap"><p className="muted">{toast || "loading…"}</p></main>;
  if (!card)
    return (
      <main className="wrap">
        <header className="bar">
          <span className="muted">No pending cards in this round.</span>
          <button className="icon-btn" title="Manage subdecks" onClick={() => setManageOpen(true)}>
            🗂
          </button>
          <button className="icon-btn" title="Model settings" onClick={() => setSettingsOpen(true)}>
            ⚙
          </button>
        </header>
        <RequestZone {...{ requests, reqInput, setReqInput, reqRef, addRequest, removeRequest }} />
        <ExportBar accepted={session.accepted} exportPath={session.export_path} />
        <Footer
          {...{ decks, deck, setDeck, onRegenerate, onImport, busy, requestCount: requests.length }}
        />
        {settingsOpen && (
          <SettingsModal onClose={() => setSettingsOpen(false)} onToast={setToast} />
        )}
        {manageOpen && (
          <ManageSubdecksModal
            subdecks={subdecks}
            onRename={onRenameSubdeck}
            onClose={() => setManageOpen(false)}
          />
        )}
        {toast && <div className="toast" onClick={() => setToast("")}>{toast}</div>}
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
        <button className="icon-btn" title="Manage subdecks" onClick={() => setManageOpen(true)}>
          🗂
        </button>
        <button className="icon-btn" title="Model settings" onClick={() => setSettingsOpen(true)}>
          ⚙
        </button>
      </header>

      {!editing && (
        <div className="subdeck-row">
          <label htmlFor="card-subdeck">Subdeck</label>
          <input
            id="card-subdeck"
            list="subdecks"
            value={subdeckInput}
            placeholder="(deck root) — e.g. Ch01 - The Market"
            onChange={(e) => setSubdeckInput(e.target.value)}
            onBlur={commitSubdeck}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                commitSubdeck();
                e.currentTarget.blur();
              } else if (e.key === "Escape") {
                setSubdeckInput(card.subdeck ?? "");
                e.currentTarget.blur();
              }
            }}
          />
          <datalist id="subdecks">
            {subdecks
              .filter((s) => s.name)
              .map((s) => (
                <option key={s.name} value={s.name} />
              ))}
          </datalist>
        </div>
      )}

      {editing ? (
        <CardEditor
          card={editing}
          onChange={setEditing}
          onSave={() => decide("edit")}
          onCancel={() => setEditing(null)}
          busy={busy}
        />
      ) : (
        <section className={`card ${flipped ? "flipped" : ""}`} onClick={() => setFlipped((f) => !f)}>
          {card.type === "cloze" ? (
            // Cloze: reveal in place — the same sentence with [...] replaced by the term.
            <div className="side prompt">
              <CardContent html={flipped ? answerSide(card) : promptSide(card)} />
            </div>
          ) : (
            <>
              <div className="side prompt">
                <CardContent html={promptSide(card)} />
              </div>
              {flipped && (
                <div className="side answer">
                  <CardContent html={answerSide(card)} />
                </div>
              )}
            </>
          )}
          {!flipped && <div className="hint">click or press space to flip</div>}
          {decision && <div className={`stamp ${decision.action}`}>{decision.action}</div>}
        </section>
      )}

      {!editing && (
        <>
          <div className="zone">
            <label className="zone-label">Your decision on this card</label>
            <div className="actions">
              <button className="accept" onClick={() => decide("accept")} disabled={busy}>
                ✓ Accept <kbd>a</kbd>
              </button>
              <button onClick={() => setEditing(card)} disabled={busy}>
                ✎ Edit it yourself <kbd>e</kbd>
              </button>
              <button className="discard" onClick={() => decide("discard")} disabled={busy}>
                ✗ Discard <kbd>d</kbd>
              </button>
            </div>
            <div className="zone-hint">
              <b>Edit it yourself</b> changes the card text now and accepts it.
            </div>
          </div>

          <div className="zone fb-zone">
            <label className="zone-label">
              Send it back to the model for the next round <kbd>w</kbd>
            </label>
            <textarea
              ref={feedbackRef}
              className="feedback"
              placeholder="what's wrong / what you want instead — e.g. “too vague, name the source” or “make this cloze”…"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (feedback.trim()) decide("discard");
                } else if (e.key === "Escape") {
                  e.currentTarget.blur();
                }
              }}
            />
            <div className="actions">
              <button className="discard" onClick={() => feedback.trim() && decide("discard")} disabled={busy}>
                ✗ Discard &amp; request a revision
              </button>
            </div>
            <div className="zone-hint">
              <b>Enter</b> = discard &amp; request a revision · <b>Shift+Enter</b> = new line · <b>Esc</b> = back to card
            </div>
          </div>
        </>
      )}

      <RequestZone {...{ requests, reqInput, setReqInput, reqRef, addRequest, removeRequest }} />
      <ExportBar accepted={session.accepted} exportPath={session.export_path} />
      <Footer
        {...{ decks, deck, setDeck, onRegenerate, onImport, busy, requestCount: requests.length }}
      />
      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} onToast={setToast} />}
      {manageOpen && (
        <ManageSubdecksModal
          subdecks={subdecks}
          onRename={onRenameSubdeck}
          onClose={() => setManageOpen(false)}
        />
      )}
      {toast && <div className="toast" onClick={() => setToast("")}>{toast}</div>}
    </main>
  );
}

// Renders Anki HTML (images, bold, etc.) and typesets LaTeX via MathJax. Cards are LLM
// output grounded in arbitrary source documents, so the HTML is sanitized before injection
// — a prompt-injected source must not be able to run script in the review app.
function CardContent({ html }: { html: string }) {
  return (
    <MathJax dynamic>
      <div
        className="content"
        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }}
      />
    </MathJax>
  );
}

function CardEditor({
  card,
  onChange,
  onSave,
  onCancel,
  busy,
}: {
  card: Card;
  onChange: (c: Card) => void;
  onSave: () => void;
  onCancel: () => void;
  busy: boolean;
}) {
  const set = (patch: Partial<Card>) => onChange({ ...card, ...patch });
  return (
    <section className="card editing">
      <div className="edit-head">
        ✎ Editing the card text yourself — Save accepts this version · Esc cancels
      </div>
      {card.type === "cloze" ? (
        <textarea
          autoFocus
          value={card.cloze_text}
          onChange={(e) => set({ cloze_text: e.target.value })}
          placeholder="cloze text with {{c1::deletion}}"
        />
      ) : (
        <>
          <textarea
            autoFocus
            value={card.front}
            onChange={(e) => set({ front: e.target.value })}
            placeholder="front"
          />
          <textarea
            value={card.back}
            onChange={(e) => set({ back: e.target.value })}
            placeholder="back"
          />
        </>
      )}
      <input
        className="subdeck-edit"
        value={card.subdeck}
        onChange={(e) => set({ subdeck: e.target.value })}
        placeholder="subdeck (optional) — e.g. Ch01 - The Market"
      />
      <div className="actions">
        <button className="accept" onClick={onSave} disabled={busy}>
          Save &amp; accept
        </button>
        <button onClick={onCancel} disabled={busy}>
          Cancel <kbd>esc</kbd>
        </button>
      </div>
    </section>
  );
}

function ExportBar({ accepted, exportPath }: { accepted: number; exportPath: string }) {
  const filename = exportPath.split("/").pop() || "cards.apkg";
  return (
    <div className="export-bar">
      {accepted > 0 ? (
        <a className="dl-btn" href="/api/export.apkg" download={filename}>
          ⬇ Download accepted .apkg ({accepted})
        </a>
      ) : (
        <span className="muted">Accept cards to build the .apkg…</span>
      )}
      <span className="export-path" title={exportPath}>
        auto-saved to <code>{exportPath}</code>
      </span>
    </div>
  );
}

function RequestZone({
  requests,
  reqInput,
  setReqInput,
  reqRef,
  addRequest,
  removeRequest,
}: {
  requests: string[];
  reqInput: string;
  setReqInput: (s: string) => void;
  reqRef: RefObject<HTMLTextAreaElement>;
  addRequest: () => void;
  removeRequest: (i: number) => void;
}) {
  return (
    <div className="zone req-zone">
      <label className="zone-label">
        Request new cards for the next round <kbd>r</kbd>
      </label>
      {requests.length > 0 && (
        <ul className="req-list">
          {requests.map((r, i) => (
            <li key={i}>
              <span>{r}</span>
              <button onClick={() => removeRequest(i)} title="remove">
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <textarea
        ref={reqRef}
        className="req-input"
        placeholder="e.g. “a card on the budget line slope −p1/p2”"
        value={reqInput}
        onChange={(e) => setReqInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            addRequest();
          } else if (e.key === "Escape") {
            e.currentTarget.blur();
          }
        }}
      />
      <div className="zone-hint">
        <b>Enter</b> to queue · <b>Shift+Enter</b> for a new line. Queued requests become new
        cards when you ↻ Regenerate round.
      </div>
    </div>
  );
}

function Footer({
  decks,
  deck,
  setDeck,
  onRegenerate,
  onImport,
  busy,
  requestCount,
}: {
  decks: string[];
  deck: string;
  setDeck: (d: string) => void;
  onRegenerate: () => void;
  onImport: () => void;
  busy: boolean;
  requestCount: number;
}) {
  return (
    <footer className="footer">
      <button
        onClick={onRegenerate}
        disabled={busy}
        title="Keeps accepted/edited cards, creates your requested cards, and revises cards you discarded with feedback."
      >
        ↻ Regenerate round{requestCount ? ` (${requestCount} requested)` : ""}
      </button>
      <input
        className="deck-input"
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

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="icon-btn" onClick={onClose} title="Close">
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function SettingsModal({
  onClose,
  onToast,
}: {
  onClose: () => void;
  onToast: (s: string) => void;
}) {
  const [cfg, setCfg] = useState<ModelConfig | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getConfig()
      .then(setCfg)
      .catch((e) => onToast(String(e)));
  }, [onToast]);

  if (!cfg)
    return (
      <Modal title="Model settings" onClose={onClose}>
        <p className="muted">loading…</p>
      </Modal>
    );

  const save = async () => {
    setSaving(true);
    try {
      await saveConfig({
        provider: cfg.provider,
        model: cfg.model,
        reasoning_effort: cfg.reasoning_effort,
        api_key: apiKey || undefined,
      });
      onToast("settings saved");
      onClose();
    } catch (e) {
      onToast(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Model settings" onClose={onClose}>
      <div className="form">
        <label>
          Provider
          <select
            value={cfg.provider}
            onChange={(e) => setCfg({ ...cfg, provider: e.target.value as ModelConfig["provider"] })}
          >
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
          </select>
        </label>
        <label>
          Model
          <input
            value={cfg.model}
            onChange={(e) => setCfg({ ...cfg, model: e.target.value })}
            placeholder="gpt-5.5 / claude-opus-4-8"
          />
        </label>
        <label>
          Reasoning effort
          <input
            list="effort-options"
            value={cfg.reasoning_effort}
            onChange={(e) => setCfg({ ...cfg, reasoning_effort: e.target.value })}
            placeholder="high"
          />
          <datalist id="effort-options">
            <option value="minimal" />
            <option value="low" />
            <option value="medium" />
            <option value="high" />
            <option value="xhigh" />
            <option value="max" />
          </datalist>
        </label>
        <label>
          API key
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={cfg.has_key ? "key saved — leave blank to keep" : "paste your API key"}
          />
        </label>
        <div className="actions">
          <button className="accept" onClick={save} disabled={saving}>
            Save
          </button>
          <button onClick={onClose} disabled={saving}>
            Cancel <kbd>esc</kbd>
          </button>
        </div>
        <p className="zone-hint">
          Stored at <code>~/.config/ankify/config.json</code>. Effort maps to OpenAI{" "}
          <code>reasoning_effort</code> and Anthropic <code>output_config.effort</code> — free-form,
          so type whatever value your model accepts.
        </p>
      </div>
    </Modal>
  );
}

function ManageSubdecksModal({
  subdecks,
  onRename,
  onClose,
}: {
  subdecks: Subdeck[];
  onRename: (oldName: string, newName: string) => void;
  onClose: () => void;
}) {
  const named = subdecks.filter((s) => s.name);
  return (
    <Modal title="Subdecks" onClose={onClose}>
      {named.length === 0 ? (
        <p className="muted">
          No subdecks yet. Set a card's subdeck (e.g. “Ch01 - The Market”) to group it.
        </p>
      ) : (
        <ul className="subdeck-manage">
          {named.map((s) => (
            <SubdeckRow key={s.name} subdeck={s} onRename={onRename} />
          ))}
        </ul>
      )}
      <p className="zone-hint">
        Cards land in Anki as <code>deck::subdeck</code>. Renaming updates every card in that
        subdeck.
      </p>
    </Modal>
  );
}

function SubdeckRow({
  subdeck,
  onRename,
}: {
  subdeck: Subdeck;
  onRename: (oldName: string, newName: string) => void;
}) {
  const [name, setName] = useState(subdeck.name);
  return (
    <li>
      <input value={name} onChange={(e) => setName(e.target.value)} />
      <span className="muted">
        {subdeck.count} card{subdeck.count === 1 ? "" : "s"}
      </span>
      <button
        disabled={!name.trim() || name === subdeck.name}
        onClick={() => onRename(subdeck.name, name.trim())}
      >
        Rename
      </button>
    </li>
  );
}
