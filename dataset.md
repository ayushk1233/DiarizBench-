# Production dataset and annotation convention (T05)

Status: **design proposal** (the "proposed production benchmark" scope). This is a specification for the 60-hour collection and its reference-quality process — it is **not** the pilot corpus. The pilot uses 24 pre-existing recordings (T06) with their native references. Nothing here is presented as collected data.

Source of truth: `plan.md §2 (Design the production dataset)`.

---

## 1. Composition: 60 hours, two splits

| Split | Duration | Purpose | Source policy |
|---|---|---:|---|
| **Public development** | **12 h** | Model setup, threshold/fairness tuning, reproducible baselines. Shareable. | Licensed public material. |
| **Private evaluation** | **48 h** | Held-out scoring. Never used during development. | Newly collected, consented conversations. |

The 4:1 eval:dev ratio keeps a large held-out set while leaving enough public audio that anyone can reproduce the development setup. Dev is shared with participants; eval is released only as audio + references after the evaluation window closes.

---

## 2. Domain × language grid

Four equally represented domains, equal English/Indic duration within each.

| Domain | Total | English | Indic | Characteristic conditions |
|---|---|---:|---:|---|
| **Meetings** | 15 h | 7.5 h | 7.5 h | Multi-speaker, table-top, distant + close mics, agenda-driven turns. |
| **Telephone** | 15 h | 7.5 h | 7.5 h | 2-party PSTN/VoIP, band-limited 8 kHz, codec artifacts, call-center style. |
| **Interviews / media** | 15 h | 7.5 h | 7.5 h | 1–3 speakers, studio or field mics, host + guest, occasional crosstalk. |
| **Informal conversation** | 15 h | 7.5 h | 7.5 h | Free-flowing, overlap-heavy, laughter, casual turn-taking, background noise. |
| **Total** | **60 h** | **30 h** | **30 h** | |

**Dev split of the same grid:** 3 h per domain (1.5 h English + 1.5 h Indic). **Eval split:** 12 h per domain (6 h English + 6 h Indic).

---

## 3. Indic language coverage

Six languages, balanced across the overall collection:

| Language | Total | Dev | Eval |
|---|---:|---:|---:|
| Hindi | 5 h | 1 h | 4 h |
| Bengali | 5 h | 1 h | 4 h |
| Marathi | 5 h | 1 h | 4 h |
| Tamil | 5 h | 1 h | 4 h |
| Telugu | 5 h | 1 h | 4 h |
| Kannada | 5 h | 1 h | 4 h |
| **Indic total** | **30 h** | **6 h** | **24 h** |

Within a domain the 7.5 h of Indic is spread across the six languages **as domain availability permits** (e.g. telephone conversations skew to whatever languages callers actually speak), subject to the global constraint that each language totals 5 h. Code-mixed conversations (English↔Indic, and Indic↔Indic) are collected deliberately and **tagged as code-mixed** so they can be analyzed as their own slice rather than misassigned to one language.

---

## 4. Metadata recorded per recording

Every recording carries a structured metadata record so that slicing in the leaderboard (T13) is data-driven, not guessed:

| Field | What is recorded |
|---|---|
| **Speaker count** | Reference number of speakers (and whether it is stable or speakers enter/leave). |
| **Overlap ratio** | Fraction of total speech time where ≥2 speakers are simultaneously active. |
| **Turn lengths** | Per-speaker turn-length distribution (count, mean, median, p95). |
| **Microphone conditions** | Close-talk / distant / array / telephone (8 kHz); per-channel note. |
| **Noise** | Broad SNR band (e.g. <10 dB, 10–20 dB, >20 dB) plus a short descriptor. |
| **Accents** | Per-speaker accent/region tag (self-declared, consent permitting). |
| **Code-mixing** | Fraction of turns that mix languages, plus the language pairs involved. |

---

## 5. Crowded and low-participation quotas

- **Crowded quota:** at least **25% of evaluation recordings (by count) and 25% of evaluation audio duration** must come from sessions with **5 or more speakers**. This is what keeps the low-activity-speaker diagnostic (metrics.md §2) and the "Beyond DER" finding measurable — a benchmark with only 2–4-speaker files can silently ignore speaker-coverage failures.
- **Low-participation speakers are separately identified:** any reference speaker contributing ≤5% of their recording's speaker-time (matching the diagnostic threshold) is flagged in metadata, so the diagnostic can be computed without a post-hoc hunt.
- These quotas are **collection targets**, stated up front; any shortfall is published, not hidden (same honesty rule as the pilot's coverage targets in T06).

---

## 6. Split-integrity rules

- **Split by source conversation and speaker group:** all audio of one conversation, and all recordings of one speaker group, stay in a single split. No speaker's voice appears in both dev and eval — this prevents speaker-identity leakage across the split.
- **Alternate microphones kept together:** near-field and far-field recordings of the *same* session are assigned to the same split (usually eval), so a system is never tuned on one mic of a meeting and scored on another.
- **Consent linkage:** a speaker who withdraws consent removes all of their audio from both splits at once.

---

## 7. Source material policy

- **Development (12 h):** licensed public material (e.g. permissively licensed corpora), redistributable with the benchmark so third parties can reproduce setup.
- **Evaluation (48 h):** newly collected, consented conversations. Consent covers audio use, accent/language metadata, and the no-reidentification commitment. No public figure audio, no broadcast scraping, no third-party data without explicit license.

---

## 8. Acoustic annotation convention

One written convention applies to the whole production collection (this is what makes cross-domain pooling legitimate — the Anuvani finding is that *differing* conventions move DER by several points):

| Rule | Meaning |
|---|---|
| **Pauses excluded** | Silence is not part of any speaker's segment. A pause ends a speaker's segment; speech after it starts a new one. (No long within-speaker gaps collapsed into "one turn".) |
| **Overlap labelled independently** | Each simultaneous speaker is labelled on their **own track**. Overlap is the union of two tracks, not a special "overlap" region that overwrites one speaker. |
| **Brief backchannels retained** | Short verbal responses — "mm-hmm", "yeah", "right" — are labelled to the speaker who produced them, **not** merged into the main speaker. This is what keeps low-activity speakers measurable. |
| **Non-speech vocalizations documented separately** | Laughter, coughing, singing, crying are labelled on a separate non-speech track. They are **not** counted as speech for DER, but their positions are recorded so overlap and noise analyses can account for them. |
| **Speech definition** | Intentional verbal communication, including filled pauses ("uh", "um") and backchannels. Excludes pure laughter and other non-speech vocalizations. |

Boundary granularity target: **±50 ms** after adjudication (measured against a fixed manual pass), so the zero-collar headline (metrics.md §3) is not dominated by label-placement noise.

---

## 9. Annotation quality process

**Two independent annotators → adjudication → written handbook**, matching `plan.md §2`:

1. **Independent pass:** two annotators label each recording from scratch against the §8 convention, using the written handbook.
2. **Agreement measurement (before adjudication):** agreement is reported explicitly and is *never* improved by adjudication and then presented as raw agreement. Reported as:
   - **Inter-annotator DER** — annotator B scored against annotator A as reference, zero collar, overlap included (the same scoring as the benchmark).
   - **Speaker-count agreement** — fraction of recordings where both annotators agree on the number of speakers.
   - **Boundary agreement** — median absolute boundary offset after optimal one-to-one mapping.
3. **Adjudication:** a third, senior annotator resolves all disagreements. Disagreements on **boundaries, overlap, speaker identity, and speaker count** are the explicitly-tracked categories.
4. **Acceptance checks:** an adjudicated file is accepted only when it passes the boundary (≤±50 ms), overlap, speaker-identity, and speaker-count checks in the handbook.
5. **Reporting:** both pre-adjudication agreement *and* the adjudicated reference quality are reported alongside results. The benchmark publishes the agreement it actually achieved; it does not claim a perfect reference.

---

## 10. Relationship to the pilot

The pilot (T06–T11) deliberately uses **pre-existing corpora with their native references**, so it cannot adopt this unified convention end-to-end. That limitation is why:
- pilot scores are reported **per corpus first**, and cross-corpus aggregates are labelled exploratory (metrics.md §5);
- the completed pilot annotation audit (T10) inspects six references structurally; it does not re-label audio or measure a convention-induced score difference. A listening-based re-annotation study remains future work.

The §1–§9 specification is the **proposed production benchmark**; it is what T12's main document presents as the "designed, not yet built" deliverable.
