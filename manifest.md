# Pilot manifest — 24 recordings (T06)

The frozen list of exactly what audio gets scored, fixed **before any prediction is inspected**. Selection is deterministic and reproducible from the sources; every identifier below was verified live against Hugging Face / the upstream corpora on **2026-11-10**.

Source of truth: `plan.md §4 (Recordings)`. Scoring follows `metrics.md` (zero collar, overlap scored, unknown speaker count).

---

## 1. Selection rules (deterministic)

1. **Indic DiarBench (12)** — 2 samples per language (Hindi, Bengali, Marathi, Tamil, Telugu, Kannada). Per language: pick the **highest-speaker-count near-field sample** from one meeting, and the **highest-speaker-count in-the-wild sample** from a *different* recording — so the two are independent speaker groups. Samples are the dataset's `sample_id` unit; `recording_id` groups them into meetings.
2. **AMI (6)** — single distant microphone (`SDM`) condition, `only_words` references. Four meetings from the canonical test partition (EN2002, ES2004, IS1009, TS3003) + two validation meetings (ES2011, IS1008) to reach six *distinct speaker groups* (avoids pseudo-replicating a/b/c/d chunks of one meeting). Each `a` chunk is already ≈5 min.
3. **VoxConverse (6)** — dev split, files with **≥5 reference speakers**, chosen from the top of the speaker-count ranking to include one very crowded case.

**Excerpt rule:** every file is truncated to its **first 300 s** (deterministic); scoring regions are that window, and references are clipped to it. Files already ≤300 s use their whole length.

---

## 2. The manifest

### Indic DiarBench (`sarvamai/indic-diarbench`, test split, CC BY 4.0)

Reference = `annotated_transcript` (speaker_id / start / end) → RTTM. `nspk`/`dur` are the dataset's own `num_speakers` / `duration_seconds`.

| ID | Language | Condition | recording_id | sample_id | Ref spk | Dur (s) | Scoring region (s) |
|---|---|---|---|---|---|---|---|
| HI-01 | Hindi | Near field | `hindi_nf_001` | `hindi_018` | 9 | 196.6 | 0–196.6 |
| HI-02 | Hindi | In the wild | `hindi_itw_004` | `hindi_036` | 5 | 310.0 | 0–300.0 |
| BN-01 | Bengali | Near field | `bengali_nf_001` | `bengali_030` | 8 | 206.4 | 0–206.4 |
| BN-02 | Bengali | In the wild | `bengali_itw_008` | `bengali_040` | 6 | 305.0 | 0–300.0 |
| MR-01 | Marathi | Near field | `marathi_nf_002` | `marathi_024` | 6 | 178.3 | 0–178.3 |
| MR-02 | Marathi | In the wild | `marathi_itw_008` | `marathi_038` | 5 | 397.4 | 0–300.0 |
| TA-01 | Tamil | Near field | `tamil_nf_001` | `tamil_010` | 5 | 144.5 | 0–144.5 |
| TA-02 | Tamil | In the wild | `tamil_itw_018` | `tamil_049` | 6 | 1422.0 | 0–300.0 |
| TE-01 | Telugu | Near field | `telugu_nf_001` | `telugu_011` | 8 | 192.4 | 0–192.4 |
| TE-02 | Telugu | In the wild | `telugu_itw_004` | `telugu_030` | 8 | 600.1 | 0–300.0 |
| KN-01 | Kannada | Near field | `kannada_nf_001` | `kannada_025` | 7 | 196.1 | 0–196.1 |
| KN-02 | Kannada | In the wild | `kannada_itw_012` | `kannada_039` | 8 | 335.0 | 0–300.0 |

### AMI (single distant mic, `only_words` references)

Reference = BUTSpeechFIT `AMI-diarization-setup` `only_words` RTTM (manual annotations v1.6.2). SDM audio, 16 kHz.

| ID | Meeting | Partition | Ref spk (typ.) | Scoring region |
|---|---|---|---|---|
| AMI-01 | `ES2004a` | test | 4 | whole chunk (per `uems/test/ES2004a.uem`) |
| AMI-02 | `EN2002a` | test | 4 | whole chunk |
| AMI-03 | `IS1009a` | test | 4 | whole chunk |
| AMI-04 | `TS3003a` | test | 4 | whole chunk |
| AMI-05 | `ES2011a` | validation | 4 | whole chunk |
| AMI-06 | `IS1008a` | validation | 4 | whole chunk |

### VoxConverse (dev split, CC BY 4.0)

Reference = official `dev/<id>.rttm`. Audio = `dev/wav/<id>.wav`.

| ID | File | Ref spk | Scoring region |
|---|---|---|---|
| VC-01 | `cjfer` | 15 | 0–300 s (excerpt) |
| VC-02 | `fkvvo` | 9 | 0–300 s (excerpt) |
| VC-03 | `aisvi` | 8 | 0–300 s (excerpt) |
| VC-04 | `eziem` | 8 | 0–300 s (excerpt) |
| VC-05 | `bdopb` | 7 | 0–300 s (excerpt) |
| VC-06 | `eapdk` | 7 | 0–300 s (excerpt) |

---

## 3. Coverage targets (checked against the manifest)

| Target | Required | This manifest |
|---|---|---:|
| Crowded excerpts (≥5 reference speakers) | ≥6 | **18** (all 12 Indic + all 6 VoxConverse; AMI is 4-spk) |
| Substantial-overlap excerpts | ≥6 | Expected met — verified against references at T08. Indic DiarBench reports avg **12.8% overlap**; VoxConverse is overlap-selected; AMI meetings contain crosstalk. Any unmet target is published. |
| Distinct source conversations (for bootstrap independence) | 24 | **24** distinct speaker groups (2 per Indic language, 6 AMI meetings, 6 VoxConverse files). |

---

## 4. Predefined 12-recording fallback subset

If data access, GPU budget, or a model failure forces reduction (per `plan.md §4 (Time limits and fallback)`), the balanced fallback is fixed now:

| Corpus | Recordings |
|---|---|
| Indic (6, one per language) | `hindi_018`, `bengali_030`, `marathi_024`, `tamil_010`, `telugu_011`, `kannada_025` (all near-field, crowded) |
| AMI (3) | `ES2004a`, `EN2002a`, `IS1009a` |
| VoxConverse (3) | `cjfer`, `fkvvo`, `aisvi` |

This subset is balanced across corpus, language, and architecture-relevant conditions, and is declared **before** any result is seen.

---

## 5. Per-recording fields carried into the harness (T07/T08)

Each manifest row expands to: **source · split · timestamps/excerpt window · language · condition · reference (native, format noted) · scoring region (UEM) · audio checksum**. The checksum (SHA-256 of the decoded 16 kHz mono WAV) is computed at download time in T08 and written back into this manifest — it cannot be computed before the audio is fetched. Reference sources and exposure flags:

| Corpus | Reference provenance | Training-exposure flag |
|---|---|---|
| Indic DiarBench | dataset `annotated_transcript` → RTTM | Anuvani = **known overlap** (its own benchmark); community-1 / Nemotron = **unknown** |
| AMI | BUTSpeechFIT `only_words` RTTM | community-1 = **known overlap** (model card reports AMI-SDM); Nemotron / Anuvani = **unknown** |
| VoxConverse | official `dev/*.rttm` | community-1 = **known overlap** (model card reports VoxConverse); Nemotron / Anuvani = **unknown** |

Exposure is recorded per `metrics.md §4` and never used to alter scores.

---

## 6. Reproducibility

- The full Indic metadata (all 6 languages, 562 samples) is saved at `scripts/indic_metadata.json`; extraction is `scripts/extract_corpus_metadata*.py` (venv: `.venv-meta`, `pyarrow` + `fsspec`, range-reads only metadata columns).
- VoxConverse dev speaker counts were computed from the official `dev/*.rttm` files (216 files; 91 have ≥5 speakers).
- AMI meeting list verified against `BUTSpeechFIT/AMI-diarization-setup` (`lists/test.meetings.txt`, `only_words/rttms/test/*`).
