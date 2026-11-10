"""T12 — uncertainty + contract-required sensitivity checks.

Two gaps between `metrics.md` and what T09/T11 published, closed here without
touching any headline number:

1. metrics.md §1: "A metric is published only with its uncertainty." DER/JER
   bootstrap intervals existed (T11); count accuracy and low-activity recall did
   not. Wilson intervals for count accuracy (one independent observation per
   recording) and a recording-clustered bootstrap for low-activity recall
   (speakers are nested inside recordings, so a naive Wilson interval is too
   narrow).

2. metrics.md §2: the low-activity diagnostic must be published as a *curve*
   over {3,5,10}% activity x {0.4,0.5,0.75}s minimum duration, not a single
   number. The 5% / 0.5s / 50% defaults stay the headline.

Also adds paired-bootstrap intervals for JER (companion metric, same treatment
as DER).

Writes data/runs/results/uncertainty.json.

Usage:
  .venv-harness/bin/python scripts/t12/uncertainty.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "harness"))

from loaders import hyp_path, load_manifest, ref_path  # noqa: E402
from rttm import parse_rttm, turns_to_annotation  # noqa: E402
from scoring import low_activity, score_pair  # noqa: E402

RESULTS = os.path.join(ROOT, "data", "runs", "results")
OUT = os.path.join(RESULTS, "uncertainty.json")
SYSTEMS = ["community-1", "nemotron", "anuvani"]
SEED = 20261111
N_BOOT = 10_000


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, (centre - half) * 100), min(100.0, (centre + half) * 100))


def load_annotations(manifest):
    """Return {rid: (ref, hyp, uem)} for each system, parsed once."""
    out = {}
    for system in SYSTEMS:
        per = {}
        for rec in manifest:
            uem = [rec["scoring_region"]]
            ref = turns_to_annotation(parse_rttm(open(ref_path(rec)).read()),
                                      rec["recording_id"], uem=uem)
            hyp = turns_to_annotation(parse_rttm(open(hyp_path(system, rec)).read()),
                                      rec["recording_id"], uem=uem)
            per[rec["id"]] = (ref, hyp, uem)
        out[system] = per
    return out


def main():
    manifest = load_manifest()
    ids = [r["id"] for r in manifest]
    res = {s: {r["id"]: r for r in json.load(
        open(os.path.join(RESULTS, f"{s}.json")))["per_recording"]} for s in SYSTEMS}
    ann = load_annotations(manifest)
    rng = np.random.default_rng(SEED)

    out = {"seed": SEED, "n_boot": N_BOOT}

    # ---------- 1. count accuracy + low-activity recall, with uncertainty ----------
    out["count_accuracy"] = {}
    out["low_activity_recall"] = {}
    for s in SYSTEMS:
        diffs = [res[s][r]["hyp_speaker_count"] - res[s][r]["ref_speaker_count"] for r in ids]
        k = sum(1 for d in diffs if d == 0)
        lo, hi = wilson(k, len(ids))
        out["count_accuracy"][s] = {"k": k, "n": len(ids), "pct": 100 * k / len(ids),
                                    "wilson95": [lo, hi]}

        # clustered bootstrap: resample recordings, pool their low-activity speakers
        n_low = np.array([res[s][r]["low_activity"]["n_low"] for r in ids])
        n_rec = np.array([res[s][r]["low_activity"]["n_recovered"] for r in ids])
        boots = []
        for _ in range(N_BOOT):
            idx = rng.integers(0, len(ids), len(ids))
            den = n_low[idx].sum()
            boots.append(n_rec[idx].sum() / den if den else np.nan)
        boots = np.array([b for b in boots if not np.isnan(b)]) * 100
        out["low_activity_recall"][s] = {
            "n_recovered": int(n_rec.sum()), "n_low": int(n_low.sum()),
            "pct": 100 * n_rec.sum() / n_low.sum(),
            "clustered_bootstrap95": [float(np.percentile(boots, 2.5)),
                                      float(np.percentile(boots, 97.5))],
        }

    # ---------- 2. low-activity threshold sensitivity (contract §2) ----------
    out["low_activity_sensitivity"] = {}
    for s in SYSTEMS:
        grid = {}
        for act in (0.03, 0.05, 0.10):
            for mind in (0.4, 0.5, 0.75):
                nl = nr = 0
                for rid in ids:
                    ref, hyp, uem = ann[s][rid]
                    la = low_activity(ref, hyp, uem, activity_threshold=act,
                                      min_dur=mind, recovery=0.5)
                    nl += la["n_low"]
                    nr += la["n_recovered"]
                grid[f"act{act:.2f}_min{mind:.2f}"] = {
                    "n_low": nl, "n_recovered": nr,
                    "recall_pct": (100 * nr / nl) if nl else None}
        out["low_activity_sensitivity"][s] = grid

    # ---------- 3. JER paired bootstrap ----------
    jer = {s: np.array([res[s][r]["jer"] * 100 for r in ids]) for s in SYSTEMS}
    out["jer_intervals"] = {}
    for s in SYSTEMS:
        boots = np.array([jer[s][rng.integers(0, len(ids), len(ids))].mean()
                          for _ in range(N_BOOT)])
        out["jer_intervals"][s] = {"mean": float(jer[s].mean()),
                                   "ci95": [float(np.percentile(boots, 2.5)),
                                            float(np.percentile(boots, 97.5))]}
    pairs = [(a, b) for i, a in enumerate(SYSTEMS) for b in SYSTEMS[i + 1:]]
    alpha_b = 0.05 / len(pairs)
    lo_p, hi_p = 100 * alpha_b / 2, 100 * (1 - alpha_b / 2)
    out["jer_pairwise"] = {}
    for a, b in pairs:
        d = np.array([(jer[a] - jer[b])[rng.integers(0, len(ids), len(ids))].mean()
                      for _ in range(N_BOOT)])
        out["jer_pairwise"][f"{a}__vs__{b}"] = {
            "mean_diff_pp": float((jer[a] - jer[b]).mean()),
            "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
            "ci_bonferroni": [float(np.percentile(d, lo_p)),
                              float(np.percentile(d, hi_p))],
        }

    json.dump(out, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}\n")

    print("=== count accuracy (Wilson 95%) ===")
    for s in SYSTEMS:
        c = out["count_accuracy"][s]
        print(f"  {s:12} {c['k']:2}/{c['n']} = {c['pct']:4.0f}%  "
              f"[{c['wilson95'][0]:.0f}, {c['wilson95'][1]:.0f}]")

    print("\n=== low-activity recall (clustered bootstrap 95%) ===")
    for s in SYSTEMS:
        c = out["low_activity_recall"][s]
        print(f"  {s:12} {c['n_recovered']:2}/{c['n_low']} = {c['pct']:4.0f}%  "
              f"[{c['clustered_bootstrap95'][0]:.0f}, {c['clustered_bootstrap95'][1]:.0f}]")

    print("\n=== low-activity sensitivity: recall % (rows=threshold, cols=min dur) ===")
    print(f"  {'system':12} " + "".join(f"{m:>8}" for m in ("0.40s", "0.50s", "0.75s")))
    for s in SYSTEMS:
        for act in (0.03, 0.05, 0.10):
            row = []
            for mind in (0.4, 0.5, 0.75):
                g = out["low_activity_sensitivity"][s][f"act{act:.2f}_min{mind:.2f}"]
                row.append(f"{g['recall_pct']:5.0f}%({g['n_low']:2})")
            print(f"  {s:12} " + "".join(f"{v:>8}" for v in row) + f"   act<={act:.0%}")

    print("\n=== JER mean [95% CI] and pairwise ===")
    for s in SYSTEMS:
        j = out["jer_intervals"][s]
        print(f"  {s:12} {j['mean']:5.1f}  [{j['ci95'][0]:.1f}, {j['ci95'][1]:.1f}]")
    for k, v in out["jer_pairwise"].items():
        print(f"  {k}: {v['mean_diff_pp']:+5.1f} pp  "
              f"[{v['ci95'][0]:+.1f}, {v['ci95'][1]:+.1f}]")


if __name__ == "__main__":
    main()
