# Scoring harness

Implements `manifest → inference → hypothesis RTTM → scoring → tables/figures`
(`plan.md §4`). Scoring settings are locked in `metrics.md` and encoded here:
**zero collar, overlap scored (`skip_overlap=False`), unknown speaker count.**

## Layout

| File | Purpose |
|---|---|
| `rttm.py` | RTTM parse/serialize + `pyannote.core.Annotation` conversion (same-speaker coalescing; cross-speaker overlap preserved). |
| `scoring.py` | Primary scorer: DER, JER, DER components, overlap-only DER, speaker counts, low-activity diagnostic, count metrics. |
| `crosscheck.py` | Wrapper over `nryant/dscore` (DIHARD reference scorer, `third_party/dscore`) for independent verification. |
| `fixtures.py` | 8 hand-computed validation fixtures + invalid-RTTM cases (`plan.md §5`). |
| `test_scoring.py` | Pytest suite: fixtures, invalid rejection, low-activity, overlap, zero-collar sensitivity, cross-check. |
| `pipeline.py` | `run_manifest()`: manifest + ref/hyp loaders → per-recording + aggregate results. |
| `manifest.json` | Machine-readable 24-recording manifest (mirrors `manifest.md`). |

## Environment

- Python 3.11 venv: `.venv-harness`
- Key deps: `pyannote.metrics 4.2.0`, `pyannote.core 6.1.0`, `numpy`, `scipy`,
  `pandas`, `pytest`, plus `third_party/dscore` (`intervaltree`, `tabulate`).

## Validate

```bash
.venv-harness/bin/python -m pytest harness/test_scoring.py -v
```

`25 passed` = the scorer reproduces hand-computed DER/JER for every failure
mode **and** matches the independent DIHARD scorer (`nryant/dscore`, via NIST
`md-eval` Perl, 0 ms collar, overlap included) to within 2% (DER) / 3% (JER).

## Cross-check note (important)

- `pyannote.metrics` reports DER/JER as **fractions (0–1)**.
- `nryant/dscore` reports them in **percent (0–100)**; `crosscheck.py` divides by
  100 so the two are directly comparable.

## Scoring contract implemented

| Setting | Value |
|---|---|
| Collar | 0 ms (headline); 250 ms sensitivity via `score_pair(collar=0.250)` |
| Overlap | scored (`skip_overlap=False`) |
| Speaker count | unknown (never passed to systems) |
| Counts | speakers with positive activity inside the scoring region |
| Low-activity | ≤5% of ref time AND ≥0.5 s; recovered if ≥50% overlaps the optimally-matched hypothesis speaker (`scoring.low_activity`) |
| Aggregation | equal-weight mean over recordings (`pipeline._weighted_mean`) as the base unit; cell-averaging and bootstrap live in the analysis step (T11) |

## Saved evidence and fresh runs

The repository includes non-audio reference RTTMs, hypotheses and score JSON for the completed
pilot. Source audio is not included. Fetch it separately using `docs/DATA.md`, then import
`kaggle/diarizbench_pilot.ipynb` to execute inference on a Kaggle GPU. The main README documents
preparation, Secrets, checkpointing, result collection and rescoring.

The scorer's `collar=0.25` removes a **250 ms total window** around each reference boundary
(125 ms on either side). Do not equate it with a different scorer's ±250 ms convention.
