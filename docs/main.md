[[space:58]]

Prepared by **Ayush Kumar**  ·  11 November 2026

Five working days  ·  free tools  ·  Kaggle T4 ×2  ·  experiment frozen before writing

This document designs a public diarization leaderboard for multilingual product teams and reports a
fully executed pilot on 24 recordings, three open systems, and 72 inference runs. It separates two
scopes throughout: the **proposed production benchmark** (a complete design) and the **measured
pilot** (what was actually run and scored). Every number in the pilot traces to a saved artefact;
the provenance table is Appendix C.

[[space:6]]

[[kpi:24 recordings|7 languages|3 systems|72 runs|196 min speech]]

[[space:4]]

> **In this submission.** (1) This main report: design, measured pilot, analysis, and reflections.
> (2) A one-page summary for a decision-maker. (3) A leaderboard sketch with the overview table,
> model-detail view, and governance rules. (4) A two-minute video walkthrough. Code, manifest,
> environment pins, and all result files ship as reproducibility material.

[[space:8]]

**How to read this document.** The full argument is 14 sections plus three appendices. If you are
short on time, the table below is the shortest honest route to a decision.

[[widths:34,66]]
| If you want to… | Read |
|---|---|
| Get the result in two minutes | Executive summary, then the one-page summary |
| Judge whether the design is right | Sections 1–4: audience, metrics, test data, frozen contract |
| Judge whether the evidence supports it | Sections 6–8: execution, results, significance testing |
| See where it breaks | Sections 9–12: three failure analyses, annotation audit, threats to validity |
| See what I would change | Sections 13–14: production plan, then the four reflections |

[[toc]]

# Executive summary

A product team choosing a diarization engine is not asking "which model has the lowest DER". It is
asking whether the system knows **who spoke when**, whether it keeps the **quiet participant** who
says twelve seconds in a five-minute meeting, and whether it returns answers **fast enough and under
the conditions the product actually runs in**. This submission turns those three questions into a
leaderboard design, then tests the design by running it end to end.

**What was built.** A frozen scoring contract (zero collar, overlap scored, unknown speaker count),
a 24-recording manifest across three corpora and seven languages, a validated scoring harness
(25 tests, cross-checked against `dscore`), a checkpointed Kaggle pipeline, and a paired-bootstrap
analysis. Three open systems were run on all 24 recordings: **72/72 units completed with zero
errors**.

**What was measured** (equal-weight over the 24 recordings; DER zero collar, overlap scored):

| System | DER % (95% CI) | JER % (95% CI) | Exact count | Low-activity recall | RTF |
|---|---|---|---|---|---|
| `pyannote/speaker-diarization-community-1` | 20.4 [15.5, 25.3] | 38.6 [30.3, 47.2] | 38% | 45% | 0.072 |
| `nvidia/Nemotron-3-Diarization` (streaming) | 21.6 [15.7, 27.6] | 32.5 [23.4, 41.6] | **58%** | **61%** | 0.079 |
| `CIIL/Anuvani-Diarization` | **13.8 [10.0, 17.9]** | **29.9 [22.7, 37.4]** | 33% | 47% | **0.053** |

**The measured configuration result.** Anuvani has lower DER than both tested configurations by more than the predeclared
one-point practical threshold and with Bonferroni-corrected significance (+6.6 pp vs community-1,
+7.8 pp vs Nemotron). The DER difference between community-1 and Nemotron is **not resolved by this sample** (−1.2 pp,
95% CI [−4.2, +2.0]). The JER view is weaker still: it separates Anuvani from community-1 but not
from Nemotron (+2.7 pp, CI [−3.6, +9.0]). We report both and claim only what survives.

**What the headline hides.** All three systems under-count speakers (bias −0.58 to −1.17 speakers
per recording) and all three drop **39–55% of low-activity speakers** — people who speak at most 5%
of the meeting. On the hardest Telugu conversation, overlap-only DER is 82–100% for every system
while whole-file DER is 38–42%. Nemotron's error is 79% *missed speech* (88% on AMI), a pattern
consistent with conservative speech activation, but this pilot does not isolate its cause.

**The three design decisions that changed the answer.**

1. **Score strictly and say so.** Zero collar, overlap included, unknown speaker count. A 250 ms
   collar lowers every score by 2.8–3.6 pp without changing the ranking, so the strict number is
   defensible *and* the sensitivity is disclosed.
2. **Publish speaker coverage next to accuracy.** the community-1/Nemotron DER gap is unresolved;
   count accuracy differs by 20.8 pp and low-activity recall by 15.8 pp descriptively. A leaderboard that shows
   only DER would erase a product-relevant difference.
3. **Never pool corpora silently.** The three corpora label overlap at 0.1%, 4–20%, and 16–28% and
   time segments at 11–746 per file. Per-corpus cells come first; the cross-corpus average is
   labelled exploratory.

**The limitation that matters most.** Anuvani was fine-tuned on Indic DiarBench, one of the three
pilot corpora, so its Indic margin cannot be separated from training-data exposure. Its wins on AMI
and VoxConverse do not establish unseen-data generalisation: its DiariZen parent also lists these
corpora as training sources. Exact session overlap has not been audited. The Indic comparison is
in-domain, not unseen-language, generalisation. This is disclosed on every
score, not buried.



[[page]]

# 1. The product question

Diarization leaderboards usually rank systems by diarization error rate (DER) on a handful of
English meeting corpora. That ranking answers a research question. It does not answer the questions
a product team asks before committing engineering time, a vendor contract, or a privacy review.

We framed the leaderboard around three questions, and made each one a first-class output rather than
a footnote:

- **Accuracy — does it identify who spoke when?** DER against a fixed, strict scoring contract,
  with an interval rather than a point estimate.
- **Speaker coverage — does it preserve people who speak briefly?** Exact speaker-count accuracy,
  count bias, and a low-activity-speaker recall diagnostic, because duration-weighted DER is
  mathematically capable of staying low while a participant disappears.
- **Practicality — how fast, and under what conditions?** Real-time factor (RTF) on fixed hardware
  with the timed workload stated exactly, model-load time reported separately, and operating mode
  (offline vs streaming) treated as a filter rather than a footnote.

The leaderboard serves the following users and decisions:

[[widths:25,39,36]]
| User | Decision supported | Evidence to inspect |
|---|---|---|
| Meeting-product or ML lead | Which engine should power participant-attributed notes, and which needs a deeper trial? | DER/JER, brief-speaker coverage, overlap failures, and the audio inspector |
| Call-analytics buyer | Which service merits a vendor evaluation under telephone, language, privacy, and latency constraints? | Telephone/language cells, delivery mode, coverage, cost and workload disclosures; telephone testing is proposed, not present in this pilot |
| Multilingual voice-product builder | Does a general or Indic-adapted system suit the product's actual language mix? | Indic language/domain slices, code-mixing annotation limits, exposure and confidence intervals |
| Benchmark maintainer | Can this row be published, reproduced, compared, or re-scored after a correction? | Complete run evidence, protocol/reference versions, settings, failures and provenance |

The pilot supports shortlisting and diagnostic questions. It cannot replace a product-specific,
held-out trial, establish vendor privacy properties, or provide production cost/latency estimates.

> **What this document is not.** It is not a claim that three systems on 24 recordings settle the
> ranking of diarization. The pilot is deliberately small and deliberately strict about what it can
> support: it validates the *instrument*, demonstrates that the instrument changes conclusions, and
> publishes intervals wide enough to show how much is still unknown.

# 2. What the leaderboard measures, and why

## 2.1 Two scopes, kept separate

| Scope | What it contains | Status in this submission |
|---|---|---|
| **Proposed production benchmark** | Collection and annotation protocol, unified reference convention, eight domain × language cells, governance and re-scoring rules | Designed, not built |
| **Measured pilot** | 3 open systems × 24 recordings, frozen contract, scored and analysed | Executed end to end |

Nothing in the production design is presented as measured. Where a production rule could not be
implemented at pilot scale — the unified annotation convention, the eight-cell equal weighting,
live-streaming latency — the pilot says what it substituted and why.

## 2.2 Research that changed a decision

Each source below earned its place by changing something concrete in the design, not by being cited.

| Source | Finding that mattered | Decision it forced |
|---|---|---|
| Beyond DER (2026) | Duration-weighted DER hides dropped low-activity speakers | Mandatory count metrics + low-activity recall diagnostic |
| Indic DiarBench (2026) | Code-mixed, overlapping Indian conversation is where English-centric systems diverge | Dedicated Indic cells; 12 of 24 pilot recordings |
| SDBench / OpenBench (2025) | Accuracy without measured speed is not a product answer | RTF with a stated workload; fixed hardware; load reported separately |
| DIHARD III (2020) | Strict scoring (no collar, overlap scored, unknown count) is the honest default | Contract frozen before any inference |
| Anuvani-Diarization (2026) | Annotation conventions are worth 1.9–4.1 pp of DER | Convention audit; never pool corpora silently |
| Benchmarking Diarization Models (2025) | Aggregate DER hides *where* systems fail | Missed / false-alarm / confusion decomposition |
| DISPLACE 2024 | Speaker changes and language changes are entangled in code-switched speech | Language slices; speaker-vs-language separation named as a production requirement |
| Park et al. review (2021) | Modular vs end-to-end families fail differently | System-family column; both families represented in the pilot |

The single most consequential of these was DIHARD III. Freezing the contract before inference is
what makes the 250 ms sensitivity result meaningful: it is a *pre-declared* alternative, not a
post-hoc rescue of a number that looked bad.

## 2.3 Fairness rules (frozen before inference)

1. **Identical input.** Every system received the same 16 kHz mono waveform and the same scoring
   regions. No system received reference transcripts, identities, or a speaker-count hint.
2. **Frozen defaults.** Documented default inference settings, fixed before evaluation. No tuning
   on pilot audio.
3. **No reference-driven repair.** No gap filling, no speaker re-labelling against the reference,
   no system-specific post-processing beyond the model's own documented output format.
4. **Exposure disclosed.** Every score carries a training-data exposure flag: known overlap,
   declared disjoint, or unknown.
5. **Operating modes separated.** Offline and streaming results never share a ranking. This rule
   turned out to matter more than expected (Section 5.3).
6. **Failures recorded.** An errored or unsupported run is reported, never silently dropped; an
   incomplete system gets coverage information and no overall rank.



# 3. Test data

## 3.1 The 24 recordings

The manifest was frozen before any prediction was inspected. Each row carries source, split,
language, condition, scoring region, reference path, audio checksum, and per-system exposure.

[[widths:13,9,30,9,11,12,12,14]]
| Corpus | Recordings | Languages | Speakers per excerpt | Segments per file | Scored audio | Reference speaker-time | Overlap share |
|---|---|---|---|---|---|---|---|
| Indic DiarBench | 12 | Hindi, Bengali, Marathi, Tamil, Telugu, Kannada (2 each) | 3–9 | 23–163 | 144–300&nbsp;s | 54 min | 0.1–28.3% |
| AMI (SDM) | 6 | English | 4 | 169–746 | 839–2143&nbsp;s | 115 min | 3.9–20.5% |
| VoxConverse | 6 | English | 6–13 | 11–49 | 300 s | 27 min | 0.0–8.8% |

In total: **205 minutes of scored audio and 196 minutes of reference speaker-time** (speaker-time
exceeds wall-clock where speakers overlap). Coverage targets were set in advance and met:

- **Crowded conversations:** 17 of 24 excerpts contain five or more speakers inside the scoring
  region (18 by whole-recording counts). Target: at least 6.
- **Substantial overlap:** 15 of 24 excerpts have at least 5% overlap. Target: at least 6.
- **Language spread:** six Indian languages, two recordings each, one near-field and one in-the-wild.

The Indic in-the-wild files are the code-mixed ones: the corpus documents English code-mixing,
dialectal variation, and frequent overlap, and its transcripts interleave Indic script with
Roman-script English. That is the slice the leaderboard exists to expose.

## 3.2 Scoring regions and excerpt policy

AMI is scored as whole meetings (839–2143 s) because the reference is word-timed and truncating a
meeting changes the speaker set more than it saves compute. Indic in-the-wild and VoxConverse use
deterministic 300 s excerpts; Indic near-field files are shorter than 300 s and are used whole
(144–206 s). Audio is truncated to the scoring region **before** inference, so no system pays for or
sees audio outside the scored window.

Excerpts cost speakers. Tamil `TA-02` has six speakers across the full recording but three inside
the excerpt; Kannada `KN-02` drops 8 to 7; VoxConverse `VC-01` drops 15 to 13. All counts in this
document are **in-region** counts, per the frozen contract. An earlier draft used whole-recording
counts and was corrected; that correction alone moved community-1's count MAE from 1.54 to 1.17.

## 3.3 References and their conventions

The pilot uses each corpus's native reference rather than re-annotating: Indic DiarBench's
speaker-attributed transcripts converted to RTTM (12/12 validated against the dataset's own speaker
counts), AMI's official `only_words` RTTM, and VoxConverse's official `dev` RTTM. This is the honest
choice for a five-day pilot and the wrong choice for a production benchmark, because the three
conventions disagree (Section 10). The production design replaces them with one unified convention;
the pilot publishes per-corpus results first and labels every cross-corpus aggregate exploratory.

A conversion bug found at this stage is worth recording: in-the-wild samples label speakers as
`Speaker A` and `New speaker A`. Spaces in the speaker field silently collapsed eight speakers into
two when written as RTTM. Sanitising the field (`Speaker_A`) restored exact agreement with the
dataset's declared counts on all 12 Indic files. Reference plumbing is where silent scoring errors
live.



## 3.4 Proposed production collection (not collected)

The proposed benchmark contains **60 hours: 12 public development hours and 48 private evaluation
hours**. Four domains each receive 15 hours: meetings, telephone, interviews/media, and informal
conversation. Each domain is half English and half Indic; Hindi, Bengali, Marathi, Tamil, Telugu,
and Kannada receive five hours each across the complete collection. At least 25% of evaluation
recordings and duration should contain five or more speakers.

Target 2-party calls, 2–8-person meetings/interviews and dedicated 6–12-speaker crowded sessions.
Collect headset/USB-mic, laptop/phone, tabletop/distant-mic and native telephone audio; keep native
sample-rate metadata (upsampling an 8 kHz call does not restore its lost bandwidth). Balance regional
accents and urban/rural speaker backgrounds within languages where recruitment allows, record
self-declared metadata with consent, and publish representation gaps.

Record microphone/device, noise, accent/region (consent permitting), speaker count, turn length,
overlap, and code-mixing. Use source-conversation and speaker-group-disjoint splits, keeping all
microphone variants of a session together. Development material must permit the intended use;
private evaluation conversations require explicit collection and evaluation consent.

Two independent annotators mark acoustic speech boundaries, brief verbal backchannels, and each
simultaneous speaker separately. Pauses are excluded and non-speech vocalizations tagged separately.
Measure pre-adjudication DER, count agreement, and boundary disagreement, then adjudicate with a
third annotator and version the references. The handbook and achieved agreement accompany scores.
This is a collection and quality-control proposal, not an annotation study completed in this pilot.

# 4. Metrics and scoring contract

## 4.1 The metrics

| Metric | Role | Definition |
|---|---|---|
| **DER** | Primary accuracy | (missed + false alarm + confusion) ÷ total reference speaker-time |
| **JER** | Companion accuracy | Mean matched-speaker Jaccard error: 1 minus intersection / union; unmatched reference speakers score 100% |
| **Exact count accuracy** | Speaker coverage | Recordings where predicted count equals reference count |
| **Count MAE / bias** | Coverage, magnitude and direction | mean abs error / mean signed error, in speakers |
| **Low-activity recall** | Proposed diagnostic | Share of low-activity speakers recovered after optimal one-to-one matching |
| **Overlap-only DER** | Diagnostic | DER restricted to reference time with two or more simultaneous speakers |
| **DER components** | Diagnosis | Missed, false-alarm, confusion, each as a share of reference time |
| **RTF** | Practicality | Processing time ÷ audio duration, with the timed workload stated |

DER is duration-weighted, which is exactly why it is insufficient alone: a speaker who contributes
4.6% of a meeting can vanish entirely and move DER by a couple of points. JER gives each reference
speaker equal weight and is the cheapest correction. The **low-activity diagnostic is our proposal**,
not an established community metric, and is labelled as such wherever it appears.

**Low-activity speaker:** at most 5% of reference speaker-time in the recording, and at least 0.5 s
of speech (a stability threshold for this diagnostic, not evidence that shorter speech is noise). **Recovered:** at
least 50% of that speaker's reference time overlaps their optimally matched hypothesis speaker.

## 4.2 Frozen settings

| Setting | Value | Why |
|---|---|---|
| Collar | **0 ms** headline; 250 ms sensitivity alongside | Strict scoring; the sensitivity shows how much is boundary jitter |
| Overlap | **Included** | Ignoring overlap flatters systems that cannot handle it |
| Speaker count | **Unknown** to every system | The system must estimate the count, which is the product requirement |
| Scoring regions | Explicit per recording | Prevents disagreement about lead-in, silence, and trailing audio |
| Count source | Labels with positive activity **inside** the region | A speaker who only speaks outside the excerpt is not a speaker for that recording |
| Output mode | Overlap-capable output preserved | Score the system as users receive it, not a mode tuned for the benchmark |

**Collar convention matters.** A collar excludes a window around reference speech boundaries so
small timing offsets receive less weight. In this harness, `pyannote.metrics collar=0.25` means a
250 ms total window, or 125 ms on each side, as implemented by `UEMSupportMixin.extrude`.
The saved 250 ms sensitivity results use that exact setting; they must not be silently interpreted
as a plus/minus 250 ms window from a different scorer. A collar can also hide brief-turn errors,
so zero collar remains the primary result and overlap/speaker-count rules stay unchanged.

The headline number is therefore DER at zero collar, overlap scored, unknown count. Every other
number is a companion or a sensitivity, never a substitute.

## 4.3 Validating the instrument before using it

Scoring was validated on nine hand-computed fixtures before any real audio was scored: perfect
output (0.0% DER), permuted labels (0.0%), missing brief speaker (2.44% DER, 50% JER, count −1,
low-activity recall 0), merged speakers (50% confusion), split speaker (50% confusion),
overlap-perfect (0.0%), silence false alarm (50%), empty hypothesis (100%), and invalid timestamps
(rejected). **25/25 tests pass.** DER and JER agree with `nryant/dscore` within 2% and 3%
respectively on every fixture, after normalising dscore's percent units against pyannote's
fractions.

One caveat is carried forward rather than hidden: Anuvani's model card reports that
`pyannote.metrics` reads about 0.20 percentage points higher than NIST `md-eval` on Indic DiarBench. Our absolute
numbers are therefore not directly comparable to md-eval numbers published elsewhere. Within-run
comparisons use the same scorer consistently; this does not prove a universal constant offset.



# 5. Systems under test

## 5.1 The three pilots

| System | Family | Speaker / overlap behaviour | Licence | Exposure (pilot corpora) | Settings |
|---|---|---|---|---|---|
| pyannote community-1 | Modular: segmentation + embedding + VBx | No hard cap; overlap-capable | Open weights, gated access | **Known overlap** on AMI + VoxConverse; unknown on Indic | Unknown count; regular (non-exclusive) output |
| NVIDIA Nemotron-3 | End-to-end Sortformer, ~100M parameters | **Hard cap 8 speakers**; overlap-capable | OpenMDW v1.1 | Unknown | Streaming, low-latency mode (see 5.3); 8 channels |
| CIIL Anuvani | End-to-end (DiariZen `md-v2` + Indic fine-tune) | 22 Indic languages + English | CC BY-NC 4.0 weights | **Known corpus exposure** on Indic DiarBench; parent training includes AMI + VoxConverse | Default; unknown count |

Exact repository IDs: `pyannote/speaker-diarization-community-1`,
`nvidia/Nemotron-3-Diarization`, `CIIL/Anuvani-Diarization`. These are the identifiers a
reviewer can resolve; no family name stands in for a checkpoint.

The three were chosen to cover the families a product team will actually shortlist: a modular
general baseline, a streaming end-to-end model, and an Indic-specialised end-to-end model. Published repository IDs and dependency constraints are recorded in `pins.md`. The run templates
do not consistently pin immutable checkpoint revisions or capture full environment locks; exact
future inference reproduction is therefore limited. Saved RTTMs make this scoring analysis repeatable.

## 5.2 Two additional systems were attempted but not benchmarked

- **DiariZen `md-v2`** (the parent of Anuvani) is blocked by its environment: Python 3.10, torch
  2.1.1, and a vendored pyannote 3.1, with no conda on Kaggle. Its architecture is represented via
  Anuvani, its Indic derivative.
- **3D-Speaker CAM++** installed and ran but collapsed a six-speaker conversation to one speaker.
  The adapter was not validated further within the budget. This is an unsuccessful integration
  attempt, not evidence that the model is inferior. Excluding it after a poor smoke result also
  creates selection bias; a production benchmark must publish attempted integrations and failures.

The plan's fallback rule allowed exactly this: three working systems on the same 24 recordings, with
the reduction disclosed. No recording was dropped.

## 5.3 A deviation that must be disclosed: Nemotron ran in streaming mode

The plan called for Nemotron's documented offline configuration. That was not achievable in this
environment: the checkpoint's position limit is 5,000 frames (about 50 s), which makes a single
forward pass over a 25-minute meeting unsafe, and NeMo's offline long-audio wrapper was not
available. Nemotron was therefore run in the processor's **streaming, low-latency** mode, chunk by
chunk, on every file.

This is an operating-mode mismatch and it is not cosmetic. Three observations motivate a matched-mode follow-up: Nemotron's error is **79% missed speech** overall and **88% on AMI**, a pattern consistent with conservative speech activation, although the cause was not isolated; its AMI DER (29.6%) is the
highest of the three tested configurations; and Anuvani's card lists Nemotron at **18.38%** on Indic DiarBench under offline
scoring, against our 25.1% Indic result. The honest reading is that **Nemotron's row is a streaming
data point, not a verdict on its offline capability**, and the leaderboard must show operating mode
as a column. We keep the run, label it, and retain its descriptive results without awarding it an offline rank. A same-data rerun in both
modes is required to measure a mode effect; a published full-corpus score cannot estimate it.



## 5.4 Broader comparison catalog: twelve named systems

The assignment requires at least ten concrete candidates. Only the three pilots above have measured
results. The following catalog covers self-hosted, cloud, and on-device products; it is not a
12-system evaluation. Public identifiers are given where available. Opaque API backends require the
request configuration, response version metadata, region, and run date to be archived at execution.
Documentation was reviewed on 11 November 2026; an API feature name is not a pinned checkpoint.

[[widths:10,39,23,28]]
| # | System / published identifier | Organization / family | Delivery and evaluation status |
|---|---|---|---|
| 1 | `pyannote/speaker-diarization-community-1` | pyannote; modular clustering | Self-hosted; measured offline |
| 2 | `nvidia/Nemotron-3-Diarization` | NVIDIA; end-to-end Sortformer | Self-hosted; measured streaming |
| 3 | `CIIL/Anuvani-Diarization` | CIIL; DiariZen-derived | Self-hosted; measured offline |
| 4 | `BUT-FIT/diarizen-wavlm-large-s80-md-v2` | BUT-FIT; WavLM-based diarization | Self-hosted; environment blocked |
| 5 | Precision-2 (`model="precision-2"`) | pyannoteAI; diarization pipeline | Cloud API; not run |
| 6 | Deepgram Nova-3 with versioned diarization (`diarize_model=v2`, batch) | Deepgram; ASR + diarization | Cloud API; not run |
| 7 | AssemblyAI Speaker Diarization (`speaker_labels=true`) | AssemblyAI; ASR + speaker labels | Cloud API; backend version/config to archive; not run |
| 8 | Amazon Transcribe (`ShowSpeakerLabels`) | AWS; ASR + speaker partitioning | Cloud API; backend not publicly pinned; not run |
| 9 | Speech-to-Text V2 Chirp 3 (`chirp_3`) | Google; ASR + diarization | Cloud API; not run |
| 10 | Speechmatics Batch Transcription with speaker diarization | Speechmatics; ASR + speaker labels | Cloud API; backend/config to archive; not run |
| 11 | Falcon (`pvfalcon`) | Picovoice; local diarization engine | On-device SDK; not run |
| 12 | SpeakerKit (`SpeakerKit`, Argmax OSS Swift) | Argmax; Core ML diarization | Apple-device SDK; not run; ASR optional |

Commercial API systems require paid access, service-specific language checks, and a disclosed
ASR workload where coupled. Self-hosted weights require their own license review: Anuvani and
DiariZen weights are non-commercial. Speaker limits, overlap representation, supported languages,
and immutable revisions must be checked for the exact execution configuration rather than inferred
from a family name. Count limits above a model's capacity are retained and flagged, not excluded.

API elapsed time includes upload, queuing, polling, inference, and result retrieval. SDK speed is
measured on the target device. Neither is directly ranked against Kaggle GPU inference-only RTF.
Offline and streaming accuracy ranks are also separate; all-mode views have no shared rank.

Official product references: [pyannoteAI](https://docs.pyannote.ai/api-reference/diarize),
[Deepgram](https://developers.deepgram.com/docs/diarization),
[AssemblyAI](https://www.assemblyai.com/docs/pre-recorded-audio/label-speakers),
[AWS](https://docs.aws.amazon.com/transcribe/latest/dg/diarization.html),
[Google Chirp 3](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3),
[Speechmatics](https://docs.speechmatics.com/speech-to-text/features/diarization),
[Falcon](https://picovoice.ai/docs/falcon/), and
[SpeakerKit](https://github.com/argmaxinc/argmax-oss-swift).

# 6. Execution and reproducibility

## 6.1 Pipeline

The production evaluation proceeds through these eight steps; the pilot implements the saved-audio,
inference, scoring and analysis stages, while consented collection and independent publication are proposals.

1. **Collect and register:** obtain permitted audio, consent where required, source IDs and metadata.
2. **Build references:** dual annotation, pre-adjudication agreement, adjudication and reference versioning.
3. **Freeze the test:** development/evaluation splits, scoring regions, 16 kHz mono conversion, checksums,
   collar/overlap/count policy and supported operating tracks.
4. **Register each system:** exact available identifier, immutable revision when obtainable, delivery mode,
   license/access, settings and training-exposure declaration. Missing version provenance stays visible.
5. **Run and preserve:** execute on the canonical audio, checkpoint recording-level status, and retain raw
   outputs, RTTMs, timing scope, errors and coverage without hiding unsupported cases.
6. **Score consistently:** validate RTTMs, apply the common UEM and scorer, compute accuracy, counting,
   overlap and timing diagnostics, and keep incomplete runs unranked.
7. **Assess and inspect:** paired conversation-level bootstrap, corrected comparisons and practical
   thresholds; inspect corpus/language slices and listen to selected examples without claiming a formal audit.
8. **Publish and maintain:** review the evidence, publish scores with uncertainty, mode/settings/hardware,
   coverage/exposure/reference versions and examples, archive prior boards, and re-score every affected
   system after a reference correction. API/device timing and offline/streaming ranks stay separate.

`manifest › inference › hypothesis RTTM › scoring › tables and figures`. Every unit (one system, one
recording) writes its own RTTM, timing JSON, and status entry, and the driver skips a unit only when
status is `ok` **and** the RTTM is non-empty. Re-running the notebook after an interruption resumes
without repeating completed work. Raw output is zipped on Kaggle and merged locally by
`scripts/t09/merge_output.py`, which applies the same done-rule as the orchestrator.

All 72 units completed on a Kaggle Tesla T4 ×2 in one notebook session, with **zero errors** and no
missing recordings. Total inference time across the three systems was about 42 minutes of GPU time,
well inside the 12 GPU-hour pilot budget.

## 6.2 The environment was the hard part

Three failures cost real time and are recorded because they are the difference between a
reproducible run and a lucky one:

- **Broken mixed NumPy.** The image ships Debian NumPy 1.26.4 plus a partial pip 2.1.3, producing
  `numpy.ufunc has no __qualname__`. Resolution: `numpy>=2.5,<2.6` together with `numba>=0.67`
  (the first numba that accepts NumPy 2.5), plus an end-of-install forced NumPy reinstall as a
  safety net. Two earlier attempts (`numpy<2.3`; `numba>=0.60`) both left a broken ufunc state.
- **Torch silently upgraded.** Installing `pyannote.audio` pulled torch 2.15.0, which broke the
  runtime. Pinned `torch<2.15` and `torchvision<0.27` in the same install.
- **MP3 truncation.** `torchcodec` mis-read an MP3 as 9.93 s instead of 97.6 s. Every input is now
  16 kHz mono WAV.

## 6.3 Timing protocol

Timing is measured on a fixed six-recording panel spanning 3–25 minutes, with one warm-up and
three timed repetitions per recording. **Setup/load is timed separately and excluded from RTF.**
The kernel times each system's `infer(wav)` callable, not an identical abstract model operation.
File loading and required processing inside those callables are included. In particular, the
Nemotron timing path returns frame logits without the pilot's final speaker-segment extraction;
the other callables return pipeline outputs. These are measured implementation timings, not fully
matched end-to-end workloads. No scoring or result upload is timed. Setup may include dependency
checks/model initialization; Anuvani also performs its startup self-test. Three repetitions do not
measure variation across fresh sessions or hardware.
RTF is reported instead of "latency" because offline throughput says nothing about streaming
responsiveness. Native streaming latency needs a live-input protocol, which is out of pilot scope and
stated as such.



# 7. Results

## 7.1 The main table

Equal-weight over the 24 recordings. Intervals: paired bootstrap, 10,000 resamples, seed 20261111
for DER and JER; Wilson for count accuracy; recording-clustered bootstrap for low-activity recall
(speakers are nested in recordings, so a naive interval would be too narrow).

[[widths:18,15,15,12,10,14,9,7]]
| System | DER % | JER % | Exact count | Count bias | Low-activity recall | DER @250 ms | RTF |
|---|---|---|---|---|---|---|---|
| community-1 | 20.4 [15.5, 25.3] | 38.6 [30.3, 47.2] | 38% [21, 57] | −1.17 | 45% [12, 69] | 16.7 | 0.072 |
| Nemotron-3 | 21.6 [15.7, 27.6] | 32.5 [23.4, 41.6] | **58% [39, 76]** | −0.92 | **61% [35, 81]** | 18.8 | 0.079 |
| Anuvani | **13.8 [10.0, 17.9]** | **29.9 [22.7, 37.4]** | 33% [18, 53] | **−0.58** | 47% [14, 72] | **10.3** | **0.053** |
^ Table 1. Pilot leaderboard row per system. Exact repository IDs are given in Section 5.1. Counts are in-region. Low-activity recall is over 38 low-activity speakers across 24 recordings. Count MAE is in Table 3; model load time and RTF detail are in Table 6. RTF is the duration-weighted panel mean, load excluded. Completion coverage is 24/24 for every system.

The intervals are the story as much as the means: all three overlap, so the table alone cannot tell
you whether Anuvani is genuinely ahead. That is why Section 8 tests the paired differences directly
rather than asking a reader to eyeball overlapping intervals.

## 7.2 Per corpus

| System | Indic (12) | AMI-SDM (6) | VoxConverse (6) | Corpus-equal |
|---|---|---|---|---|
| community-1 | 26.1 | 22.7 | 6.8 | 18.5 |
| Nemotron-3 | 25.1 | 29.6 | 6.5 | 20.4 |
| Anuvani | **16.5** | **17.5** | **4.9** | **12.9** |
^ Table 2. DER % by corpus, native reference conventions. The corpus-equal column weights the three corpora equally; the global 24-recording mean is 20.4 / 21.6 / 13.8.

[[fig:per_corpus_der.png|Figure 1. Per-corpus DER. Observed DER is lower on these VoxConverse excerpts than on the other corpora. Content, speaker participation and reference conventions all vary; this plot does not isolate their effects. Cross-corpus aggregates are exploratory.]]

Anuvani has the lowest observed mean in each corpus; the ordering of these tested means does
not change under the reported weighting summaries. This does not remove exposure or mode confounds. The *margin* changes with weighting. On Indic it is 8.6–9.6 pp, on AMI 5.2–12.1
pp, on VoxConverse 1.6–1.9 pp. A leaderboard that ranked on VoxConverse alone would call the three
systems nearly equal (4.9–6.8%); a leaderboard that ranked on Indic alone would call the gap huge.
Neither is wrong; a single pooled number would hide both.

## 7.3 Indic languages

[[fig:indic_language.png|Figure 2. Indic DER by language, two recordings per language. Telugu floors every system; Tamil separates them most; Kannada reverses the community-1/Nemotron order. With n=2 per cell these are exploratory slices, not language rankings.]]

Telugu is the hard slice for everyone (36.1–50.1%) and it is the highest-overlap language in the
pilot (20.4–28.3% on the two files). Tamil separates the systems most sharply: Anuvani 7.8% against
16.9% (Nemotron) and 25.1% (community-1). Kannada shows why two recordings per language cannot
support a ranking: Nemotron's 31.9% is its worst Indic cell, while Anuvani's 10.1% is its best.

## 7.4 Where the error comes from

[[fig:der_components.png|Figure 3. DER decomposed into missed speech, false alarm, and confusion. community-1 and Nemotron lose most of their error to missed speech; Anuvani is balanced and low on all three. Components sum to the DER in Table 1.]]

The decomposition changes the interpretation of the ranking. community-1's 20.4% is 10.6 missed +
3.1 false alarm + 6.6 confusion. Nemotron's 21.6% is 17.1 missed + 1.2 false alarm + 3.3 confusion:
most of its error is missed speech. Configuration, model behavior, and reference conventions could
all contribute; their effects were not isolated. Anuvani's 13.8% is 6.8 + 2.9 + 4.1, the only balanced profile. On Tamil
`TA-02`, community-1's 29.6% is dominated by **confusion (22.1 pp)** with only 3.2 pp missed: it
hears the speech and assigns it to the wrong person, collapsing three reference speakers into two.

## 7.5 Speaker counting

[[fig:count_bias.png|Figure 4. Signed speaker-count bias with mean absolute error. Every system under-counts on average; community-1 is the most biased, Anuvani the least.]]

[[widths:16,8,8,8,12,12,14]]
| System | Exact | MAE | Bias | Indic MAE | AMI MAE | VoxConverse MAE |
|---|---|---|---|---|---|---|
| community-1 | 9/24 | 1.17 | −1.17 | 1.83 | 0.50 | 0.50 |
| Nemotron-3 | **14/24** | 0.92 | −0.92 | 1.42 | **0.00** | 0.83 |
| Anuvani | 8/24 | **0.83** | **−0.58** | **1.08** | 0.67 | 0.50 |
^ Table 3. Speaker-count behaviour, in-region counts.

Two different failure shapes hide behind similar MAE. Nemotron is exactly right most often (14/24,
mostly the four-speaker AMI meetings) but carries the worst single error in the run: on `VC-01` it
emits 8 speakers against 13 in the excerpt (15 in the full recording), a −5 error caused by its hard
cap. Anuvani is rarely exactly right but rarely far off — a scattering of ±1 misses. community-1
systematically under-counts Indic (MAE 1.83, bias −1.83), which is the "beyond DER" failure the
diagnostic exists to catch: on `BN-01` it finds 4 speakers where the reference has 8.

## 7.6 Low-activity speaker coverage

| System | Recovered | Recall | 95% CI | Recall at 3% / 10% activity |
|---|---|---|---|---|
| community-1 | 17/38 | 45% | [12, 69] | 38% / 53% |
| Nemotron-3 | 23/38 | 61% | [35, 81] | 58% / 62% |
| Anuvani | 18/38 | 47% | [14, 72] | 42% / 53% |
^ Table 4. Low-activity recall at the headline 5% activity / 0.5 s duration / 50% recovery thresholds, with the contract-mandated sensitivity at 3% and 10% activity. The full 3×3 grid is in Appendix C.

The ordering is stable across the sensitivity grid — Nemotron first, community-1 and Anuvani
indistinguishable — but the *level* is not: recall rises with the activity threshold because more
speakers qualify and the easy ones are recovered. The intervals are wide (35–81% for the leader)
because 38 speakers nested in 24 recordings is a small sample. **No system recovers even two thirds
of the people who speak least**, and the best system on this diagnostic is the worst on DER. That
combination is the argument for publishing coverage next to accuracy.

[[fig:speaker_coverage.png|Figure 6. Exact count accuracy and low-activity recall with 95% intervals. Count intervals use Wilson; recall intervals resample recordings. Differences are descriptive and do not establish coverage superiority.]]

## 7.7 Overlap

Overlap is where the pilot's most uncomfortable number lives. Mean overlap-only DER across the 23
recordings that contain overlap is **68.2% (community-1), 59.9% (Nemotron), 67.7% (Anuvani)** —
against whole-file DER of 20.4 / 21.6 / 13.8. On the densest moment of Telugu `TE-02`
(three simultaneous speakers at 97.2–97.7 s) overlap-only DER is 99.8 / 81.8 / 91.7%.

Overlap-only DER does **not** track headline DER here: Anuvani has lower overall DER but worse overlap-only DER than Nemotron. community-1 has
slightly higher overlap-only DER than Anuvani (68.2% versus 67.7%). We report the observation and
resist the tidy explanation. At n=24 with 23 overlap-bearing files, the overlap view is a
diagnostic that shows how much error concentrates in simultaneous speech, not a ranking signal. It
does establish one thing clearly: a benchmark that skipped overlap would be measuring a different,
easier task.

## 7.8 Collar sensitivity

| System | DER, zero collar | DER, 250 ms collar | Change |
|---|---|---|---|
| community-1 | 20.4 | 16.7 | −3.6 |
| Nemotron-3 | 21.6 | 18.8 | −2.8 |
| Anuvani | 13.8 | 10.3 | −3.5 |
^ Table 5. Boundary-collar sensitivity. The 250 ms collar is a companion result, never a substitute for the zero-collar headline.

Removing a 250 ms boundary collar changes scores by about three points; this is boundary
sensitivity, not proof that all removed errors are harmless jitter. The ranking is unchanged, which is
the useful part: the conclusion does not depend on the collar, but the magnitude does, and a
submission that reported only the 250 ms number would overstate every system by roughly 15% of its
error.

## 7.9 Speed

[[fig:accuracy_speed.png|Figure 5. Accuracy against speed. Anuvani is bottom-left: most accurate and lowest RTF. Nemotron is top-right. Axes are DER (lower better) and RTF (lower better).]]

| System | Setup/load (s) | RTF | Speed factor | RTF range across files |
|---|---|---|---|---|
| community-1 | 0.57 | 0.072 | 13.9× | 0.064 (5&nbsp;min) to 0.077 (25&nbsp;min) |
| Nemotron-3 | 0.73 | 0.079 | 12.7× | 0.078–0.079 (flat) |
| Anuvani | 12.98 | **0.053** | **18.8×** | 0.051–0.054 (flat) |
^ Table 6. Timing panel: one warm-up plus three repetitions on six recordings, one T4 ×2. Load excluded from RTF.

Two structural findings matter more than the ranking. First, **the modular pipeline degrades with
length** (0.064 to 0.077) while the two end-to-end systems are flat, so RTF measured only on 5-minute
clips would flatter community-1. Second, **load time inverts the ranking for short files**. For a
single 5-minute recording, a setup + 300 × panel-RTF projection is 22.1 s (community-1), 24.3 s (Nemotron), 29.0 s
(Anuvani) — community-1 is fastest. The break-even is about 11 minutes of audio; beyond that Anuvani
has the lower projected total. These are extrapolations, not measured five-minute end-to-end
service requests, and depend on whether setup is repeated. The unmatched timed-callable scope
also prevents a universal speed claim.



# 8. How sure are we that one system beats another?

Paired bootstrap over the 24 independent recordings, 10,000 resamples, fixed seed. A win requires
both statistical significance after Bonferroni correction across the three pairwise comparisons and
the predeclared **≥1 pp DER** practical threshold.

| Pair | Mean Δ DER (pp) | 95% CI | Bonferroni CI | Verdict |
|---|---|---|---|---|
| community-1 vs Nemotron | −1.2 | [−4.2, +2.0] | [−5.0, +2.6] | **not resolved** |
| community-1 vs Anuvani | +6.6 | [+4.4, +9.1] | [+3.9, +9.7] | **Anuvani wins** |
| Nemotron vs Anuvani | +7.8 | [+4.6, +11.1] | [+4.0, +12.0] | Mode-confounded |
^ Table 7. Pairwise DER differences. Negative means the first system has lower DER. Mixed-mode rows describe tested configurations and do not establish model superiority.

| Pair | Mean Δ JER (pp) | 95% CI | Bonferroni CI | Verdict |
|---|---|---|---|---|
| community-1 vs Nemotron | +6.1 | [−1.0, +12.6] | [−2.4, +14.2] | not established |
| community-1 vs Anuvani | +8.7 | [+5.3, +13.1] | [+4.8, +14.3] | **Anuvani wins** |
| Nemotron vs Anuvani | +2.7 | [−3.6, +9.0] | [−4.7, +10.2] | not established |
^ Table 8. Pairwise JER differences, same resampling scheme.

[[fig:paired_differences.png|Figure 7. Paired DER differences with Bonferroni-adjusted bootstrap intervals. The community-1/Anuvani row is the matched offline comparison; the other two rows are mode-confounded. The shaded band marks plus/minus 1 pp.]]

The two metrics agree on one claim and disagree on another. Both put Anuvani ahead of community-1
in this sample under the stated test. On Nemotron, DER says the gap is large and significant (+7.8 pp) while JER says it is
not established (+2.7 pp, CI spanning zero). JER equal-weights speakers, so the disagreement means
Anuvani's DER and JER answer different weighted questions. These averages alone do not locate which
speakers account for the difference; the JER gap is smaller and less certain. The defensible summary is:

> **Among the two offline systems, Anuvani has lower DER in this pilot. Its observed DER gap
> against the streaming Nemotron configuration is descriptive and cannot establish offline-model
> superiority. The community-1/Nemotron difference is not resolved; absence of significance does
> not prove equivalence. On JER, only the Anuvani–community-1 difference is established.**

This is the kind of statement a leaderboard should make it easy to produce and hard to overstate.
With 24 recordings, the detectable difference is roughly 4 pp; anything smaller than that is a
suggestion, not a result.



# 9. Three failure analyses

Each case is drawn from saved hypotheses and reference timestamps; `scripts/t10/analyze.py`
reproduces the excerpts.

## 9.1 A brief speaker disappears (`BN-01`, Bengali near-field)

Reference speaker `SPEAKER_05` contributes **12.87 s, 4.6% of the meeting's speech**, in six short
interjections across 168 seconds. All three systems drop the speaker (low-activity recall 0/1):

| System | Hypothesis speakers | `SPEAKER_05` recovered |
|---|---|---|
| community-1 | 4 of 8 | no |
| Nemotron-3 | 6 of 8 | no |
| Anuvani | 6 of 8 | no |

The reference/hypothesis alignment suggests overlap with dominant turns and possible speaker
merging. This is a timestamp-based interpretation, not a verified listening judgment: the speech time is largely still present, scored as confusion or
miss, but the person has vanished from the transcript. This is the exact failure the low-activity
diagnostic was designed to expose, and it is invisible in a DER table that shows 22.8–41.2% for the
same file.

## 9.2 Three people talk at once (`TE-02`, Telugu in-the-wild)

At 97.2–97.7 s the reference has three simultaneous speakers:

- `Speaker_D` [92.1–97.7], `Speaker_A` [96.5–97.7], `New_speaker_A` [97.2–98.6]

The systems handle the same instant very differently. community-1 emits four labels in 0.6 s with
0.1–0.3 s slivers (over-segmentation). Nemotron emits three labels but splits one into two adjacent
90 ms fragments (boundary smear). Anuvani emits three local labels; their count alone does not establish correct identity or
boundaries. No listening-based quality judgment was made. On the full recording,
overlap-only DER on this file is 99.8 / 81.8 / 91.7%: even the cleanest output loses most of the
overlap. Overlap handling, not clean single-speaker speech, is what separates these systems in
practice.

## 9.3 A multilingual slice separates tested configurations (`TA-02` Tamil vs `TE-02` Telugu)

The source corpus describes code-mixing in its in-the-wild material. Without language-boundary
annotations or a listening audit, these two examples support a multilingual comparison, not a
causal claim about code-switching. The two Dravidian files tell different stories:

| Recording | community-1 | Nemotron-3 | Anuvani | Failure mode |
|---|---|---|---|---|
| `TA-02` Tamil (3 speakers) | 29.6 | 16.8 | **5.7** | community-1: confusion 22.1 pp, collapses 3 to 2 |
| `TE-02` Telugu (8 speakers) | 38.6 | 42.0 | 38.4 | all: missed + confusion, 20.4% overlap |
^ Table 9. Two multilingual in-the-wild conversations. Code-switch boundaries were not annotated in this pilot.

On Tamil, community-1 is not missing speech (3.2 pp missed); it is confidently attributing speech to
the wrong person (22.1 pp confusion) and losing a speaker entirely. Anuvani, fine-tuned on Indic
conversation, is at 5.7%. On Telugu, the highest-overlap language in the pilot, everyone fails
(38.4–42.0%) and the specialist's advantage nearly disappears. The pair is the strongest practical
argument for inspecting Indic slices and a warning against attributing the gap specifically to
code-mixing, model specialization, or microphone conditions without controlled comparisons.



# 10. Annotation audit: what the references disagree about

Six excerpts (2 Indic, 2 AMI, 2 VoxConverse) were audited structurally against a unified convention.
This pass did not re-listen to audio; it characterises where the corpora's conventions diverge, which
is the part that affects cross-corpus comparison.

[[widths:11,12,10,9,9,12,11,11]]
| Excerpt | Corpus | Region (s) | Speakers | Segments | Speech density | Overlap share | Segments < 0.5 s |
|---|---|---|---|---|---|---|---|
| HI-01 | Indic | 196.6 | 9 | 69 | 110.8% | 16.1% | 12 |
| TE-02 | Indic | 300.0 | 8 | 163 | 122.9% | 21.2% | 20 |
| AMI-02 | AMI | 2142.7 | 4 | 746 | 118.1% | 20.5% | 223 |
| AMI-04 | AMI | 1505.6 | 4 | 242 | 68.1% | 4.4% | 79 |
| VC-01 | VoxConverse | 300.0 | 13 | 49 | 100.8% | 8.8% | 5 |
| VC-03 | VoxConverse | 300.0 | 8 | 35 | 91.6% | 0.1% | 1 |
^ Table 10. Structural audit of six references. Speech density is reference speaker-time divided by region duration; above 100% means overlap is being counted.

The audit establishes structural differences, not their cause or a measured DER penalty:

1. **Overlap coverage differs.** Observed overlap varies across these files, including very low
   values in several VoxConverse excerpts. This can reflect conversation content, annotation policy,
   or both. Without listening and re-annotation, low labelled overlap is not evidence of missing labels.
2. **Segment granularity differs.** AMI has many word-timed segments, while VoxConverse uses longer
   turns. Adjacent segments from the same speaker may merge into the same activity union; segment
   counts alone do not establish extra boundary error.
3. **Speech density is not speech occupancy.** The table divides speaker-time by region duration,
   so values above 100% are possible under overlap. It does not measure the fraction of silence.
   For example, AMI-02 has 118.1% density; AMI cannot be summarized as uniformly 68–88% speech.

**No acoustic reference corrections were made.** The six-file audit checks structure and timestamps;
it does not establish that any reference is correct, defective, or internally acoustically consistent.
Per-corpus reporting and exploratory cross-corpus aggregates are appropriate until a listening-based,
blinded re-annotation study measures convention effects under a common handbook.



# 11. Did the research-inspired hypotheses hold?

| # | Hypothesis from the reading | What the pilot observed | Verdict |
|---|---|---|---|
| H1 | Count and low-activity diagnostics reveal failures DER hides (Beyond DER) | The community-1/Nemotron DER gap is not resolved; count accuracy differs by 20.8 pp and low-activity recall by 15.8 pp descriptively; no coverage superiority test was performed | **Supported** |
| H2 | The Indic/code-mixed slice separates general from Indic-specialised systems (Indic DiarBench) | Anuvani leads Indic by 8.6–9.6 pp and Tamil by 9–17 pp — but also leads AMI and VoxConverse, so the advantage is not Indic-specific; Indic exposure is confounded | **Partially supported** |
| H3 | Accuracy must be reported with measured speed, because there is a trade-off (SDBench) | No accuracy/speed trade-off appeared: Anuvani is both most accurate and lowest RTF. A load-time/throughput trade-off does exist and flips the ranking below ~11 min of audio | **Supported as a rule; predicted trade-off absent** |
| H4 | Strict scoring is the honest default (DIHARD III) | Zero collar, overlap scored, unknown count produce a defensible ranking; 250 ms collar moves scores 2.8–3.6 pp without changing it; overlap-only DER is 60–68% | **Supported** |
| H5 | Annotation conventions move DER materially (Anuvani) | Observed reference structure differs; content and convention effects remain confounded because no audio was re-annotated | **Partially supported** |
| H6 | Error decomposition and crowded-recording analysis reveal failure modes (Benchmarking Diarization Models) | Components explain the ranking: Nemotron is 79% missed speech, community-1's Tamil failure is 75% confusion, the 8-speaker cap surfaces as a −5 count error | **Supported** |
| H7 | Speaker changes and language changes are entangled in code-switched speech (DISPLACE) | Not tested: the pilot has no language-boundary annotations, so code-mixing enters only through corpus metadata | **Not tested** |

Two of these verdicts cost something to write. H2 is weaker than the headline suggests: the
tested specialist configuration has the lowest means across these samples. Base-model quality,
training-corpus exposure, configuration, and adaptation effects remain confounded. H5 is the one we most wanted to quantify and could not, because quantifying convention effects
requires re-annotating audio, not re-reading RTTM files.



# 12. Threats to validity

- **Sample size.** 24 recordings, two per Indic language. The detectable DER difference is about
  4 pp; every per-language cell is exploratory. Anuvani's Indic margin is credible in direction,
  not in size.
- **Exposure.** Anuvani was fine-tuned on Indic DiarBench, one of the three pilot corpora. Its Indic
  result is an in-domain result. Its parent also lists AMI and VoxConverse as training corpora.
  community-1 has AMI/VoxConverse exposure; Nemotron's exposure is unknown. Exposure is printed on every score, and no cross-system claim ignores it.
- **Operating mode.** Nemotron ran streaming/low-latency, the other two offline. Its row is a
  streaming data point; its published offline Indic figure (18.38%) is 6.7 pp better than our 25.1%,
  on a different full-corpus protocol. It neither measures nor bounds a mode penalty here.
- **Corpus composition confound.** Indic near-field files have 5–9 speakers and 13–28% overlap;
  in-the-wild excerpts include 3–8 speakers and different overlap levels. The pilot's "near-field is harder"
  result (32.8 vs 13.0% for community-1) is confounded by speaker count and conversation content;
  it does not isolate a microphone effect.
- **Reference quality.** References were validated for internal consistency and speaker counts, not
  by listening. The audit is structural. A human listening pass is the obvious next step.
- **Scorer offset.** `pyannote.metrics` reads about 0.20 percentage points higher than NIST `md-eval` on Indic
  DiarBench according to Anuvani's card. Absolute values are not comparable to md-eval publications;
  relative comparisons here use one scorer consistently; a model-dependent offset is not ruled out.
- **Timing.** One GPU type and three repetitions. The timed callables differ in I/O and output
  post-processing scope; Nemotron returns frame logits. Setup/load can include dependency checks
  and Anuvani's self-test. Projected five-minute totals are not measured service latency.
- **Inference provenance.** Repository IDs and dependency constraints are recorded, but complete
  immutable weight revisions and environment locks were not consistently captured. Saved outputs
  support rescoring; a bit-for-bit future inference rerun is not guaranteed.
- **Excerpt truncation.** AMI is scored whole while the other corpora are excerpted, so file length
  is confounded with corpus. Per-corpus reporting contains the damage; it does not remove it.

- **No transcription-quality evaluation.** cpWER, tcpWER, WER/CER and related speaker-attributed
  ASR metrics were not run. The saved hypotheses contain activity labels, not recognized words.
- **Coverage and selection.** Three systems and three public corpora exclude telephone, healthcare,
  and many acoustic/language conditions. Unsuccessful integrations are disclosed; this is not a
  census of available systems or evidence that excluded models are worse.
- **Statistical interpretation.** Non-significant differences do not prove equivalence. Coverage
  gaps are descriptive, not tested superiority claims. Mixed-mode tests describe configurations;
  they cannot support a common offline/streaming model rank.

# 13. From pilot to production leaderboard

The pilot validates the instrument; the production design scales it. The full sketch is a separate
deliverable; the operating rules that matter are these.

**Aggregation.** Eight domain × language-group cells (four domains × {English, Indic}), equal cell
weights, with the conventional globally pooled number and every cell published alongside. The pilot
approximates this with three corpus cells and six language slices, and says so.

**UI references and implemented product.** The supplied SignalBench HTML and MagicPath project
informed the overview, results, comparison, audio inspector, datasets and evaluation-run sections.
Their demo scores/settings and simulated audio were not used as evidence. The local HTML uses saved
pilot results and three playable, attributed Indic DiarBench excerpts. It supports waveform seeking,
speed controls, reference/model timelines, speaker-turn previews, local-file playback, run inspection
and configuration export. Previews play the original mixture, not separated voices; configuration
export does not launch inference. The PDF is a static sketch; the HTML is the functional prototype.

**Table.** Model and version, DER with interval, JER, count accuracy, RTF, and completion coverage in
the main row. Filters for domain, language, speaker count, overlap, and operating mode. A model
detail view exposes error components, counting bias, low-activity recall, hardware, settings,
exposure, and one example failure per system, with an entry point to the audio inspector.

**Operating mode is a filter, not a footnote.** Streaming and offline results never share a rank.
The pilot's Nemotron row is the cautionary example: without the mode label it would look like a
worse model rather than a differently configured one.

**Adding systems.** Curated additions require a pinned checkpoint, a documented default
configuration, an exposure declaration, and a complete run over the frozen manifest. Bring-your-own
submissions are accepted only as a separate, clearly labelled track with self-reported settings and
no rank until reproduced.

**Re-scoring and versioning.** References are versioned; a correction triggers a full re-score of all
systems against the new reference version and publishes both the old and new numbers with the diff.
Protocol versions are immutable, and every leaderboard row carries the protocol version that produced
it. A system is never re-ranked silently.

**Current scope and extension.** Speaker-attributed transcription metrics (cpWER/tcpWER), language
diarization, and live streaming latency were not measured. Section 14.4 proposes separately labelled
tracks with their own references, settings, and timing protocol. These do not replace DER/JER.



## 13.1 Roadmap toward a speech evaluation lab (proposed)

A stronger research platform would diagnose individual stages as well as the complete product.
These are proposed experiments, not capabilities evaluated by this pilot. They would share
versioned datasets, consent/access records, immutable environments, held-out test splits,
experiment tracking, automated checks, confidence intervals, and an evidence review before publication.
A lab-quality process means controlled, reproducible experiments, not a promise of state-of-the-art scores.

[[widths:20,42,38]]
| Research track | Experiment and required reference | Outputs and decision |
|---|---|---|
| **Speaker separation** | Recover individual waveforms from an overlapping mixture using clean isolated sources or controlled mixtures. Compare mixture, separated stems and artifacts; test downstream diarization/ASR with and without separation. | Permutation-aligned SI-SDR and SI-SDR improvement, intelligibility/listening checks, downstream DER/tcpWER. Do isolated voices improve attribution without damaging words? |
| **Speaker similarity / verification** | Extract embeddings from consented same/different-speaker pairs across microphones, sessions and languages. Keep identities disjoint between development and test; calibrate thresholds on development only. | Similarity distributions, equal error rate (EER), minimum detection cost (minDCF), false-accept/miss curves and calibration. Raw cosine similarity is not an identity probability. |
| **Speaker clustering** | Hold the speech segments and embeddings fixed; compare agglomerative, spectral and other clustering methods. Use oracle-count runs only as a separately labelled diagnostic. | DER/JER, count MAE, adjusted Rand index and homogeneity/completeness or V-measure. Inspect merging and fragmentation; purity alone can reward too many clusters. |
| **VAD / SAD** | Treat voice activity detection and speech activity detection as the speech-versus-non-speech stage; define filled pauses, backchannels and vocalizations consistently. Test noise, silence and overlapping speech. | Precision, recall, F1, missed-speech/false-alarm time and boundary errors. Fix downstream modules to isolate the effect of the detector and sweep thresholds on development data. |
| **Controlled component studies** | Freeze all but one stage: SAD, embeddings, clustering, overlap handling, separation, or ASR. Compare the same source conversations under matched modes and compute budgets. | Confidence intervals on end-to-end DER/tcpWER changes, RTF/memory/cost and failure cases. Separate a component improvement from a different dataset or implementation. |

The listening room would eventually allow synchronized mixture versus separated-stem playback,
consented speaker-pair listening, clustering merge/split inspection, and SAD overlays. At present it
plays original excerpts and saved speaker turns only; those previews are not separated stems,
computed similarity judgments, or a completed human annotation audit.

Method references: [Asteroid source-separation toolkit](https://github.com/asteroid-team/asteroid),
[SpeechBrain verification metrics](https://speechbrain.readthedocs.io/en/latest/API/speechbrain.utils.metric_stats.html),
and [scikit-learn clustering evaluation](https://scikit-learn.org/stable/modules/clustering.html#clustering-performance-evaluation).

## 13.2 Extending metrics, datasets, and deployment evidence (proposed)

With more time I would expand both **what is measured** and **where it is measured**, while
retaining the existing DER/JER and speaker-coverage results as a separate diarization track.

1. **Add cpWER and tcpWER in a speaker-attributed transcription track.** cpWER (concatenated
   minimum-permutation word error rate) concatenates words by speaker and chooses the speaker
   permutation with the fewest substitutions, deletions, and insertions. tcpWER adds temporal
   constraints so words far apart in time cannot be matched merely because the text is similar.
   These answer whether the right words reached the right speaker stream; they cannot be computed
   from the pilot's RTTMs alone. Neither metric was run in this submission.
2. **Add complementary recognition and temporal diagnostics.** Report ordinary WER, and CER where
   language-specific tokenization makes it useful, to expose recognition errors independently of
   attribution. Consider DI-cpWER or ORC-WER to help distinguish recognition from speaker-assignment
   effects, plus speech-activity and overlap-detection precision/recall/F1 and boundary errors.
   Publish definitions, eligible samples, and uncertainty instead of combining unlike metrics into
   one opaque score. DER/JER, counting, low-activity recall, and RTF remain core outputs.
3. **Build the references these metrics need.** Human-check speaker-attributed transcripts;
   provide segment/word timings or explicitly document MeetEval's pseudo-word timing strategy.
   Freeze text normalization, Indic-script and code-mixed tokenization, punctuation/number policy,
   and tcpWER timing collar on development data. This timing collar is independent of DER's 0/250 ms
   collar. Use a pinned MeetEval version. For diarizer comparisons, hold the ASR model and word-to-turn
   attribution procedure fixed; show complete vendor ASR+diarization systems in a separate track.
4. **Evaluate more diverse datasets.** Add DIHARD III for diverse domains, ICSI for natural meetings,
   CALLHOME for telephone speech, DISPLACE for Indian multilingual/code-switched conversations,
   AliMeeting for Mandarin near/far-field meetings, and CHiME-8 DASR for distant multi-device speech.
   Verify access, licenses, held-out splits, speaker overlap with training, reference conventions,
   and transcript/timestamp availability before use. Give each corpus its own results; no new corpus
   is claimed as evaluated here. Grow toward the proposed 60-hour collection, with sample counts
   chosen using variance and power analysis rather than a fixed minimum that guarantees significance.
5. **Close the current fairness and reference gaps.** Run Nemotron on the same audio in documented
   offline and streaming configurations; isolate mode effects instead of borrowing a published
   score from another protocol. Conduct a blinded listening audit and dual annotation/adjudication
   study, including brief speakers and overlap. Add language-boundary labels to test code-switching
   effects directly, and audit exact source/session exposure for all systems.
6. **Broaden deployment evidence.** Test CPU, GPU, and edge hardware over repeated sessions,
   measure cold/warm end-to-end time and cost per audio-hour, and add a live-input protocol for
   first-result delay, revision delay, and finalization latency. Add human-reviewed meeting-note
   attribution accuracy as a task-level outcome, separately from the acoustic and word metrics.

The practical sequence is: validate references and matching operating modes first; add a fixed-ASR
cpWER/tcpWER pipeline next; then expand corpora and hardware. More metrics without reliable reference
text, timestamp policy, and representative data would add apparent precision rather than evidence.
Definitions and implementation reference: [MeetEval](https://github.com/fgnt/meeteval), including its
[tcpWER protocol](https://github.com/fgnt/meeteval/blob/main/doc/tcpwer.md).

# References

1. Ryant, N. et al. **The Third DIHARD Diarization Challenge.** arXiv:2012.01477 (2020 preprint). Evaluation plan used for the scoring contract (regions, collar, overlap, unknown count).
2. **Beyond DER: Speaker Counting in Crowded End-to-End Diarization.** 2026. arXiv:2609.27315. Source of the count and low-activity diagnostics.
3. Sarvam AI. **Indic DiarBench.** 2026. arXiv:2607.23808. Dataset, language coverage, and code-mixing characterisation.
4. **SDBench: A Comprehensive Benchmark for Speaker Diarization.** 2025. arXiv:2507.16136. Accuracy-with-speed reporting.
5. CIIL. **Anuvani-Diarization.** 2026. arXiv:2610.20327. Annotation-convention effects and Indic results.
6. **Benchmarking Diarization Models across Multilingual Data.** 2025. Error decomposition and high-speaker-count analysis.
7. **The Second DISPLACE Challenge.** 2024. Multilingual Indian speaker and language diarization evaluation plan.
8. Park, T. J. et al. **A Review of Speaker Diarization: Recent Advances with Deep Learning.** Computer Speech & Language, 2022 (2021 preprint).
9. Bredin, H. et al. **pyannote.audio.** Toolkit and `pyannote.metrics` scorer.
10. **dscore** (nryant), commit `e02f949`. Cross-check scorer, as used by Indic DiarBench.
11. **pyannote/speaker-diarization-community-1** model card. https://huggingface.co/pyannote/speaker-diarization-community-1
12. **nvidia/Nemotron-3-Diarization** model card. https://huggingface.co/nvidia/Nemotron-3-Diarization
13. **CIIL/Anuvani-Diarization** model card. https://huggingface.co/CIIL/Anuvani-Diarization
14. **MeetEval: A Toolkit for Computation of Word Error Rates for Meeting Transcription Systems.** arXiv:2307.11394. https://github.com/fgnt/meeteval
15. **Additional dataset documentation:** https://dihardchallenge.github.io/dihard3/ ; https://groups.inf.ed.ac.uk/ami/icsi/ ; https://catalog.ldc.upenn.edu/LDC97S42 ; https://displace2024.github.io/ ; https://www.openslr.org/119/ ; https://www.chimechallenge.org/challenges/chime8/task1/

# Appendix A. Reproducibility

[[widths:38,62]]
| Artefact | Location |
|---|---|
| Machine-readable manifest (24 rows, checksums, regions, exposure) | `harness/manifest.json` |
| Scoring harness + 25 tests | `harness/` (`.venv-harness/bin/pytest harness/tests`) |
| Reference extraction and audit | `scripts/extract_indic_references.py`, `scripts/audit_references.py` |
| Pilot driver (resumable, 72 units) | `kaggle/run_pilot.py`, `kaggle/diarizbench_models.py` |
| Kaggle notebook | `ayuwat/notebookb62243b3c5` |
| Merge, score, summarise | `scripts/t09/{merge_output,score,summarize}.py` |
| Failure analyses | `scripts/t10/analyze.py` |
| Statistics and figures | `scripts/t11/{statistics,figures}.py` |
| Uncertainty and sensitivity | `scripts/t12/uncertainty.py` |
| Document build | `scripts/t12/build_main.py`, `docs/main.md` |

```text
# rescore everything from saved hypotheses
.venv-harness/bin/python scripts/t09/score.py
.venv-harness/bin/python scripts/t11/statistics.py
.venv-harness/bin/python scripts/t12/uncertainty.py
.venv-harness/bin/python scripts/t11/figures.py
.venv-harness/bin/python scripts/t12/figures_doc.py
.venv-harness/bin/python scripts/t12/build_main.py --author "First Last"
```

Environment pins: `pyannote.audio>=4.0.1`, `torch<2.15`, `torchvision<0.27`,
`numpy>=2.5,<2.6`, `numba>=0.67`, `transformers` (Nemotron), `anuvani_diar==1.0.0`.
Audio is a private Kaggle dataset mounted at
`/kaggle/input/datasets/ayuwat/diarizbench-pilot-audio/`. Full source recordings are not
redistributed; the companion HTML embeds three attributed CC BY 4.0 excerpts totaling 47 seconds.
Exact source intervals and license links are in `submission/AUDIO_SOURCES.md`.

# Appendix B. Per-recording results

[[widths:10,10,12,7,7,8,8,9,9,9]]
| Recording | Language | Condition | Ref spk | c1 spk | Nemo spk | Anu spk | c1 DER | Nemo DER | Anu DER |
|---|---|---|---|---|---|---|---|---|---|
| AMI-01 | English | SDM | 4 | 4 | 4 | 4 | 25.2 | 33.2 | 18.5 |
| AMI-02 | English | SDM | 4 | 4 | 4 | 4 | 23.9 | 31.8 | 19.7 |
| AMI-03 | English | SDM | 4 | 4 | 4 | 5 | 21.8 | 22.7 | 18.0 |
| AMI-04 | English | SDM | 4 | 2 | 4 | 3 | 26.1 | 39.9 | 19.8 |
| AMI-05 | English | SDM | 4 | 3 | 4 | 3 | 29.0 | 34.2 | 20.0 |
| AMI-06 | English | SDM | 4 | 4 | 4 | 5 | 10.0 | 16.0 | 8.8 |
| BN-01 | Bengali | near-field | 8 | 4 | 6 | 6 | 41.2 | 28.5 | 22.8 |
| BN-02 | Bengali | in-the-wild | 6 | 6 | 6 | 6 | 11.4 | 10.3 | 10.1 |
| HI-01 | Hindi | near-field | 9 | 6 | 8 | 8 | 30.0 | 18.5 | 22.0 |
| HI-02 | Hindi | in-the-wild | 5 | 4 | 4 | 4 | 9.1 | 10.2 | 4.6 |
| KN-01 | Kannada | near-field | 7 | 5 | 4 | 4 | 24.7 | 36.9 | 16.7 |
| KN-02 | Kannada | in-the-wild | 7 | 7 | 5 | 7 | 16.7 | 26.8 | 3.4 |
| MR-01 | Marathi | near-field | 6 | 2 | 4 | 4 | 32.7 | 28.6 | 24.0 |
| MR-02 | Marathi | in-the-wild | 5 | 4 | 5 | 4 | 10.2 | 7.4 | 6.2 |
| TA-01 | Tamil | near-field | 5 | 3 | 3 | 4 | 20.6 | 16.9 | 9.8 |
| TA-02 | Tamil | in-the-wild | 3 | 2 | 3 | 3 | 29.6 | 16.8 | 5.7 |
| TE-01 | Telugu | near-field | 8 | 5 | 5 | 7 | 47.7 | 58.1 | 33.7 |
| TE-02 | Telugu | in-the-wild | 8 | 7 | 7 | 9 | 38.6 | 42.0 | 38.4 |
| VC-01 | English | in-the-wild | 13 | 13 | 8 | 13 | 14.4 | 28.2 | 13.3 |
| VC-02 | English | in-the-wild | 8 | 7 | 8 | 8 | 4.8 | 2.1 | 2.7 |
| VC-03 | English | in-the-wild | 8 | 8 | 8 | 8 | 5.4 | 2.1 | 4.5 |
| VC-04 | English | in-the-wild | 8 | 7 | 8 | 7 | 8.0 | 3.6 | 4.5 |
| VC-05 | English | in-the-wild | 6 | 6 | 6 | 5 | 5.6 | 1.9 | 2.1 |
| VC-06 | English | in-the-wild | 6 | 5 | 6 | 5 | 2.2 | 1.1 | 2.1 |
^ Table B1. All 72 scored units. Speaker counts are in-region reference vs hypothesis. DER is zero collar, overlap scored.

# Appendix C. Number provenance

| Claim in this document | Source artefact |
|---|---|
| All DER/JER/count/low-activity/overlap/collar values per recording | `data/runs/results/<system>.json`, `<system>_collar0.25.json` |
| Pooling, bootstrap intervals, pairwise verdicts | `data/runs/results/statistics.json` (`scripts/t11/statistics.py`) |
| Count Wilson intervals, low-activity clustered intervals, 3×3 sensitivity grid, JER intervals | `data/runs/results/uncertainty.json` (`scripts/t12/uncertainty.py`) |
| Original figure sources | `scripts/t12/figures_doc.py`, `scripts/t11/figures.py` |
| Figures 1–7 (final visual design) | `scripts/t14/build_figures.py`; values from saved scores, statistics and uncertainty |
| RTF, load time, per-file ranges | `data/runs/timing/<system>/panel.json`, `panel_summary.json` |
| Failure-case timestamps and counts | `scripts/t10/analyze.py`, `t10_findings.md` |
| Run status, coverage, 72/72 units | `data/runs/state.json`, `summary.json` |
| Manifest, checksums, scoring regions, exposure | `harness/manifest.json` |

**Freeze statement.** Measured scores remain unchanged. Sensitivity/uncertainty additions are saved
in `uncertainty.json`; this revision changes presentation and proposed research, not measured results.

[[page]]

# 14. Reflections

## 14.1 Which design choice are you least sure about, and why?

**The recording-equal headline aggregation.** It gives a short conversation the same weight as a
long meeting, which may not match a buyer's workload. I used it to keep one long meeting from
dominating and published corpus-level and corpus-equal views alongside it. The observed ordering
is stable across those summaries, but its margin changes. I would validate usage-based weights on
held-out customer scenarios before defining a production headline. Zero collar is another trade-off,
which is why the 250 ms sensitivity is published rather than substituted.

## 14.2 Which benchmark you read influenced you most, and how?

**DIHARD III most influenced the methodology:** it made me freeze scoring regions, collar,
overlap handling and speaker-count policy before inference. **Beyond DER most influenced the
product:** it motivated count accuracy and low-activity-speaker recall beside DER, so a missing
participant cannot disappear inside a good average. Indic DiarBench motivated explicit multilingual
slices; SDBench motivated measured speed with a stated workload. Each source changed a concrete
choice rather than only appearing in the references.

## 14.3 What could make your leaderboard misleading, and how did you guard against it?

A single average can hide corpus imbalance, dropped speakers, training exposure, mismatched modes
and uncertain differences. I publish per-corpus results, counting/JER/low-activity diagnostics,
uncertainty, exposure and timing scope; offline and streaming have separate ranks. Failed or
capacity-limited cases remain visible, and non-significance is not called equivalence. The audio
inspector makes examples reviewable. Remaining gaps are the listening-based reference audit,
exact session exposure and immutable inference provenance; displaying these gaps does not remove them.

## 14.4 What would you improve with more time?

First I would close the matched-mode, reference-quality and immutable-version gaps, then expand
datasets and add cpWER/tcpWER with human-checked text, timing and a fixed ASR protocol. I would
build separately scored **speaker separation, speaker similarity/verification, clustering, and
VAD/SAD** tracks, using controlled ablations, held-out identities/conversations and task-appropriate
metrics. The product would gain synchronized separated-stem and speaker-pair listening once those
outputs exist. I would also measure hardware cost and live latency. Sections 13.1–13.2 specify the
research roadmap; none of those additional model evaluations is claimed as completed here.
