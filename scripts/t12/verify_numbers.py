"""T12 — assert every headline number in the submission PDF matches its saved result.

The document claims (Appendix C) that each published number traces to a saved
artefact. This script checks that claim mechanically:

  1. Recompute the headline quantities from the per-recording result files,
     the manifest, and the timing panel.
  2. Assert the recomputed values agree with `statistics.json` /
     `uncertainty.json` (internal consistency of the artefacts themselves).
  3. Assert the formatted number appears in the rendered PDF text.

Anything that fails prints FAIL and the script exits non-zero. Run it after every
rebuild:

  .venv-harness/bin/python scripts/t12/verify_numbers.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import numpy as np
import pypdfium2 as pdfium

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RES = os.path.join(ROOT, "data", "runs", "results")
def _resolve(kind):
    """Prefer the submission-named file, fall back to the working name."""
    sub = os.path.join(ROOT, "submission")
    hits = sorted(glob.glob(os.path.join(sub, f"*_Q1_{kind}.pdf")))
    if hits:
        return hits[0]
    return os.path.join(sub, f"Q1_{kind}.pdf")


PDF = _resolve("Main")
SKETCH = _resolve("Leaderboard")

SYSTEMS = ["community-1", "nemotron", "anuvani"]
LABEL = {"community-1": "community-1", "nemotron": "Nemotron-3", "anuvani": "Anuvani"}
SHORT = {"community-1": "community-1", "nemotron": "Nemotron", "anuvani": "Anuvani"}

MINUS = "\u2212"


# ------------------------------------------------------------------ formatting
def num(x: float, d: int = 1) -> str:
    """Format with the document's typographic minus."""
    s = f"{abs(x):.{d}f}"
    return (MINUS if x < 0 else "") + s


def signed(x: float, d: int = 1) -> str:
    """Explicit sign, as used in the pairwise tables."""
    return ("+" if x >= 0 else MINUS) + f"{abs(x):.{d}f}"


def ci(lo: float, hi: float, d: int = 1) -> str:
    return f"[{signed(lo, d)}, {signed(hi, d)}]"


# ------------------------------------------------------------------ loading
def load():
    man = json.load(open(os.path.join(ROOT, "harness", "manifest.json")))["recordings"]
    stats = json.load(open(os.path.join(RES, "statistics.json")))
    unc = json.load(open(os.path.join(RES, "uncertainty.json")))
    panel = json.load(open(os.path.join(ROOT, "data", "runs", "timing",
                                        "panel_summary.json")))["systems"]
    rec = {}
    col = {}
    for s in SYSTEMS:
        rec[s] = {r["id"]: r for r in json.load(
            open(os.path.join(RES, f"{s}.json")))["per_recording"]}
        col[s] = {r["id"]: r for r in json.load(
            open(os.path.join(RES, f"{s}_collar0.25.json")))["per_recording"]}
    return man, stats, unc, panel, rec, col


def panel_rtf(panel, durations):
    tot_t = sum(r["mean_s"] for r in panel["recordings"].values())
    tot_d = sum(durations[rid] for rid in panel["recordings"])
    return tot_t / tot_d


DUR = {"HI-01": 196.6, "TE-02": 300.0, "AMI-01": 1049.4, "AMI-04": 1505.6,
       "VC-01": 300.0, "VC-03": 300.0}


# ------------------------------------------------------------------ PDF text
def pdf_text(path: str) -> str:
    doc = pdfium.PdfDocument(path)
    raw = "\n".join(p.get_textpage().get_text_range() for p in doc)
    raw = raw.replace(MINUS, "-").replace("\u2013", "-")
    return re.sub(r"\s+", " ", raw)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace(MINUS, "-").replace("\u2013", "-")).strip()


def verify_sketch(man, st, unc, rows):
    """The sketch is generated from the same artefacts; check the rendered text too."""
    text = pdf_text(SKETCH)
    claims = []
    for s in SYSTEMS:
        r = rows[s]
        claims += [
            (f"sketch {s} DER", num(r["der"])),
            (f"sketch {s} DER CI", f"{num(r['der_ci'][0])} to {num(r['der_ci'][1])}"),
            (f"sketch {s} JER", num(r["jer"])),
            (f"sketch {s} RTF", f"{r['rtf']:.3f}"),
            (f"sketch {s} exact count", f"{r['k']}/{r['n']}"),
            (f"sketch {s} low-activity recall", f"{r['low']['pct']:.0f}%"),
        ]
        for c, _, _ in [("indic-diarbench", "", 0), ("ami", "", 0), ("voxconverse", "", 0)]:
            claims.append((f"sketch {s} {c} DER", num(r["per_corpus"][c])))
        claims.append((f"sketch {s} corpus-equal", num(r["corpus_equal"])))
    claims += [
        ("sketch pairwise c1 vs nemo", num(st["pairwise"]["community-1__vs__nemotron"]["mean_diff_pp"]) + " pp"),
        ("sketch pairwise c1 vs anu", num(st["pairwise"]["community-1__vs__anuvani"]["mean_diff_pp"])),
        ("sketch pairwise nemo vs anu", num(st["pairwise"]["nemotron__vs__anuvani"]["mean_diff_pp"]) + " pp"),
        ("sketch recordings", f"{len(man)} recordings"),
    ]
    failed = [(w, e) for w, e in claims if norm(e) not in text]
    print(f"\nSketch: {len(claims)-len(failed)}/{len(claims)} claims verified in Q1_Leaderboard.pdf")
    for w, e in failed:
        print(f"  - {w}: expected {e!r}")
    return failed


def main():
    man, stats, unc, panel, rec, col = load()
    ids = [r["id"] for r in man]
    text = pdf_text(PDF)
    claims: list[tuple[str, str, str]] = []   # (what, expected text, source)

    def add(what, expected, source):
        claims.append((what, norm(expected), source))

    # ---------------- internal consistency: artefacts vs recomputation ----------
    problems = []

    def agree(name, a, b, tol=1e-9):
        if abs(a - b) > tol:
            problems.append(f"{name}: artefact {a:.6f} != recomputed {b:.6f}")

    der = {s: np.array([rec[s][r]["der"] * 100 for r in ids]) for s in SYSTEMS}
    jer = {s: np.array([rec[s][r]["jer"] * 100 for r in ids]) for s in SYSTEMS}
    der250 = {s: np.array([col[s][r]["der"] * 100 for r in ids]) for s in SYSTEMS}
    for s in SYSTEMS:
        agree(f"DER {s}", stats["pooling"][s]["der_global"], float(der[s].mean()))
        agree(f"JER {s}", unc["jer_intervals"][s]["mean"], float(jer[s].mean()))

    # ---------------- Table 1: global accuracy row per system ------------------
    for s in SYSTEMS:
        d_lo, d_hi = stats["intervals"][s]["der_global_95ci"]
        j_lo, j_hi = unc["jer_intervals"][s]["ci95"]
        k = sum(1 for r in ids if rec[s][r]["hyp_speaker_count"] == rec[s][r]["ref_speaker_count"])
        c_lo, c_hi = unc["count_accuracy"][s]["wilson95"]
        la = unc["low_activity_recall"][s]
        l_lo, l_hi = la["clustered_bootstrap95"]
        bias = float(np.mean([rec[s][r]["hyp_speaker_count"] - rec[s][r]["ref_speaker_count"]
                              for r in ids]))
        rtf = panel_rtf(panel[s], DUR)

        add(f"{s} DER + 95% CI",
            f"{num(der[s].mean())} [{num(d_lo)}, {num(d_hi)}]",
            "statistics.json › pooling/intervals")
        add(f"{s} JER + 95% CI",
            f"{num(jer[s].mean())} [{num(j_lo)}, {num(j_hi)}]",
            "uncertainty.json › jer_intervals")
        add(f"{s} exact-count fraction",
            f"{k}/{len(ids)}",
            "uncertainty.json › count_accuracy")
        add(f"{s} exact-count accuracy + Wilson CI",
            f"{100*k/len(ids):.0f}% [{c_lo:.0f}, {c_hi:.0f}]",
            "uncertainty.json › count_accuracy")
        add(f"{s} count bias",
            f"{num(bias, 2)}",
            f"{s}.json › per_recording")
        add(f"{s} low-activity fraction",
            f"{la['n_recovered']}/{la['n_low']}",
            "uncertainty.json › low_activity_recall")
        add(f"{s} low-activity recall + clustered CI",
            f"{la['pct']:.0f}% [{l_lo:.0f}, {l_hi:.0f}]",
            "uncertainty.json › low_activity_recall")
        add(f"{s} DER at 250 ms collar",
            f"{num(der250[s].mean())}",
            f"{s}_collar0.25.json")
        add(f"{s} RTF (duration-weighted panel)",
            f"{rtf:.3f}",
            "timing/panel_summary.json")
        add(f"{s} model load time",
            f"{panel[s]['load_s']:.2f}",
            "timing/panel_summary.json")

    # Table 1 renders as one row per system; assert the concatenated row too.
    for s in SYSTEMS:
        d_lo, d_hi = stats["intervals"][s]["der_global_95ci"]
        j_lo, j_hi = unc["jer_intervals"][s]["ci95"]
        k = sum(1 for r in ids if rec[s][r]["hyp_speaker_count"] == rec[s][r]["ref_speaker_count"])
        c_lo, c_hi = unc["count_accuracy"][s]["wilson95"]
        la = unc["low_activity_recall"][s]
        l_lo, l_hi = la["clustered_bootstrap95"]
        bias = float(np.mean([rec[s][r]["hyp_speaker_count"] - rec[s][r]["ref_speaker_count"]
                              for r in ids]))
        add(f"Table 1 row: {s}",
            f"{LABEL[s]} {num(der[s].mean())} [{num(d_lo)}, {num(d_hi)}] "
            f"{num(jer[s].mean())} [{num(j_lo)}, {num(j_hi)}] "
            f"{100*k/len(ids):.0f}% [{c_lo:.0f}, {c_hi:.0f}] {num(bias, 2)} "
            f"{la['pct']:.0f}% [{l_lo:.0f}, {l_hi:.0f}] "
            f"{num(der250[s].mean())} {panel_rtf(panel[s], DUR):.3f}",
            "Table 1")

    # ---------------- Table 2: per-corpus DER ---------------------------------
    corpora = [("indic-diarbench", "Indic"), ("ami", "AMI-SDM"), ("voxconverse", "VoxConverse")]
    for s in SYSTEMS:
        row = [stats["pooling"][s]["per_corpus"][c] for c, _ in corpora]
        add(f"Table 2 row: {s}",
            f"{LABEL[s]} {num(row[0])} {num(row[1])} {num(row[2])} "
            f"{num(stats['pooling'][s]['der_corpus_equal'])}",
            "statistics.json › per_corpus / der_corpus_equal")

    # ---------------- Table 3: count behaviour --------------------------------
    for s in SYSTEMS:
        k = sum(1 for r in ids if rec[s][r]["hyp_speaker_count"] == rec[s][r]["ref_speaker_count"])
        mae = float(np.mean([abs(rec[s][r]["hyp_speaker_count"] - rec[s][r]["ref_speaker_count"])
                             for r in ids]))
        bias = float(np.mean([rec[s][r]["hyp_speaker_count"] - rec[s][r]["ref_speaker_count"]
                              for r in ids]))
        per = {}
        for c, _ in corpora:
            sub = [r for r in man if r["corpus"] == c]
            per[c] = float(np.mean([abs(rec[s][r["id"]]["hyp_speaker_count"]
                                        - rec[s][r["id"]]["ref_speaker_count"]) for r in sub]))
        add(f"Table 3 row: {s}",
            f"{LABEL[s]} {k}/{len(ids)} {mae:.2f} {num(bias, 2)} "
            f"{per['indic-diarbench']:.2f} {per['ami']:.2f} {per['voxconverse']:.2f}",
            "Table 3")

    # ---------------- Table 4: low-activity sensitivity -----------------------
    for s in SYSTEMS:
        g3 = unc["low_activity_sensitivity"][s]["act0.03_min0.50"]
        g10 = unc["low_activity_sensitivity"][s]["act0.10_min0.50"]
        add(f"Table 4 row: {s}",
            f"{LABEL[s]} {unc['low_activity_recall'][s]['n_recovered']}/"
            f"{unc['low_activity_recall'][s]['n_low']} "
            f"{unc['low_activity_recall'][s]['pct']:.0f}% "
            f"[{unc['low_activity_recall'][s]['clustered_bootstrap95'][0]:.0f}, "
            f"{unc['low_activity_recall'][s]['clustered_bootstrap95'][1]:.0f}] "
            f"{g3['recall_pct']:.0f}% / {g10['recall_pct']:.0f}%",
            "Table 4 / uncertainty.json › low_activity_sensitivity")

    # ---------------- Table 5: collar sensitivity -----------------------------
    for s in SYSTEMS:
        add(f"Table 5 row: {s}",
            f"{LABEL[s]} {num(der[s].mean())} {num(der250[s].mean())} "
            f"{num(der250[s].mean() - der[s].mean())}",
            "Table 5")

    # ---------------- Table 6: speed ------------------------------------------
    for s in SYSTEMS:
        rtf = panel_rtf(panel[s], DUR)
        add(f"Table 6 row: {s}",
            f"{LABEL[s]} {panel[s]['load_s']:.2f} {rtf:.3f} {1/rtf:.1f}×",
            "Table 6 / timing/panel_summary.json")

    # ---------------- Tables 7 and 8: pairwise verdicts ----------------------
    for key, pw in stats["pairwise"].items():
        a, b = key.split("__vs__")
        add(f"Table 7 row: {a} vs {b}",
            f"{SHORT[a]} vs {SHORT[b]} {signed(pw['mean_diff_pp'])} "
            f"{ci(*pw['ci95'])} {ci(*pw['ci_bonferroni'])}",
            "statistics.json › pairwise")
    for key, pw in unc["jer_pairwise"].items():
        a, b = key.split("__vs__")
        add(f"Table 8 row: {a} vs {b}",
            f"{SHORT[a]} vs {SHORT[b]} {signed(pw['mean_diff_pp'])} "
            f"{ci(*pw['ci95'])} {ci(*pw['ci_bonferroni'])}",
            "uncertainty.json › jer_pairwise")

    # ---------------- prose claims -------------------------------------------
    # error components
    comp = {s: {k: float(np.mean([rec[s][r]["components"][k] for r in ids]) * 100)
                for k in ("missed", "false_alarm", "confusion")} for s in SYSTEMS}
    c = comp["anuvani"]
    add("Anuvani DER components",
        f"{num(der['anuvani'].mean())}% is {num(c['missed'])} + "
        f"{num(c['false_alarm'])} + {num(c['confusion'])}",
        "per-recording components")

    # overlap-only DER (mean over files with overlap)
    for s in SYSTEMS:
        vals = [rec[s][r]["overlap_der"] * 100 for r in ids
                if rec[s][r]["overlap_der"] is not None]
        add(f"{s} overlap-only DER",
            f"{num(float(np.mean(vals)))}% ({SHORT[s]})",
            "per-recording overlap_der")

    # dataset facts
    regions = sum(r["scoring_region"][1] - r["scoring_region"][0] for r in man) / 60
    add("scored audio", f"{regions:.0f} minutes of scored audio", "manifest.json")
    add("recording count", f"{len(man)} recordings", "manifest.json")
    add("unit count", f"{len(man) * len(SYSTEMS)}/{len(man) * len(SYSTEMS)} units",
        "state.json")

    # speed: end-to-end wall clock on a 5-minute file, and break-even
    for s in SYSTEMS:
        rtf = panel_rtf(panel[s], DUR)
        add(f"{s} end-to-end 5-minute wall clock",
            f"{panel[s]['load_s'] + 300 * rtf:.1f} s",
            "derived: load + 300 s x RTF")
    t_be = ((panel["anuvani"]["load_s"] - panel["community-1"]["load_s"])
            / (panel_rtf(panel["community-1"], DUR) - panel_rtf(panel["anuvani"], DUR)))
    add("break-even audio length", f"{t_be/60:.0f} minutes of audio",
        "derived: load difference / RTF difference")

    # ---------------- run the checks -----------------------------------------
    failed = []
    print(f"{'claim':52} {'source':46} result")
    print("-" * 112)
    for what, expected, source in claims:
        ok = expected in text
        if not ok:
            failed.append((what, expected))
        print(f"{what[:52]:52} {source[:46]:46} {'PASS' if ok else 'FAIL'}")

    print()
    if problems:
        print("ARTEFACT INCONSISTENCIES")
        for p in problems:
            print("  ", p)
    else:
        print(f"Artefact consistency: {len(SYSTEMS)*2} recomputations match "
              f"statistics.json / uncertainty.json")

    print(f"\n{len(claims)-len(failed)}/{len(claims)} document claims verified "
          f"against saved results")
    failed_sketch = verify_sketch(man, stats, unc,
                                 {s: dict(
                                     der=der[s].mean(),
                                     der_ci=stats["intervals"][s]["der_global_95ci"],
                                     jer=jer[s].mean(),
                                     k=sum(1 for r in ids if rec[s][r]["hyp_speaker_count"]
                                           == rec[s][r]["ref_speaker_count"]),
                                     n=len(ids),
                                     low=unc["low_activity_recall"][s],
                                     rtf=panel_rtf(panel[s], DUR),
                                     per_corpus=stats["pooling"][s]["per_corpus"],
                                     corpus_equal=stats["pooling"][s]["der_corpus_equal"])
                                  for s in SYSTEMS})
    if failed or failed_sketch:
        if failed:
            print("\nMissing from the main PDF:")
            for what, expected in failed:
                print(f"  - {what}: expected {expected!r}")
        return 1
    if problems:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
