# Research: what makes a good spaced-repetition card, and how to evaluate generators

Consolidated findings backing the ankification rework. Three sources: a synthesized
card-quality rubric, the *Memory Machines* paper (the key prior art on LLM-generated
cards), and a scouted validation set. Everything here feeds the generator prompts,
the self-review pass, and the eval harness.

---

## 1. Memory Machines (the key prior art)

**Kirkby, O. & Matuschak, A. (2026). _Memory Machines: Can LLMs create lasting
flashcards from readers' highlights?_** Self-published, San Francisco. Not on arXiv.

- Report: https://memory-machines.com/report · Appendix: https://memory-machines.com/appendix
- Code (Apache-2.0): https://github.com/laddermedia/memory-machines
- Data (Apache-2.0):
  - https://huggingface.co/datasets/laddermedia/srs-prompts — 1,499 candidate prompts
    (1,300 train / 204 test), one row per candidate. Columns: `highlight`,
    `highlight_interpretation`, `content` (the Q&A), `source_url`, `source_meta`,
    `pluckable` (bool), `tags` (failure-mode labels), `highlight_id`.
  - https://huggingface.co/datasets/laddermedia/srs-highlights — 475 highlights, each
    grouping its candidate prompts with **T0–T3 tier labels** and task-type labels.

### Findings that shape our design

- **Card quality is hard even for frontier models.** Best generator in their arena was
  only ~64% "usable"; ~36% of cards are unusable. The dominant failure is **T1**
  (structurally broken but plausible-looking), *not* hallucination.
- **Grounded judging beats ungrounded.** An LLM judge comparing a candidate against
  human reference prompts *from the same highlight* raised precision 56%→78%
  (human agreement κ≈0.61). **Our eval harness judges generated cards grounded against
  reference-deck cards for the same source.** Ungrounded judging is a weaker fallback.
- **Apply stringency to the _question_, not the answer.** The question cues recall;
  answers may carry auxiliary context/elaboration. (Verbatim principle from their
  `rate_grounded.txt`.)
- **Two foundational criteria** every card must meet: **Meaningful** (worth remembering
  long-term) and **Stable / reliably recallable** (retrievable months later, in isolation).

### The Memory Machines rubric (reusable judge prompts in the repo)

Four-tier scale (`memory_machines/tiering/instructions/rate_grounded.txt`):

- **T3 Ready to Review** — specific, unambiguous, consistently triggers the same
  retrieval; answer captures a meaningful detail. Usable as-is.
- **T2 Needs Polish** — sound targeting/construction; minor word-level tweaks would help.
- **T1 Needs Refactor** — right region of meaning but ineffective: too vague/ambiguous
  (multiple valid answers), insufficient cues, or lacking depth. Needs restructuring.
- **T0 Off-Target** — tests the wrong information (macro- or micro-misalignment), even if
  it's a well-formed card.

"Usable" = T2+T3. Five binary failure-mode **probes**
(`memory_machines/probes/instructions/*.txt`), the most directly reusable dimensions:

1. **Lacks Context (ambiguous)** — question not answerable in isolation. Test: if the
   question itself raises "which article? / according to whom?", it's ambiguous.
2. **Solicits Multiple Responses (non-atomic)** — admits several valid answers. Flags:
   "primary/main/key/fundamental", indefinite "a/an effective…", open "why is X important",
   broad scope, vague "how". Specific attribution/enumeration rescues breadth.
3. **Shallow** — tests surface facts (counts, names) over the insight, or the answer
   under-delivers. Nuance: sometimes specificity *is* the depth (a statistic that is itself
   the point is not shallow).
4. **Wordy** — needless qualifiers, passive constructions, fancy vocab, redundant phrasing.
   Necessary technical terms are *not* wordiness.
5. **Narrow** — wrong aspect: metaphor mechanics over the principle, example trivia over the
   lesson, stripped platitude over its specific application.

Generation prompts also live in the repo (`memory_machines/arena/instruction/*.txt`):
"test what was actually highlighted, not the full interpretation; one unified concept per
prompt; Q./A. format."

---

## 2. Synthesized card-quality rubric (14 criteria)

A gradable rubric for an LLM judge scoring a single card against its source. **Hard
disqualifiers** (a 0 gates the card) vs **soft quality signals** (0/1/2 gradients).
Maps onto the Memory Machines probes; the two are merged in `docs/RUBRIC.md` for the
implementation.

**Hard disqualifiers**
1. **Atomicity** — one retrieval target, not several bundled.
2. **Single unambiguous answer** — not a set/list/open-ended; exactly one correct answer.
3. **Answer precision / no vagueness** — the question pins down what's wanted.
4. **Context-free / self-contained** — stands alone; deictic refs ("this layer") resolved.
5. **Source faithfulness** — answer supported by the source; no hallucinated detail.
6. **Not a binary / yes-no prompt** — demands generative recall, not a 50% guess.

**Soft quality signals**
7. **Effortful but reliable** — desirable difficulty; answerable ~90% once learned.
8. **Tests understanding, not pattern-matching** — meaning/mechanism over surface form.
9. **Explanatory depth (why/how)** — captures the causal link when the source has one (N/A if not).
10. **Connection / non-orphan** — relates to adjacent ideas, not floating trivia.
11. **Elaborative / generative encoding** — invites reconstruction/application over recognition.
12. **Salience / transfer to use** — for applied knowledge, framed at the point of use (N/A otherwise).
13. **Conciseness / no bloat** — question and answer as short as unambiguity allows.
14. **Worth-memorizing (value filter)** — durable, reusable fact; Nielsen's "10-minute rule".

**Judge policy:** treat 9 and 12 as N/A (drop from denominator) when the source/goal
doesn't apply; don't double-penalize one defect that trips several correlated criteria
(e.g. a yes/no prompt is also un-effortful and pattern-matchable — score the dominant flaw).

**Sources:** Matuschak, *How to write good prompts* (https://andymatuschak.org/prompts/);
Nielsen, *Augmenting Long-Term Memory* (https://augmentingcognition.com/ltm.html);
Woźniak, *Twenty Rules* (SuperMemo); controlaltbackspace.org; Bjork & Bjork (desirable
difficulties); generation effect; encoding specificity.

---

## 3. Validation set (source → reference deck pairs)

Generated cards are judged **grounded** against an expert/community reference deck for the
same source. Ranked by how cleanly the pipeline can obtain them.

| # | Domain | Source | Reference deck | Type | Access |
|---|--------|--------|----------------|------|--------|
| MM | mixed (93 sources) | Memory Machines highlights | human T0–T3 labels + reference prompts | mixed | **best** — HF datasets, Apache-2.0, already labeled |
| 1 | quantum computing | Quantum Country *QCVC* (quantum.country/qcvc) | 112 expert embedded prompts | conceptual+technical | readable free; prompts scraped from HTML; license unstated (private use) |
| 2 | learning methodology | "How to write good prompts" (andymatuschak.org/prompts) | essay's embedded prompts | conceptual | **CC BY-NC 4.0**; cleanest license |
| 3 | world geography | Ultimate Geography structured source (XLSX/CSV) | Ultimate Geography deck (~978 cards) | factual + recognition | **MIT repo**, source + deck together; flag/map cards are image-based |
| 4 | medicine (USMLE) | First Aid/Pathoma/etc. (copyrighted) | AnKing Step Deck (30k+) | factual+conceptual | gated (AnkiHub sub) + copyrighted source — stretch only |
| 5 | Japanese N5 | Tango N5 textbook (copyrighted) | JLPT Tango N5 deck | vocabulary | copyrighted; deck metadata unverified — low priority |

**Recommended core val set:** Memory Machines datasets (primary, labeled) + Quantum
Country + Ultimate Geography. Spans conceptual, technical, factual, and recognition with
clean-enough access. AnKing/Japanese only if licensed access is available.

**Not recommended / debunked:** "Executable Books" mnemonic corpus (does not exist — a
conflation); *Transformative Tools for Thought* essay (no embedded prompts, no gold deck).
