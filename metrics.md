# Metric contract and fairness rules (T04 — LOCKED)

This file freezes scoring, scoring settings, and comparison rules **before any inference runs**. T07 (scoring harness) and T09/T11 (runs, statistics, figures) implement exactly what is written here. Nothing is scored unless it follows this contract.

Source of truth: `plan.md §3`. This file is authoritative; where `plan.md` and this file disagree, this file wins (it resolves the low-activity diagnostic and the timing rule into precise, executable form).

---

## 1. Metric table

| Metric | Role | Formula / definition |
|---|---|---|
| **DER** | **Primary accuracy metric.** Fraction of reference speaker-time lost to missed speech, false-alarm speech, and speaker confusion. | `(missed + false alarm + confusion) / total reference speaker-time`, summed over scoring regions. |
| **JER** | Mandatory companion. Gives each reference speaker equal weight, so a dropped quiet speaker hurts as much as a dropped loud one. | Average, over reference speakers, of each speaker's own DER (one-vs-all). |
| **Exact speaker-count accuracy** | Fraction of recordings whose predicted speaker count equals the reference count. | `# correct counts / # recordings`. |
| **Speaker-count MAE** | Magnitude of counting errors (how many speakers off, on average). | `mean(|predicted − reference|)`. |
| **Speaker-count signed bias** | Direction of counting errors (does the system under- or over-count?). | `mean(predicted − reference)`. |
| **Low-activity-speaker recall** | Proposed diagnostic: how often the people who speak little are preserved. See §2. | Recovered low-activity speakers / total low-activity speakers. |
| **Overlap-only DER** | DER restricted to reference time where ≥2 speakers talk simultaneously. | DER computed over overlap reference time only. |
| **DER components** | Decomposition that explains *where* errors occur. | Missed-speech %, false-alarm %, confusion %, each as a share of total reference time (they sum to DER). |
| **RTF (real-time factor)** | Processing time per unit of audio; the honest speed number. | `processing_time / audio_duration` (lower is better). |
| **Speed factor** | Reciprocal convenience metric for display. | `1 / RTF` (audio seconds processed per wall-clock second). |

**Reporting units:** DER/JER/overlap-DER and the three DER components in percent (one decimal). Count accuracy and low-activity recall in percent. MAE/bias in speakers (one decimal). RTF as a decimal (two decimals); speed factor in "×".

**A metric is published only with its uncertainty.** DER/JER intervals come from the paired bootstrap (§6). Count metrics and low-activity recall are proportions over independent recordings and get Wilson or bootstrap intervals as appropriate.

---

## 2. Low-activity-speaker diagnostic (proposed, ours)

DER is duration-weighted, so a speaker who says 3 seconds in a 5-minute meeting can be dropped entirely and move DER by under a point. This diagnostic exists to catch exactly that (the "Beyond DER" finding).

**Definition of a low-activity speaker:**
1. Contributes **at most 5% of the reference speaker-time** in their recording, **and**
2. Speaks for **at least 0.5 s** (below this, the speaker is annotation noise, not a diagnosable speaker).

**Recovery rule:** after the one-to-one reference↔hypothesis speaker matching that maximizes total intersection (the standard `dscore`/`pyannote.metrics` optimal mapping), a low-activity reference speaker is **recovered** if **at least 50% of their reference speech time overlaps their matched hypothesis speaker's time**.

**Low-activity-speaker recall** = `# recovered low-activity speakers / # total low-activity speakers`, over the recordings where the diagnostic applies.

**Threshold-sensitivity check (mandatory when published):** re-run the diagnostic at `{3%, 5%, 10%}` activity thresholds and `{0.4s, 0.5s, 0.75s}` minimum-duration thresholds, holding the 50% recovery threshold fixed. Report the recall curve, not a single number, and state that the 5%/0.5s/50% defaults are our headline. This is labelled **our proposed diagnostic** — not an established community metric — throughout the submission.

---

## 3. Scoring settings (frozen)

| Setting | Value | Rationale |
|---|---|---|
| **Collar** | **0 ms (zero collar)** for the headline | Strict scoring; matches DIHARD III's no-forgiveness stance. |
| **Collar sensitivity** | A separate **250 ms** collar result alongside | Standard community setting; shows how much the headline is collar-dependent. |
| **Overlap** | **Included** (overlap scored) | Ignoring overlap inflates scores and hides a real failure mode. |
| **Speaker count** | **Unknown** to every system | No `num_speakers` hints; the system must estimate the count itself. |
| **Scoring regions** | Explicit per-recording regions (see T06 manifest) | Prevents scoring silence/lead-in that conventions disagree on. |
| **Speaker-count source** | Labels with **positive activity inside scoring regions** | A label that only speaks outside scoring regions is not a speaker for this recording. |
| **Output mode** | **Overlap-capable** output preserved (e.g. pyannote **regular** diarization, not its "exclusive" mode) | The exclusive mode would have been tuned to a different task; we score the system as users get it. |

The headline accuracy number is therefore **DER, zero collar, overlap scored, unknown speaker count**; every other number is a companion or a sensitivity result, never a substitute.

---

## 4. Fairness rules (frozen)

1. **Identical input:** every system receives the **same 16 kHz mono** waveform and the **same scoring regions**.
2. **No leakage:** no system receives reference transcripts, speaker identities, or true speaker counts (nor any derived hint).
3. **Frozen defaults:** documented default inference settings are frozen before evaluation; all setup/tuning happens on **separate development recordings**, never on pilot scoring audio.
4. **No reference-driven correction:** no gap-filling, no system-specific annotation repair, no post-hoc speaker re-labelling against the reference.
5. **Exposure disclosure:** each system's training-data exposure to the pilot corpora is recorded as **known overlap**, **declared disjoint**, or **unknown** (e.g. community-1 was trained on VoxConverse/AMI — declared overlap on those slices; unknown otherwise).
6. **Offline / streaming separated:** offline and streaming results never appear in the same ranking. Native streaming latency requires its own live-input protocol, which is out of pilot scope.
7. **Failed / unsupported runs recorded explicitly:** a run that errors, times out, or is unsupported on a recording is recorded, not silently skipped. An incomplete system receives **coverage information** (e.g. "scored 21/24") and **no complete overall rank**.

### The timing rule (hard, non-negotiable)

> **Self-hosted models, cloud APIs, and on-device SDKs never share a single speed ranking.**

They measure different things: self-hosted RTF is compute-bound on our GPU; cloud API latency includes network round-trips and vendor-side scheduling; on-device runs on end-user hardware with no GPU. Mixing them produces a misleading "fastest" claim. Therefore:

- **Self-hosted pilots** (community-1, Nemotron, Anuvani) share **one RTF table** — same GPU, same warm-up protocol, model loading reported separately.
- **Cloud APIs and on-device SDKs** appear in the catalog with their own wall-clock or device timing, **in a separate view**, and are never merged into the self-hosted speed ranking.

---

## 5. Aggregation rules

- **Headline pooled DER:** average across the **eight domain × language-group cells** (4 domains × {English, Indic}) with **equal cell weights** — so a heavily-represented cell cannot swamp the others.
- **Companion views:** conventional **globally pooled DER** (all reference time pooled) and **every per-cell result**, all published.
- **Corpus honesty:** pilot scores are reported per-corpus first (Indic DiarBench / AMI / VoxConverse each use their native reference conventions). Any **cross-corpus aggregate is labelled exploratory**, because annotation conventions differ across corpora (the Anuvani finding). The proposed production benchmark uses the single unified convention from T05.
- **Slices:** results are additionally filterable by language, speaker count, overlap, and operating mode (used by T13's leaderboard sketch).

---

## 6. Statistical rules (what makes a "win" real)

- **Paired bootstrap** over independent source conversations: **10,000 resamples**, **fixed seeds**, publish **95% intervals**.
- **Multiple comparisons:** pairwise winner claims (A beats B) are adjusted for the number of comparisons; a single unadjusted p-value never stands alone.
- **Practical significance:** a win requires **both** statistical evidence **and** a predeclared **≥1 percentage-point DER improvement**. A statistically significant sub-1-point gap is reported as "indistinguishable in practice", not as a winner.
- **Exploratory caveat:** pilot intervals — especially small language slices (2 recordings each) — are exploratory, and the caveat is stated wherever those intervals appear.

---

## 7. Validation of the contract itself (deferred to T07)

Before any real scoring, the harness must reproduce expected values on the fixture set from `plan.md §5` — perfect output, permuted labels, missing brief speaker, merged/split speakers, overlap, silence false alarms, empty hypotheses, invalid timestamps — and cross-check DER/JER against `dscore` and `pyannote.metrics` under the §3 settings. Any mismatch invalidates the harness, not the contract.
