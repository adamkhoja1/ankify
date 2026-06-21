# Implementable rubric

The concrete rubric used by `rubric.py` (self-review + eval judge). It merges our
14-criterion synthesis (`docs/RESEARCH.md` §2) with the Memory Machines tier scale and
five probes (§1). Two layers: **probes** (binary, fast, target the T1 failure mode) and a
**tier** (T0–T3, holistic, grounded against reference cards when available).

Attribution: the probe and tier definitions are adapted from the Apache-2.0
`laddermedia/memory-machines` instruction prompts (Kirkby & Matuschak, 2026). See `NOTICE`.

## Foundational criteria

Every card must satisfy both:

- **Meaningful** — captures something worth remembering long-term, not a triviality.
- **Stable / reliably recallable** — retrievable months later, reviewed in isolation,
  without the source.

Stringency falls on the **question** (it cues recall); the **answer** may elaborate.

## Probes (binary failure modes → JSON `{reason, failed}`)

| Probe | Fails when… | Maps to criteria |
|-------|-------------|------------------|
| `lacks_context` | the question can't be answered in isolation — "which article? according to whom?"; unresolved "this/that/the system"; non-standard metaphor without attribution | 4 context-free |
| `multiple_responses` | admits several valid answers — subjective qualifiers (primary/main/key/fundamental), indefinite "a/an", open "why is X important", overly broad scope, vague "how". Specific attribution/enumeration rescues breadth | 1 atomicity, 2 single answer, 3 precision |
| `shallow` | tests surface trivia (counts, names) over the insight, or the answer under-delivers. **Not** shallow when the specific number/fact *is* the insight | 8 understanding, 9 depth, 14 worth-memorizing |
| `wordy` | needless qualifiers, passive/indirect phrasing, fancy vocab, redundant padding. Necessary technical terms are **not** wordiness | 13 conciseness |
| `narrow` | targets the wrong aspect — metaphor mechanics over the principle, example trivia over the lesson, stripped platitude over its specific application | 12 salience, partial 10 connection |

Also enforced at generation/parse time, not as LLM probes:

- **binary/yes-no** (criterion 6) — reject yes/no questions structurally.
- **source faithfulness** (criterion 5) — the grounded judge and self-review flag answers
  unsupported by the source; a dedicated check compares answer claims to the source.

## Tier (T0–T3, holistic)

- **T3 Ready** — specific, unambiguous, consistent retrieval; meaningful answer. Use as-is.
- **T2 Needs polish** — sound; minor word-level tweaks only.
- **T1 Needs refactor** — right region but ineffective: vague/ambiguous, weak cues, or
  shallow. Structural fix needed. (The dominant real-world failure.)
- **T0 Off-target** — tests the wrong information (macro or micro misalignment).

**Usable = T2 or T3.** Grounded judging compares the card against reference cards for the
same source (precedents); ungrounded judging falls back to the definitions above.

## How the layers combine

- **Self-review** (generation time): run the probes; any probe failure or T0/T1 tier →
  refine (preferred) or drop. Iterate up to N rounds. Surface only T2/T3, probe-clean cards.
- **Eval** (offline): tier every generated card (grounded against the reference deck) and
  run probes; report % usable, tier distribution, per-probe failure rates, vs. the reference
  deck judged identically. Calibrate against Memory Machines human tier labels.

## Scoring object

`Verdict{ tier: T0|T1|T2|T3, probes: [{probe, failed, reason}], reason }`,
with `usable = tier in {T2, T3}`.
