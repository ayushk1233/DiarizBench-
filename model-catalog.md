# Model & service catalog

Twelve systems for the Voice Arena diarization evaluation. Three are self-hosted pilots (the ones we actually run); the rest complete the comparison set the leaderboard covers. All IDs verified against Hugging Face / vendor docs on **2026-11-10**.

## Final review corrections (11 November 2026)

The measured pilot used **streaming Nemotron**, not the offline configuration proposed below.
The final report's §5.4 is the submission catalog. SpeakerKit now has an MIT-licensed Argmax OSS
implementation with standalone diarization and optional transcription; the earlier commercial/ASR-
required description below is superseded. Deepgram now documents versioned `diarize_model` options;
`diarize=true` is the legacy v1 path. Precision-2's API identifier is `precision-2`, not a downloadable
checkpoint inferred from a repository-shaped name. Opaque API backends need configuration and
run-date provenance. No commercial API or SDK was run in the pilot.

Anuvani's parent lists AMI and VoxConverse training corpora. Exact session overlap is unaudited.
Nemotron's capacity is exceeded by HI-01 and VC-01, not VC-02; these were retained and scored.
The model catalog and attempted integrations are not evidence of a broad 12-system evaluation.
Official update sources: [SpeakerKit](https://github.com/argmaxinc/argmax-oss-swift),
[Deepgram](https://developers.deepgram.com/docs/diarization), and
[pyannoteAI](https://docs.pyannote.ai/api-reference/diarize).

## Delivery-mode taxonomy

| Bucket | Meaning | Fairness consequence |
|---|---|---|
| **Self-hosted model** | We download weights and run inference ourselves (GPU). | We control hardware, batching, and timing; RTF is directly comparable. |
| **Cloud API (diarization-native)** | Diarization is the product, via API key. | Wall-clock latency includes network; never share a speed ranking with self-hosted. |
| **Cloud STT API** | Diarization is a feature of a speech-to-text API. | Diarization requires a transcription workload; speaker labels come attached to words. |
| **On-device SDK** | Library embedded in the app, runs locally (often no GPU). | CPU/mobile timing is not comparable to GPU RTF; separate view. |

## Main catalog

| # | System | Org | Type | Delivery | Speaker / overlap caps | License | Needs transcription? |
|---|---|---|---|---|---|---|---|
| 1 | `pyannote/speaker-diarization-community-1` | pyannote | Modular pipeline (VBx clustering) | Self-hosted | No hard speaker cap; overlap-capable | Gated (accept conditions) + HF token; open | No |
| 2 | `BUT-FIT/diarizen-wavlm-large-s80-md-v2` | BUT / FIT | End-to-end (EEND on WavLM-Large, pruned) | Self-hosted | Up to 4 **simultaneous** speakers; cluster max 20 | **CC BY-NC 4.0 (non-commercial)** | No |
| 3 | `CIIL/Anuvani-Diarization` | CIIL | End-to-end (DiariZen + Indic fine-tune) | Self-hosted | 22 Indic langs + English | CC BY-NC 4.0 (weights); code MIT/Apache | No |
| 4 | `nvidia/Nemotron-3-Diarization` | NVIDIA | End-to-end (Sortformer) | Self-hosted | **Max 8 speakers**; overlap-capable | OpenMDW v1.1 (open-weight) | No |
| 5 | `pyannote/speaker-diarization-precision-2` | pyannoteAI | Premium pipeline | Cloud API (native) | No hard cap; exclusive mode | Commercial (API key) | No (optional STT orchestration) |
| 6 | Deepgram Nova-3 (`diarize=true`) | Deepgram | STT + diarization | Cloud STT API | Speaker labels on utterances | Commercial | Yes (STT) |
| 7 | AssemblyAI Universal-2 (`speaker_labels=true`) | AssemblyAI | STT + diarization | Cloud STT API | Speaker labels on utterances | Commercial | Yes (STT) |
| 8 | Amazon Transcribe | AWS | STT + diarization | Cloud STT API | Max speaker count setting | Commercial | Yes (STT) |
| 9 | Google Cloud Speech-to-Text v2 | Google | STT + diarization | Cloud STT API | min/max speaker count setting | Commercial | Yes (STT) |
| 10 | Speechmatics (SaaS) | Speechmatics | STT + diarization | Cloud STT API | Speaker labels on words | Commercial | Yes (STT) |
| 11 | Picovoice Falcon (`pvfalcon`) | Picovoice | On-device batch engine | On-device SDK | **Uncapped** speakers | Commercial (access key) | No (transcription-agnostic) |
| 12 | SpeakerKit (Argmax OSS Swift) | Argmax | Core ML diarization | On-device SDK | Configuration-dependent | MIT code; weights have separate terms | No (ASR optional) |

## Pilot detail (the three we run)

### 1. `pyannote/speaker-diarization-community-1` (pyannote) — modular baseline
- **What it is:** open-source modular pipeline (segmentation + embedding + VBx clustering) in `pyannote.audio` **4.0**. Backports the "exclusive speaker diarization" mode from the commercial `precision-2`.
- **Why in the pilot:** the general open-source baseline; the reference point every other system is compared against.
- **Run:** `Pipeline.from_pretrained(...)`, GPU via `.to(torch.device("cuda"))`. Needs accepted user conditions + HF token.
- **Notes:** supports `num_speakers` / `min_speakers` / `max_speakers`; we run with **unknown** speaker count. Keep the **regular** (overlap-capable) output, not the exclusive mode, for scoring. Feed 16 kHz mono WAV (torchcodec mis-reads mp3).

### 2. `nvidia/Nemotron-3-Diarization` (NVIDIA) — EEND, streaming-capable
- **What it is:** open-weight, 100M-param Sortformer; single checkpoint supports **offline and streaming**, 8 speaker channels ordered by arrival time.
- **Why in the pilot:** the current top of the real Voice Arena leaderboard (14.72% DER); tests the "practicality" question directly via its latency profiles.
- **Run:** NeMo Speech (`SortformerEncLabelModel.from_pretrained(...)`) or 🤗 Transformers, or `NeMo-Speech.cpp`. Needs HF token. Use the **offline 30.4s-buffer** configuration for a fair apples-to-apples comparison.
- **Notes:** **max 8 speakers** — any pilot recording with >8 speakers will silently drop some; we retain and separately flag such recordings. OpenMDW v1.1 (commercial OK).

### 3. `CIIL/Anuvani-Diarization` (CIIL) — EEND, Indic-adapted
- **What it is:** zero-shot diarization adapted to Indian conversations; the only pilot trained for Indian multilingual speech (22 scheduled languages + English).
- **Why in the pilot:** the Indic-native comparison; directly tests whether an Indic-specialized system beats general systems on our Indic slices.
- **Run:** prebuilt wheel (`anuvani_diar`); `Diarizer()` auto-fetches the 307MB model.
- **Notes:** parent of the Anuvani-Diarization paper (16.78% duration-weighted DER on IndicDiarBench, 1,164 recordings). Weights CC BY-NC 4.0; **base model is DiariZen `md-v2`** (this is the Indic-adapted derivative of DiariZen). Confirmed on GPU.

### Evaluated and rejected (not in the pilot)

- **DiariZen `md-v2`** — install blocked: requires Python 3.10 + torch 2.1.1 + vendored pyannote 3.1, and Kaggle has no conda/mamba. Its architecture is still represented via Anuvani (its Indic derivative).
- **3D-Speaker CAM++ (FunASR)** — installable and runs, but its ASR-coupled diarization collapsed a 6+ speaker conversation to 1 speaker; not worth tuning within budget when 3 systems already cover modular + EEND + EEND-Indic.

## Access-check status (2026-11-10)

All pilot IDs and catalog additions verified real by documentation, then smoke-tested live on Kaggle. **Final pilot set (3 systems):** community-1, Nemotron-3, and Anuvani.

| Pilot | HF gate | Kaggle load + run | Result (97.6s sample) |
|---|---|---|---|
| **community-1** (pyannote) | gated (accepted) | ✅ CPU (after env fixes) | 9 speakers / 31 turns; ~7.4s load + ~242s infer (CPU). |
| **Nemotron-3-Diarization** | open | ✅ GPU (`transformers`) | 6 speakers / 29 segments; ~6.7s load + ~4.1s infer. |
| **Anuvani-Diarization** | open | ✅ GPU (pip wheel) | 7 speakers / 26 segments; GPU self-test passed; RTTM saved. |

**Key findings from the live checks:**

- **Speaker-count divergence is real and visible already:** on the same 97.6s sample, Nemotron found 6 speakers, Anuvani 7, and community-1 9. This is the exact "Beyond DER" failure the benchmark must surface (T04/T10).
- **Anuvani is DiariZen + Indic fine-tune** (`base_model` = DiariZen `md-v2`) — the EEND family is represented even without running base DiariZen. Weights CC BY-NC 4.0.
- **Anuvani's README carries the full Indic DiarBench comparison** (18 systems, DER, zero collar / overlap scored / dscore `e02f949`) — matches our locked scoring contract (T04). Reference: Sarvam 16.0, Anuvani 16.78, Precision-2 17.18, DiariZen 17.99, Nemotron 18.38, community-1 21.22.

**Kaggle environment findings (critical for T08/T09):**

1. **Broken mixed numpy** — the image ships Debian `numpy 1.26.4` + a partial pip `numpy 2.1.3` (missing `numpy.ma`/`numpy.typing`), causing `numpy.ufunc has no __qualname__`. **Fix:** `rm -rf $SITE_PACKAGES/numpy* && pip install --ignore-installed "numpy>=2.3"`.
2. **torch gets upgraded to a broken 2.15.0** by `pip install pyannote.audio`. **Fix:** pin `torch<2.15 torchvision<0.27` in the same install.
3. **pyannote's `torchcodec` mis-reads mp3** (truncates 97.6s → 9.93s). **Fix:** feed 16 kHz mono WAV/FLAC, not mp3.
4. **No conda/mamba** on Kaggle (the `mamba` on PATH is an unrelated tool) — ruled out DiariZen's Python 3.10 requirement.
5. **GPU queue can be congested**; CPU is sufficient for load smoke tests (all three run on CPU; GPU confirmed via Nemotron + Anuvani on T4).

## Fair-comparison implications

- The three pilots share one canonical input (16 kHz mono) and unknown speaker count (T04).
- Nemotron has a **hard cap of 8 speakers** — this constrains crowded-slice selection in T06.
- API/on-device/self-hosted results live in **separate timing views**; only the three self-hosted pilots share an RTF ranking.
- Anuvani's non-commercial license (CC BY-NC 4.0) is surfaced, not hidden, because "what a product team can actually ship" is part of the decision.

**ref:** `plan.md §2`, `plan.md §4 (Systems)`, `evidence-table.md`.
