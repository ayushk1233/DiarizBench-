# T09 — Full pilot runs (checkpointed) + timing panel

## Overview

Three systems (`community-1`, `nemotron`, `anuvani`) × 24 recordings, run as
batches of Kaggle kernel runs. Every batch is checkpointed: results are saved to
disk after each recording and each batch, so an interrupted run resumes from
exactly where it stopped — only unfinished units are re-dispatched.

## Key files

| File | Purpose |
|---|---|
| `scripts/extract_audio.py` | One-time local audio extraction (24 WAV, 16 kHz mono, truncated to scoring region) + checksum back-fill. |
| `scripts/t09/upload_audio_dataset.sh` | Package audio into the Kaggle dataset `ayuwat/diarizbench-pilot-audio`. |
| `kaggle/pilot-runs/kernel_{community1,nemotron,anuvani}.py` | Per-system inference kernels (batch of recordings → RTTM + timing per recording). |
| `kaggle/pilot-runs/kernel_timing.py` | Timing-panel kernel (warm-up + 3 timed reps). |
| `scripts/t09/orchestrate.py` | Checkpointable dispatcher (state → batches → push/poll/download → merge). |
| `scripts/t09/score.py` | Score done recordings against references (locked settings). |
| `scripts/t09/timing_panel.py` | Drive the timing panel (one kernel per system). |
| `harness/loaders.py` | Path resolution for references/hypotheses/timing. |
| `data/runs/state.json` | **The checkpoint.** Per (system, recording): `done`/`failed`/`pending` + timing. |

## The checkpoint contract

- A unit `(system, recording)` is **done** only when its kernel wrote both
  `output/<rid>.rttm` (non-empty) and `output/<rid>.json` (status `ok`), and the
  orchestrator merged them into `data/hypotheses/<system>/<rid>.rttm` +
  `data/runs/timing/<system>/<rid>.json`.
- Kernels write each recording's files **immediately** after it finishes, and
  Kaggle commits `/kaggle/working` even on mid-batch errors — so a crash after N
  of M recordings still checkpoints those N.
- `orchestrate.py` persists `state.json` after every batch. Re-running it (or
  after a Ctrl-C) re-computes pending units and continues.

## Workflow

```bash
# 1. one-time: extract audio locally (resumable)
.venv-extract/bin/python scripts/extract_audio.py

# 2. one-time: upload audio as a Kaggle dataset
scripts/t09/upload_audio_dataset.sh --upload

# 3. smoke-test one recording per system (validates the kernels)
.venv-harness/bin/python scripts/t09/orchestrate.py --only HI-01 --systems community-1,nemotron,anuvani --batch 1

# 4. full pilot (resume-safe; re-run to continue after any failure)
.venv-harness/bin/python scripts/t09/orchestrate.py --systems community-1 --batch 6
.venv-harness/bin/python scripts/t09/orchestrate.py --systems nemotron,anuvani --batch 6

# 5. score what is done so far
.venv-harness/bin/python scripts/t09/score.py --system community-1

# 6. timing panel
.venv-harness/bin/python scripts/t09/timing_panel.py
```

## Conventions locked here

- **RTTM file id = manifest `recording_id`** everywhere (references were
  regenerated to match; hypothesis kernels write this id).
- **Audio filename = manifest `id`** (`HI-01.wav` … `VC-06.wav`).
- **Scoring region** = manifest `scoring_region` (UEM for AMI = full meeting;
  300 s excerpt for in-the-wild Indic and VoxConverse). Audio is truncated to it
  before inference.

## Env fixes baked into every kernel (from T03)

numpy purge+reinstall (`>=2.3`), `torch<2.15` pin (community-1), WAV-not-mp3,
GPU flag `--accelerator NvidiaTeslaT4`.
