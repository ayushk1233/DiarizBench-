"""T10 — failure analyses + annotation audit (reproducible extraction).

Produces the concrete evidence behind the three audio-backed failure cases and
the six-excerpt annotation audit, straight from the saved RTTMs and scores.

Usage:
  .venv-harness/bin/python scripts/t10/analyze.py
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

SYSTEMS = ["community-1", "nemotron", "anuvani"]


def parse_rttm(path):
    turns = []
    for ln in open(path, encoding="utf-8"):
        p = ln.split()
        if p and p[0] == "SPEAKER" and len(p) >= 4:
            turns.append((float(p[3]), float(p[3]) + float(p[4]), p[7]))
    return turns


def speaker_dur(turns):
    d = {}
    for s, e, sp in turns:
        d[sp] = d.get(sp, 0) + max(0.0, e - s)
    return d


def ref_path(rec):
    corpus = rec["corpus"]
    name = rec["id"] if corpus == "indic-diarbench" else rec["recording_id"]
    d = "indic" if corpus == "indic-diarbench" else corpus
    return os.path.join(ROOT, "data", "references", d, f"{name}.rttm")


def hyp_path(system, rid):
    return os.path.join(ROOT, "data", "hypotheses", system, f"{rid}.rttm")


def stats(turns, region):
    s0, e0 = region
    turns = [(s, e, sp) for s, e, sp in turns if e > s0 and s < e0]
    spk = {sp for _, _, sp in turns}
    dur = sum(min(e, e0) - max(s, s0) for s, e, _ in turns)
    b = sorted(set(x for s, e, _ in turns for x in (s, e)))
    ov = 0.0
    for a, c in zip(b[:-1], b[1:]):
        mid = (a + c) / 2
        if sum(1 for s, e, _ in turns if s < mid < e) >= 2:
            ov += c - a
    brief = sum(1 for s, e, _ in turns if e - s < 0.5)
    return len(spk), len(turns), dur, ov, brief


def main():
    m = {r["id"]: r for r in json.load(
        open(os.path.join(ROOT, "harness", "manifest.json")))["recordings"]}
    res = {s: {r["id"]: r for r in json.load(
        open(os.path.join(ROOT, "data", "runs", "results", f"{s}.json")))["per_recording"]}
        for s in SYSTEMS}

    print("=" * 78)
    print("A1. BRIEF-SPEAKER FAILURE — BN-01 (Bengali near-field)")
    print("=" * 78)
    rid = "BN-01"
    ref = parse_rttm(ref_path(m[rid]))
    rd = speaker_dur(ref)
    tot = sum(rd.values())
    for sp in sorted(rd, key=rd.get):
        print(f"  {sp:12} {rd[sp]:7.2f}s  {rd[sp]/tot*100:4.1f}%")
    low = [sp for sp, d in rd.items() if d >= 0.5 and d <= 0.05 * tot]
    print(f"  low-activity speakers: {low}")
    for s in SYSTEMS:
        la = res[s][rid]["low_activity"]
        print(f"  {s:12} recovered {la['n_recovered']}/{la['n_low']}  "
              f"dropped={[la['speakers'][i] for i in range(len(la['speakers'])) if not la['recovered'][i]]}")

    print("\n" + "=" * 78)
    print("A2. OVERLAP FAILURE — TE-02 (Telugu in-the-wild)")
    print("=" * 78)
    rid = "TE-02"
    ref = parse_rttm(ref_path(m[rid]))
    bounds = sorted(set(x for s, e, _ in ref for x in (s, e)))
    best = None
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a < 0.05:
            continue
        mid = (a + b) / 2
        n = sum(1 for s, e, _ in ref if s < mid < e)
        if best is None or n > best[0]:
            best = (n, a, b)
    n, a, b = best
    print(f"  densest overlap: {n} simultaneous speakers over [{a:.1f}-{b:.1f}]")
    for s, e, sp in ref:
        if e > a - 1 and s < b + 1:
            print(f"    ref {sp:14} [{s:.1f}-{e:.1f}]")
    for sys in SYSTEMS:
        hyp = parse_rttm(hyp_path(sys, rid))
        print(f"  {sys} hypothesis in window:")
        for s, e, sp in sorted(hyp):
            if e > a - 1 and s < b + 1:
                print(f"      {sp:14} [{s:.1f}-{e:.1f}]")

    print("\n" + "=" * 78)
    print("A3. MULTILINGUAL / CODE-MIXED — Tamil & Telugu in-the-wild")
    print("=" * 78)
    for rid in ["TA-02", "TE-02"]:
        print(f"  {rid} ({m[rid]['language']} itw):")
        for s in SYSTEMS:
            r = res[s][rid]
            c = r["components"]
            print(f"    {s:12} DER={r['der']*100:5.1f}  miss={c['missed']*100:5.1f}  "
                  f"FA={c['false_alarm']*100:5.1f}  conf={c['confusion']*100:5.1f}  "
                  f"ref={r['ref_speaker_count']}->hyp={r['hyp_speaker_count']}")

    print("\n" + "=" * 78)
    print("B. ANNOTATION AUDIT — reference convention differences")
    print("=" * 78)
    print(f"{'rid':7} {'corpus':9} {'region_s':>8} {'spk':>3} {'seg':>4} "
          f"{'speech%':>8} {'overlap%':>9} {'brief<0.5s':>10}")
    for rid, r in m.items():
        t = parse_rttm(ref_path(r))
        spk, nseg, dur, ov, brief = stats(t, r["scoring_region"])
        reg = r["scoring_region"][1] - r["scoring_region"][0]
        print(f"{rid:7} {r['corpus'][:9]:9} {reg:8.1f} {spk:3} {nseg:4} "
              f"{dur/reg*100:8.1f} {ov/dur*100:9.1f} {brief:10}")


if __name__ == "__main__":
    main()
