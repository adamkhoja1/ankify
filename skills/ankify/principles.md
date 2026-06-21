# Flashcard writing principles

Quick reference for the ankify skill. Deeper material in `card_writing_advice/`; the full
gradable rubric (probes + tiers) is in `../../docs/RUBRIC.md`.

## Two things every card must be

- **Meaningful** — captures something worth remembering long-term, not a triviality.
- **Stable** — reliably recallable months later, reviewed in isolation, without the source.

Apply stringency to the **question** (it cues recall). The **answer** may add brief context.

## Hard requirements

1. **Atomic** — one retrieval target. Split bundled facts into separate cards.
2. **Single unambiguous answer** — no sets/lists; no subjective qualifiers (primary/main/key);
   no indefinite "a/an"; no open "why is X important". Attribution or enumeration rescues
   breadth ("the four conditions Jacobs lists", "according to Kahneman").
3. **Self-contained** — resolve "this/that/the system"; name the source when the answer
   depends on a specific framing. Prefer source-anchored wording over generic paraphrase.
4. **Not yes/no** — demand generative recall, not a 50% guess.
5. **Faithful** — the answer is supported by the source; never invent details.

## Quality signals

- **Tests understanding**, not the surface shape of the question.
- **Captures the why/how** when the source explains a mechanism (not just a label).
- **Concise** — no padding; necessary technical terms are fine.
- **Connected / worth memorizing** — relates to broader knowledge; skip throwaway trivia and
  instantly re-derivable facts (Nielsen's "10-minute rule").

## Card types

- **Basic Q&A** — the default; best for understanding and "why/how".
- **Cloze** — Anki `{{c1::...}}` deletion; use when a fill-in-the-blank on a specific
  term/phrase is genuinely the cleaner test (don't overuse for concepts).
- **Reversible** — a pair (imported as two notes) only for true bidirectional associations
  (term ↔ definition, symbol ↔ meaning).

## Practical

- Prefer fewer, better cards. 10 precise cards beat 50 vague ones.
- When two things are confusable, make an explicit contrast card.
- Add source/date annotations as tags, not in the testable content, for volatile facts.
