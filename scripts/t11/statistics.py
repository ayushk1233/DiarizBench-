"""T11 — pooling + paired bootstrap + practical-significance tests.

Pools DER/JER across the pilot's cells, then runs paired bootstrap resampling
(10,000 resamples, fixed seed) over the 24 independent recordings to put 95%
intervals on each system and on every pairwise difference. A pairwise "win" is
declared only if it is (a) statistically significant after multiple-comparison
adjustment AND (b) at least the predeclared 1 percentage-point DER improvement.

Writes data/runs/results/statistics.json and prints the summary.

Usage:
  .venv-harness/bin/python scripts/t11/statistics.py
"""
from __future__ import annotations

import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RESULTS = os.path.join(ROOT, "data", "runs", "results")
OUT = os.path.join(RESULTS, "statistics.json")

SYSTEMS = ["community-1", "nemotron", "anuvani"]
SEED = 20261111
N_BOOT = 10_000
PRACTICAL_PP = 1.0  # predeclared minimum DER improvement for a meaningful win


def load():
    manifest = {r["id"]: r for r in json.load(
        open(os.path.join(ROOT, "harness", "manifest.json")))["recordings"]}
    rows = {}
    for s in SYSTEMS:
        pr = json.load(open(os.path.join(RESULTS, f"{s}.json")))["per_recording"]
        rows[s] = {r["id"]: r for r in pr}
    order = sorted(manifest)  # stable recording order
    return manifest, rows, order


def pool(manifest, rows, order, system, key, cell):
    """Equal-weight mean of `key` over recordings in `cell` (callable id->bool)."""
    vals = [rows[system][rid][key] * 100 for rid in order if cell(manifest[rid])]
    return float(np.mean(vals)) if vals else None


def bootstrap_diff(a, b, rng):
    """Paired bootstrap distribution of mean(a)-mean(b) over the recordings."""
    n = len(a)
    d = []
    for _ in range(N_BOOT):
        idx = rng.integers(0, n, n)
        d.append(float(np.mean(a[idx] - b[idx])))
    return np.array(d)


def ci(x, level=0.95):
    lo = (1 - level) / 2 * 100
    hi = 100 - lo
    return float(np.percentile(x, lo)), float(np.percentile(x, hi))


def main():
    manifest, rows, order = load()
    rng = np.random.default_rng(SEED)

    # per-recording DER/JER arrays (percent), aligned to `order`
    der = {s: np.array([rows[s][rid]["der"] * 100 for rid in order]) for s in SYSTEMS}
    jer = {s: np.array([rows[s][rid]["jer"] * 100 for rid in order]) for s in SYSTEMS}

    corpora = ["indic-diarbench", "ami", "voxconverse"]
    langs = ["Bengali", "Hindi", "Kannada", "Marathi", "Tamil", "Telugu"]
    conds = ["near_field", "in_the_wild"]

    out = {"seed": SEED, "n_boot": N_BOOT, "practical_pp": PRACTICAL_PP,
           "n_recordings": len(order)}

    # ---- pooling ----
    def cell_corpus(c):
        return lambda r: r["corpus"] == c

    out["pooling"] = {}
    for s in SYSTEMS:
        g = float(np.mean(der[s]))  # global equal-weight
        c = float(np.mean([pool(manifest, rows, order, s, "der", cell_corpus(x))
                           for x in corpora]))  # corpus-equal
        out["pooling"][s] = {"der_global": g, "der_corpus_equal": c}
        out["pooling"][s]["per_corpus"] = {
            x: pool(manifest, rows, order, s, "der", cell_corpus(x)) for x in corpora}
        out["pooling"][s]["per_language"] = {
            l: pool(manifest, rows, order, s, "der", lambda r, l=l: r["language"] == l)
            for l in langs}
        out["pooling"][s]["per_condition"] = {
            c_: pool(manifest, rows, order, s, "der", lambda r, c_=c_: r["condition"] == c_)
            for c_ in conds}

    # ---- bootstrap CIs per system (global + corpus-equal) ----
    out["intervals"] = {}
    for s in SYSTEMS:
        lo, hi = ci(bootstrap_diff(der[s], np.zeros_like(der[s]), rng))
        out["intervals"][s] = {"der_global_95ci": [lo, hi]}

    # ---- pairwise differences (DER), with significance + practical test ----
    pairs = [(a, b) for i, a in enumerate(SYSTEMS) for b in SYSTEMS[i + 1:]]
    out["pairwise"] = {}
    bonf_level = 1 - 0.05 / len(pairs)
    for a, b in pairs:
        d = bootstrap_diff(der[a], der[b], rng)  # mean(a) - mean(b)
        lo95, hi95 = ci(d)
        lo_b, hi_b = ci(d, bonf_level)
        mean_d = float(np.mean(der[a] - der[b]))
        sig95 = not (lo95 <= 0 <= hi95)
        sig_bonf = not (lo_b <= 0 <= hi_b)
        practical = abs(mean_d) >= PRACTICAL_PP
        out["pairwise"][f"{a}__vs__{b}"] = {
            "mean_diff_pp": mean_d, "ci95": [lo95, hi95],
            "ci_bonferroni": [lo_b, hi_b],
            "significant_95": bool(sig95), "significant_bonferroni": bool(sig_bonf),
            "practically_meaningful": bool(practical),
            "winner": a if (mean_d < 0 and sig_bonf and practical) else
                       (b if (mean_d > 0 and sig_bonf and practical) else None),
        }

    json.dump(out, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}\n")

    # ---- human summary ----
    print("=== DER pooling ===")
    print(f"{'system':12} {'global':>7} {'corpus-eq':>9} | " +
          "  ".join(f"{c[:4]:>6}" for c in corpora))
    for s in SYSTEMS:
        p = out["pooling"][s]
        print(f"{s:12} {p['der_global']:6.1f} {p['der_corpus_equal']:8.1f} | " +
              "  ".join(f"{p['per_corpus'][c]:6.1f}" for c in corpora))

    print("\n=== bootstrap 95% CI (global DER) ===")
    for s in SYSTEMS:
        lo, hi = out["intervals"][s]["der_global_95ci"]
        print(f"  {s:12} {out['pooling'][s]['der_global']:5.1f}  [{lo:.1f}, {hi:.1f}]")

    print("\n=== pairwise DER (A vs B: negative = A lower/better) ===")
    for k, v in out["pairwise"].items():
        a, b = k.split("__vs__")
        flags = []
        if v["significant_bonferroni"]:
            flags.append("sig(bonf)")
        if v["practically_meaningful"]:
            flags.append(f">={PRACTICAL_PP:.0f}pp")
        win = f"  => {v['winner']} wins" if v["winner"] else ""
        print(f"  {a} vs {b}: {v['mean_diff_pp']:+5.1f} pp  "
              f"95%CI [{v['ci95'][0]:+.1f},{v['ci95'][1]:+.1f}]  {','.join(flags) or 'n.s.'}{win}")


if __name__ == "__main__":
    main()
