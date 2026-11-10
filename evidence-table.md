# Research evidence table

Maps every key source to the concrete design decision it justifies. Format per source: **Protocol** (what they did) → **Relevant finding** (what matters to us) → **Limitation** (what to be careful of) → **Decision it informs** (what we do because of it).

## Master summary

| Source | Decision it informs |
|---|---|
| Beyond DER (2026) | Require speaker-count metrics + a low-activity-speaker diagnostic alongside DER. |
| Indic DiarBench (2026) | Add Indic language and code-mixing slices; use speaker-attributed joint ASR/diarization view. |
| SDBench / OpenBench (2025) | Standardize inputs; always report measured speed with accuracy; make the pipeline reproducible. |
| DIHARD III (2020) | Lock the scoring contract before inference: scoring regions, zero collar, overlap scored, unknown speaker count. |
| Anuvani-Diarization (2026) | Document reference conventions and run a separate annotation-convention audit. |
| Benchmarking Diarization Models (2025) | Decompose errors (missed speech / false alarm / confusion) and analyze high-speaker-count recordings. |
| DISPLACE 2024 + eval plan | Distinguish speaker changes from language changes; copy their reproducible evaluation rules. |
| A Review of Speaker Diarization (Park et al., 2021) | Explain system families and technical foundations; justify metric choice. |

## Core sources

### 1. Beyond DER: Speaker Counting in Crowded End-to-End Diarization (2026)
- **Protocol:** Investigates end-to-end diarization on crowded conversations, comparing DER against explicit speaker-counting measures.
- **Relevant finding:** Duration-weighted DER can stay low while a system silently drops speakers who contribute little speech — under-counting and lost low-activity speakers are hidden.
- **Limitation:** The failure is a counting problem, not an accuracy problem, so DER alone is an incomplete headline.
- **Decision:** Headline accuracy must be accompanied by exact speaker-count accuracy, count MAE + signed bias, and a low-activity-speaker recall diagnostic (T04). The crowded / 5+-speaker slice is mandatory.

### 2. Indic DiarBench (Sarvam, 2026)
- **Protocol:** Joint diarization and speaker-attributed ASR benchmark across 22 Indian languages, including overlapping and code-mixed speech.
- **Relevant finding:** Multilingual conversational coverage — including code-switching — is what real Indian deployments need; it is also where English-centric systems diverge.
- **Limitation:** A single Indic slice can't be pooled into an English headline without hiding domain shift.
- **Decision:** Dedicated Indic language and code-mixing slices in the production set, and 12 Indic DiarBench recordings in the pilot (T06). Report Indic results as labelled cells, never silently pooled (T01).

### 3. SDBench (2025) / Argmax OpenBench
- **Protocol:** A reproducible benchmark suite comparing systems across 13+ datasets and reporting accuracy alongside processing speed.
- **Relevant finding:** Fair comparison requires standardized inputs and a fixed evaluation procedure; accuracy and speed are both first-class outputs.
- **Limitation:** Speed numbers are only meaningful when the timed workload is stated exactly and hardware is fixed.
- **Decision:** One canonical input (16 kHz mono + scoring regions) per recording; report RTF with accuracy; state exactly what timed execution includes and fix the hardware (T04, T09).

### 4. The Third DIHARD Diarization Challenge (Ryant et al., 2020)
- **Protocol:** Multi-domain challenge with a documented evaluation plan: scoring regions, collar, overlap handling, and DER/JER definitions.
- **Relevant finding:** Strict scoring — no forgiveness collar, overlapping speech scored, number of speakers unknown — is the honest default for hard real-world audio.
- **Limitation:** Strict scoring penalizes boundary jitter; a single collar choice can flatter or punish systems.
- **Decision:** Lock the scoring contract before inference: zero collar, overlap included, unknown speaker count for the headline, with a 250 ms collar sensitivity result alongside (T04).

### 5. Anuvani-Diarization (CIIL, 2026)
- **Protocol:** Zero-shot evaluation of diarization across all 22 Indic languages, explicitly measuring how annotation conventions affect DER.
- **Relevant finding:** The benchmark's utterance-level convention is a hidden variable worth **1.9–4.1 percentage points of DER**, and a convention learned from other transcriptions does not transfer.
- **Limitation:** Scores from different corpora with different conventions are not directly comparable.
- **Decision:** Document reference conventions explicitly; run a separate annotation-convention audit on six excerpts and report diagnostic corrections separately (T10). Never aggregate across corpora with different conventions (T06).

### 6. Benchmarking Diarization Models (2025)
- **Protocol:** Cross-dataset evaluation of five diarization models across multilingual data, analyzing speaker confusion, missed speech, and robustness.
- **Relevant finding:** Aggregate DER hides *where* systems fail; decomposing into missed speech, false alarms, and speaker confusion reveals it.
- **Limitation:** Component analysis requires care that components are defined consistently across scoring tools.
- **Decision:** Report DER components (missed speech / false alarm / speaker confusion) and analyze high-speaker-count recordings specifically (T11). Cross-check component scoring between dscore and pyannote.metrics (T07).

### 7. The Second DISPLACE Challenge (2024) + evaluation plan
- **Protocol:** Multilingual Indian challenge evaluating speaker diarization *and* language diarization in natural conversations, with a public evaluation plan.
- **Relevant finding:** In code-switched conversations, "who spoke" and "which language" are entangled; a reproducible challenge needs explicit rules for both.
- **Limitation:** Confusing speaker changes with language changes inflates or hides errors.
- **Decision:** Distinguish speaker changes from language changes in the analysis; adopt their explicit, pre-published evaluation-plan approach for our production protocol (T04, T05).

### 8. A Review of Speaker Diarization (Park et al., 2021)
- **Protocol:** Survey of diarization methods, datasets, and metrics.
- **Relevant finding:** Establishes the standard metric family (DER/JER), the modular vs end-to-end taxonomy, and the canonical failure modes (overlap, short turns, noise).
- **Limitation:** A survey, so it gives vocabulary and context rather than a scoring recipe.
- **Decision:** Use it to explain system families (modular vs end-to-end) and to justify DER + JER as the accuracy backbone (T12).

## Secondary references (inform but are not core)

| Source | Informs |
|---|---|
| IndicVoices (2024) | Representative data collection and annotation quality across Indian languages → production data plan (T05). |
| CHiME-8 DASR (2024) | Evaluation across rooms/devices/conversation types → device and acoustic-condition slices (T05). |
| Streaming Sortformer (2025) | Streaming diarization and speaker tracking → offline/streaming separation and RTF reporting (T04, T09). |
| Powerset cross-entropy loss (2023); Overlap-aware resegmentation (2020) | Overlap handling → overlap-only DER and overlap slices (T04, T10). |
| End-to-end neural diarization with self-attention (2019) | End-to-end architecture family → system-families explanation (T12). |

## Consolidated research → decision mapping

1. **Beyond DER** → speaker-count + low-activity-speaker metrics are mandatory, not optional.
2. **Indic DiarBench** → Indic/code-mixing slices are a first-class part of the benchmark.
3. **SDBench / OpenBench** → reproducibility + accuracy-with-speed as a non-negotiable standard.
4. **DIHARD III** → strict scoring contract locked before any inference.
5. **Anuvani** → annotation conventions audited, never silently assumed.
6. **Benchmarking Diarization Models** → error decomposition + crowded-recording analysis.
7. **DISPLACE** → speaker-vs-language distinction + pre-published evaluation rules.
8. **Park et al. review** → technical vocabulary and system-families framing.

**Reading order used:** SDBench → Benchmarking Diarization Models → DIHARD III → Indic DiarBench → Anuvani-Diarization → DISPLACE 2024 → Beyond DER.

**ref:** `plan.md §2`, `decisions.md` T01.
