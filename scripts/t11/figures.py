"""T11 — figures: DER components, counting error, accuracy-vs-speed.

Generates three publication-ready PNGs into data/runs/figures/ from the saved
results + timing panel.

Usage:
  .venv-harness/bin/python scripts/t11/figures.py
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RESULTS = os.path.join(ROOT, "data", "runs", "results")
FIGDIR = os.path.join(ROOT, "data", "runs", "figures")

SYSTEMS = ["community-1", "nemotron", "anuvani"]
LABELS = {"community-1": "community-1", "nemotron": "Nemotron-3",
          "anuvani": "Anuvani"}
COLORS = {"community-1": "#6c7a89", "nemotron": "#c0392b", "anuvani": "#1f8a5b"}


def load():
    res = {}
    for s in SYSTEMS:
        res[s] = json.load(open(os.path.join(RESULTS, f"{s}.json")))["per_recording"]
    panel = {}
    for s in SYSTEMS:
        p = os.path.join(ROOT, "data", "runs", "timing", s, "panel.json")
        panel[s] = json.load(open(p))
    return res, panel


def weighted_rtf(panel, durations):
    tot_t = sum(r["mean_s"] for r in panel["recordings"].values())
    tot_d = sum(durations[rid] for rid in panel["recordings"])
    return tot_t / tot_d


def main():
    os.makedirs(FIGDIR, exist_ok=True)
    res, panel = load()
    DUR = {"HI-01": 196.6, "TE-02": 300.0, "AMI-01": 1049.4, "AMI-04": 1505.6,
           "VC-01": 300.0, "VC-03": 300.0}

    # ---- Fig 1: DER components (equal-weight over 24) ----
    fig, ax = plt.subplots(figsize=(7.4, 3.9), dpi=150)
    x = np.arange(len(SYSTEMS))
    miss, fa, conf = [], [], []
    for s in SYSTEMS:
        miss.append(np.mean([r["components"]["missed"] for r in res[s]]) * 100)
        fa.append(np.mean([r["components"]["false_alarm"] for r in res[s]]) * 100)
        conf.append(np.mean([r["components"]["confusion"] for r in res[s]]) * 100)
    ax.bar(x, miss, 0.6, label="Missed speech", color="#d9534f")
    ax.bar(x, fa, 0.6, bottom=miss, label="False alarm", color="#f0ad4e")
    ax.bar(x, conf, 0.6, bottom=np.array(miss) + np.array(fa),
           label="Confusion", color="#5bc0de")
    for i, s in enumerate(SYSTEMS):
        tot = miss[i] + fa[i] + conf[i]
        ax.text(i, tot + 0.6, f"{tot:.1f}%", ha="center", va="bottom", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[s] for s in SYSTEMS])
    ax.set_ylabel("DER components (% of reference speech)")
    ax.set_ylim(0, max(m + f + c for m, f, c in zip(miss, fa, conf)) * 1.18)
    ax.set_title("Where the error comes from (zero collar, overlap scored)")
    ax.legend(loc="upper right", frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "der_components.png"))
    plt.close(fig)

    # ---- Fig 2: speaker-count error ----
    fig, ax = plt.subplots(figsize=(7.4, 3.9), dpi=150)
    bias = [np.mean([r["hyp_speaker_count"] - r["ref_speaker_count"] for r in res[s]])
            for s in SYSTEMS]
    mae = [np.mean([abs(r["hyp_speaker_count"] - r["ref_speaker_count"]) for r in res[s]])
           for s in SYSTEMS]
    bars = ax.bar(x, bias, 0.55, color=[COLORS[s] for s in SYSTEMS])
    ax.axhline(0, color="black", lw=0.8)
    for i, s in enumerate(SYSTEMS):
        ax.text(i, bias[i] - 0.04, f"{bias[i]:+.2f}", ha="center", va="top",
                fontweight="bold")
        ax.text(i, bias[i] / 2, f"MAE {mae[i]:.2f}", ha="center", va="center",
                color="white", fontsize=9)
    ax.set_ylim(min(bias) * 1.35, 0.08)
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[s] for s in SYSTEMS])
    ax.set_ylabel("Speaker-count bias (predicted − reference)")
    ax.set_title("Systematic under-counting")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "count_bias.png"))
    plt.close(fig)

    # ---- Fig 3: accuracy vs speed ----
    fig, ax = plt.subplots(figsize=(6.8, 3.9), dpi=150)
    for s in SYSTEMS:
        der = np.mean([r["der"] for r in res[s]]) * 100
        rtf = weighted_rtf(panel[s], DUR)
        ax.scatter(rtf, der, s=260, color=COLORS[s], zorder=3)
        rightmost = rtf == max(weighted_rtf(panel[x], DUR) for x in SYSTEMS)
        ax.annotate(LABELS[s], (rtf, der), textcoords="offset points",
                    xytext=(-10, 8) if rightmost else (8, 8), fontsize=9,
                    ha="right" if rightmost else "left")
    ax.margins(x=0.16, y=0.14)
    ax.set_xlabel("RTF (lower is faster)")
    ax.set_ylabel("DER % (lower is better)")
    ax.set_title("Accuracy vs speed")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "accuracy_speed.png"))
    plt.close(fig)

    print("wrote:")
    for f in ["der_components.png", "count_bias.png", "accuracy_speed.png"]:
        print("  ", os.path.join(FIGDIR, f))


if __name__ == "__main__":
    main()
