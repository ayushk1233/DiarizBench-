# Pinned model stack and environment (T08)

Exact checkpoints, dependency constraints, and input conventions for the three
pilot systems, fixed so T09 runs are reproducible. All confirmed working on
Kaggle (Tesla T4 / CPU) in T03.

## Final review note

This file records repository identifiers and dependency constraints, **not a complete immutable
checkpoint/environment lock**. Run templates load default repository revisions. Historical inference
cannot be guaranteed identical on a future install. Saved RTTMs/scores remain available for rescoring.
Nemotron's actual streaming kernel uses `processor.extract_speaker_dict`, not the preliminary
argmax description below; the separate timing callable returns logits without final segment extraction.
Inputs were clipped to scoring regions before the completed pilot inference (see final report §3.2).

## Shared environment fixes (Kaggle base image)

| # | Problem | Fix |
|---|---|---|
| 1 | Broken mixed numpy (`numpy.ufunc has no __qualname__`) | `rm -rf $SITE_PACKAGES/numpy* && pip install --ignore-installed "numpy>=2.3"` |
| 2 | `pip install pyannote.audio` upgrades torch to broken 2.15.0 | pin `torch<2.15 torchvision<0.27` in the same install |
| 3 | `torchcodec` mis-reads mp3 (truncates to ~10 s) | feed **16 kHz mono WAV/FLAC**, never mp3 |
| 4 | No conda/mamba on Kaggle | n/a for these three (all pip-installable) |

## The three systems

### 1. `pyannote/speaker-diarization-community-1` (modular baseline)
- **Checkpoint:** `pyannote/speaker-diarization-community-1` (HF, gated — token required).
- **Library:** `pyannote.audio >= 4.0.1` (this checkpoint requires the 4.x API).
- **Deps:** `torch<2.15`, `torchvision<0.27`, `numpy>=2.3`.
- **Invocation:** `Pipeline.from_pretrained("pyannote/speaker-diarization-community-1", token=HF_TOKEN).to(device)`, then `pipeline("audio.wav")`.
- **Output → RTTM:** iterate `out.speaker_diarization.itertracks(yield_label=True)` → `(Segment, _, speaker_id)`.
- **Settings:** unknown speaker count (no `num_speakers` hint); regular (overlap-capable) output, not the "exclusive" mode.

### 2. `nvidia/Nemotron-3-Diarization` (EEND Sortformer, streaming)
- **Checkpoint:** `nvidia/Nemotron-3-Diarization` (HF).
- **Library:** `transformers` (`AutoModelForAudioFrameClassification` + `AutoProcessor`).
- **Output:** frame logits `(1, num_frames, 8)` — 8 ordered speaker channels. **Post-processing required** to convert to RTTM: VAD on the activity, then argmax speaker per frame, merge adjacent frames. 8-speaker hard cap.

### 3. `CIIL/Anuvani-Diarization` (EEND, Indic-adapted)
- **Checkpoint:** `CIIL/Anuvani-Diarization` (HF, base model = DiariZen `md-v2`).
- **Library:** `anuvani_diar` wheel `1.0.0` (`cp310-abi3`), fetched from the model repo's `wheels/` dir.
- **Invocation:** `from anuvani_diar import Diarizer; diarize = Diarizer()` (auto-fetches the 307 MB model, runs a GPU self-check).
- **Output:** diarization segments → RTTM (format confirmed at T08/T09 run).

## Input convention (all three)

16 kHz mono WAV; scoring regions applied at scoring time (harness UEM), not at
inference. Speaker count is never passed as a hint.

## Reproducibility artifacts

- `kaggle/pilot-community-1/access_check.py`, `pilot-nemotron/`, `pilot-anuvani/` — T03 smoke-test scripts (prove load + run).
- `kaggle/pilot-runs/run_community1.py` — reusable "download audio → run → write RTTM + timing" template.
