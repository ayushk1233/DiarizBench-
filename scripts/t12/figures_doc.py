"""T12 — document figures not produced by T11 (plotting only, no rescoring).

  per_corpus_der.png  grouped bars, 3 corpora x 3 systems
  indic_language.png  Indic per-language DER heatmap (6 languages x 3 systems)

Usage:
  .venv-harness/bin/python scripts/t12/figures_doc.py
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
FIGDIR = os.path.join(ROOT, "data", "runs", "figures")
STATS = os.path.join(ROOT, "data", "runs", "results", "statistics.json")

SYSTEMS = ["community-1", "nemotron", "anuvani"]
LABELS = {"community-1": "community-1", "nemotron": "Nemotron-3", "anuvani": "Anuvani"}
COLORS = {"community-1": "#6c7a89", "nemotron": "#c0392b", "anuvani": "#1f8a5b"}
CORPORA = [("indic-diarbench", "Indic\n(12)"), ("ami", "AMI-SDM\n(6)"),
           ("voxconverse", "VoxConverse\n(6)")]
LANGS = ["Hindi", "Bengali", "Marathi", "Tamil", "Telugu", "Kannada"]


def main():
    os.makedirs(FIGDIR, exist_ok=True)
    st = json.load(open(STATS))["pooling"]

    # ---- per-corpus DER ----
    fig, ax = plt.subplots(figsize=(7.4, 3.9), dpi=150)
    x = np.arange(len(CORPORA))
    w = 0.26
    for i, s in enumerate(SYSTEMS):
        vals = [st[s]["per_corpus"][c] for c, _ in CORPORA]
        pos = x + (i - 1) * w
        ax.bar(pos, vals, w, color=COLORS[s], label=LABELS[s])
        for p, v in zip(pos, vals):
            ax.text(p, v + 0.4, f"{v:.1f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([lab for _, lab in CORPORA])
    ax.set_ylabel("DER % (zero collar, overlap scored)")
    ax.set_title("Per-corpus DER — native reference conventions, never pooled silently")
    ax.set_ylim(0, max(st[s]["per_corpus"][c] for s in SYSTEMS for c, _ in CORPORA) * 1.22)
    ax.legend(frameon=False, ncol=3, loc="upper center")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "per_corpus_der.png"))
    plt.close(fig)

    # ---- Indic language heatmap ----
    M = np.array([[st[s]["per_language"][l] for s in SYSTEMS] for l in LANGS])
    fig, ax = plt.subplots(figsize=(6.6, 3.9), dpi=150)
    im = ax.imshow(M, cmap="RdYlGn_r", vmin=0, vmax=55, aspect="auto")
    ax.set_xticks(range(len(SYSTEMS)))
    ax.set_xticklabels([LABELS[s] for s in SYSTEMS])
    ax.set_yticks(range(len(LANGS)))
    ax.set_yticklabels(LANGS)
    for i in range(len(LANGS)):
        for j in range(len(SYSTEMS)):
            ax.text(j, i, f"{M[i, j]:.1f}", ha="center", va="center", fontsize=9,
                    color="black")
    ax.set_title("Indic DER by language (2 recordings each — exploratory)")
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
    cb.set_label("DER %")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "indic_language.png"))
    plt.close(fig)

    print("wrote per_corpus_der.png, indic_language.png")


if __name__ == "__main__":
    main()
