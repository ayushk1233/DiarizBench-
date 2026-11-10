"""Consolidate scored results into per-corpus / per-language tables.

Reads data/runs/results/<system>.json (+ collar variants) and the manifest, and
prints a compact breakdown: overall (equal-weight), per corpus, and per Indic
language, for DER and JER, at both collars.

Usage:
  .venv-harness/bin/python scripts/t09/summarize.py
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

SYSTEMS = ["community-1", "nemotron", "anuvani"]
RESULTS = os.path.join(ROOT, "data", "runs", "results")


def mean(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else float("nan")


def load(system, collar):
    suffix = f"_collar{collar}" if collar else ""
    p = os.path.join(RESULTS, f"{system}{suffix}.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)["per_recording"]


def main():
    manifest = {r["id"]: r for r in json.load(
        open(os.path.join(ROOT, "harness", "manifest.json")))["recordings"]}

    corpora = ["indic-diarbench", "ami", "voxconverse"]
    langs = sorted({m["language"] for m in manifest.values()})

    for collar in (0.0, 0.25):
        print(f"\n{'='*70}\nCollar {collar} ms\n{'='*70}")
        # build system -> {rid: row}
        data = {s: {r["id"]: r for r in load(s, collar)} for s in SYSTEMS}

        def agg(rows, key):
            return mean([r[key] for r in rows])

        print(f"\n{'system':<12} {'ALL':>7} {'Indic':>7} {'AMI':>7} {'VC':>7} | "
              + "  ".join(f"{l:>6}" for l in langs))
        for s in SYSTEMS:
            rows = list(data[s].values())
            cell = []
            for c in corpora:
                cell.append(agg([r for r in rows if manifest[r['id']]['corpus'] == c], "der"))
            langcell = []
            for l in langs:
                langcell.append(agg([r for r in rows if manifest[r['id']]['language'] == l], "der"))
            print(f"{s:<12} {agg(rows,'der')*100:>6.1f} {cell[0]*100:>7.1f} "
                  f"{cell[1]*100:>7.1f} {cell[2]*100:>7.1f} | "
                  + "  ".join(f"{v*100:>6.1f}" for v in langcell))

        print(f"\n{'system':<12} {'JER ALL':>8} {'JER Indic':>9} {'JER AMI':>8} {'JER VC':>7}")
        for s in SYSTEMS:
            rows = list(data[s].values())
            print(f"{s:<12} {agg(rows,'jer')*100:>7.1f} "
                  f"{agg([r for r in rows if manifest[r['id']]['corpus']=='indic-diarbench'],'jer')*100:>9.1f} "
                  f"{agg([r for r in rows if manifest[r['id']]['corpus']=='ami'],'jer')*100:>8.1f} "
                  f"{agg([r for r in rows if manifest[r['id']]['corpus']=='voxconverse'],'jer')*100:>7.1f}")


if __name__ == "__main__":
    main()
