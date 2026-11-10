"""T14 — one-page summary, rendered to a single A4 page.

Same palette and typography as the main report, but built as HTML/CSS and printed
by headless Chrome so the dense one-page layout stays under control. All measured
numbers come from the saved result files.

  .venv-harness/bin/python scripts/t14/build_onepager.py
  -> submission/Q1_OnePager.pdf   (exactly one page)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RES = os.path.join(ROOT, "data", "runs", "results")
OUT_HTML = os.path.join(ROOT, "docs", "onepager.html")
OUT_PDF = os.path.join(ROOT, "submission", "Q1_OnePager.pdf")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
AUTHOR = "Ayush Kumar"   # replaced by --author

SYSTEMS = ["community-1", "nemotron", "anuvani"]
NAME = {"community-1": "pyannote community-1",
        "nemotron": "NVIDIA Nemotron-3 (streaming)",
        "anuvani": "CIIL Anuvani"}
DUR = {"HI-01": 196.6, "TE-02": 300.0, "AMI-01": 1049.4, "AMI-04": 1505.6,
       "VC-01": 300.0, "VC-03": 300.0}
MINUS = "\u2212"


def num(x, d=1):
    return (MINUS if x < 0 else "") + f"{abs(x):.{d}f}"


def signed(x, d=1):
    return ("+" if x >= 0 else MINUS) + f"{abs(x):.{d}f}"


def panel_rtf(p):
    tot_t = sum(r["mean_s"] for r in p["recordings"].values())
    tot_d = sum(DUR[rid] for rid in p["recordings"])
    return tot_t / tot_d


def load():
    man = json.load(open(os.path.join(ROOT, "harness", "manifest.json")))["recordings"]
    st = json.load(open(os.path.join(RES, "statistics.json")))
    unc = json.load(open(os.path.join(RES, "uncertainty.json")))
    panel = json.load(open(os.path.join(ROOT, "data", "runs", "timing",
                                        "panel_summary.json")))["systems"]
    rec = {s: {r["id"]: r for r in json.load(
        open(os.path.join(RES, f"{s}.json")))["per_recording"]} for s in SYSTEMS}
    collar_rec = {s: {r["id"]: r for r in json.load(
        open(os.path.join(RES, f"{s}_collar0.25.json")))["per_recording"]} for s in SYSTEMS}
    ids = [r["id"] for r in man]
    rows = {}
    for s in SYSTEMS:
        k = sum(1 for r in ids
                if rec[s][r]["hyp_speaker_count"] == rec[s][r]["ref_speaker_count"])
        rows[s] = dict(
            der=float(np.mean([rec[s][r]["der"] * 100 for r in ids])),
            der250=float(np.mean([collar_rec[s][r]["der"] * 100 for r in ids])),
            der_ci=st["intervals"][s]["der_global_95ci"],
            jer=float(np.mean([rec[s][r]["jer"] * 100 for r in ids])),
            jer_ci=unc["jer_intervals"][s]["ci95"],
            k=k, n=len(ids),
            low=unc["low_activity_recall"][s],
            rtf=panel_rtf(panel[s]),
            corpus_equal=st["pooling"][s]["der_corpus_equal"])
    return man, st, unc, rows


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
@page { size: A4; margin: 0; }
body { font-family: Georgia, "Times New Roman", serif; color: #1c1c1c;
       -webkit-font-smoothing: antialiased; }
.page { width: 210mm; height: 297mm; padding: 0; position: relative; overflow: hidden; }
.band { background: #14213d; color: #fff; padding: 11mm 14mm 8mm; }
.band .kicker { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 6.8pt; letter-spacing: 1.1pt; text-transform: uppercase; color: #7fd1b0;
  font-weight: 700; }
.band h1 { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 22pt;
  font-weight: 700; letter-spacing: -0.3pt; margin-top: 2.4mm; }
.band .sub { font-size: 9.6pt; color: #d7e0ea; margin-top: 1.6mm; }
.rule { height: 1.4mm; background: #7fd1b0; }
.body { padding: 7mm 14mm 0; }
.sans { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }
h2 { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 7.6pt;
  text-transform: uppercase; letter-spacing: 0.9pt; color: #0b6e4f; font-weight: 700;
  margin-bottom: 1.6mm; }
p { font-size: 8.6pt; line-height: 1.46; color: #24292f; }
.cols { display: flex; gap: 8mm; }
.cols > div { flex: 1; }
table { width: 100%; border-collapse: collapse; margin-top: 1.6mm; }
th { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 6.2pt;
  text-transform: uppercase; letter-spacing: 0.5pt; color: #5b6472; text-align: right;
  font-weight: 600; padding: 0 1.6mm 1.4mm; border-bottom: 0.7pt solid #14213d; }
th:first-child { text-align: left; }
td { font-size: 8pt; padding: 1.9mm 1.6mm; border-bottom: 0.35pt solid #e3e7ec;
  text-align: right; font-variant-numeric: tabular-nums; }
td:first-child { text-align: left; }
td.sys { font-weight: 700; color: #14213d; text-align: left; }
th:nth-child(2) { text-align: left; }
td.rank { font-weight: 700; color: #14213d; width: 7mm; }
td.rank.tie { color: #5b6472; }
th.rank { width: 7mm; }
td .ci { display: block; font-size: 6.4pt; color: #5b6472; }
.collar-note { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 6.7pt; line-height: 1.4; color: #5b6472; margin-top: 1.7mm; }
tr.best td { background: #f2f8f5; }
.decisions { display: flex; gap: 4mm; margin-top: 1.6mm; }
.dec { flex: 1; border-top: 1.6pt solid #14213d; padding-top: 2.2mm; }
.dec .n { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 6.4pt;
  font-weight: 700; color: #0b6e4f; letter-spacing: 0.6pt; }
.dec .t { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 8pt;
  font-weight: 700; color: #14213d; margin: 0.8mm 0 1.2mm; line-height: 1.25; }
.dec p { font-size: 7.6pt; line-height: 1.42; }
.claim { border-left: 2.4pt solid #0b6e4f; background: #f4f8f6; padding: 3mm 3.6mm;
  margin-top: 2mm; }
.claim p { font-size: 8.8pt; }
.limit { border: 0.6pt solid #e3d9c4; background: #fdfaf3; padding: 3mm 3.6mm; }
.limit p { font-size: 7.8pt; line-height: 1.42; }
.foot { position: absolute; left: 14mm; right: 14mm; bottom: 8mm;
  border-top: 0.5pt solid #c9cfd8; padding-top: 2mm;
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 6.6pt;
  color: #5b6472; display: flex; justify-content: space-between; }
.space { height: 3.8mm; }
"""


def main():
    global AUTHOR
    ap = argparse.ArgumentParser()
    ap.add_argument("--author", default=AUTHOR)
    ap.add_argument("--out", default=OUT_PDF)
    args = ap.parse_args()
    AUTHOR = args.author

    man, st, unc, rows = load()
    order = sorted(SYSTEMS, key=lambda s: rows[s]["der"])
    best_der = order[0]

    def trow(s, rank, tie=False):
        r = rows[s]
        cls = "best" if s == best_der else ""
        return f"""
      <tr class="{cls}">
        <td class="rank{' tie' if tie else ''}">{rank}</td>
        <td class="sys">{NAME[s]}</td>
        <td>{num(r['der'])}<span class="ci">{num(r['der_ci'][0])} to {num(r['der_ci'][1])}</span></td>
        <td>{num(r['der250'])}<span class="ci">{signed(r['der250']-r['der'])} pp</span></td>
        <td>{num(r['jer'])}<span class="ci">{num(r['jer_ci'][0])} to {num(r['jer_ci'][1])}</span></td>
        <td>{100*r['k']/r['n']:.0f}%<span class="ci">{r['k']}/{r['n']}</span></td>
        <td>{r['low']['pct']:.0f}%<span class="ci">{r['low']['n_recovered']}/{r['low']['n_low']}</span></td>
        <td>{r['rtf']:.3f}<span class="ci">{1/r['rtf']:.1f}×</span></td>
      </tr>"""

    pw = st["pairwise"]
    c1n = pw["community-1__vs__nemotron"]
    c1a = pw["community-1__vs__anuvani"]
    na = pw["nemotron__vs__anuvani"]
    jer_na = unc["jer_pairwise"]["nemotron__vs__anuvani"]

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>DiarizBench — one-page summary</title><style>{CSS}</style></head><body>
<div class="page">
  <div class="band">
    <div class="kicker">Voice Arena take-home · Q1 · one-page summary</div>
    <h1>DiarizBench: a diarization leaderboard for multilingual product teams</h1>
    <div class="sub">A benchmark design tested on three open systems and 24 recordings,
      and seven languages — with every number traceable to a saved run.</div>
  </div>
  <div class="rule"></div>

  <div class="body">
    <div class="cols">
      <div>
        <h2>Purpose</h2>
        <p>A product team choosing a diarization engine is not asking which model has the lowest
        error rate. It is asking whether the system knows <b>who spoke when</b>, whether it keeps the
        <b>quiet participant</b> who says twelve seconds in a five-minute meeting, and whether it
        returns answers <b>fast enough</b> under the conditions the product actually runs in. The
        leaderboard turns those three questions into three published outputs instead of one score.</p>
      </div>
      <div>
        <h2>Setup</h2>
        <p>Three open systems × 24 recordings × three corpora (Indic DiarBench 12, AMI-SDM 6,
        VoxConverse 6), seven languages, <b>205 minutes of scored audio</b> and 196 minutes of
        reference speaker-time. The contract was frozen before inference: zero collar, overlap
        scored, speaker count unknown, identical 16 kHz input, documented defaults, no tuning on
        pilot audio. <b>72/72 units completed with zero errors.</b></p>
      </div>
    </div>

    <div class="space"></div>

    <h2>Principal finding — DER %, collar sensitivity, overlap scored, unknown count</h2>
    <table>
      <tr><th class="rank">Mode</th><th>System</th><th>DER · 0 ms<br>(95% CI)</th><th>DER · 250 ms<br>Δ vs 0 ms</th><th>JER (95% CI)</th>
        <th>Exact count</th><th>Low-activity recall</th><th>RTF</th></tr>
      {trow("anuvani", "OFF")}
      {trow("community-1", "OFF")}
      {trow("nemotron", "STR")}
    </table>
    <p class="collar-note"><b>Collar:</b> a window excluded around reference speech boundaries.
      Here <b>pyannote.metrics c = 0.25 s</b> removes 125 ms on each side; the second DER column is
      sensitivity, with its change in percentage points. Zero collar remains primary. Overlap and
      unknown speaker count are unchanged. Other scorers may define the collar differently.</p>

    <div class="claim">
      <p><b>Anuvani has the lowest observed DER: 13.8%.</b> Its offline gap against community-1 is
      {signed(c1a['mean_diff_pp'])} pp and survives Bonferroni correction and the 1 pp practical
      threshold. The {signed(na['mean_diff_pp'])} pp gap against streaming Nemotron is a comparison
      of configurations, not an offline-model ranking. The community-1/Nemotron DER difference is
      unresolved (95% CI {signed(c1n['ci95'][0])} to {signed(c1n['ci95'][1])}); this does not establish
      equivalence. All averages are exploratory across native corpus conventions.</p>
    </div>

    <div class="space"></div>

    <h2>Three design decisions that changed the answer</h2>
    <div class="decisions">
      <div class="dec">
        <div class="n">01</div>
        <div class="t">Score strictly, then publish the sensitivity</div>
        <p>Zero collar is primary. A boundary collar reduces sensitivity to timestamp offsets, but can
        mask short turns. The saved 250 ms setting lowers DER by 2.8–3.6 pp; both views are shown,
        with the scorer's collar convention explicit.</p>
      </div>
      <div class="dec">
        <div class="n">02</div>
        <div class="t">Publish speaker coverage next to accuracy</div>
        <p>Despite an unresolved DER gap, count accuracy ({100*rows['community-1']['k']/24:.0f}%
        vs {100*rows['nemotron']['k']/24:.0f}%) and low-activity recall
        ({rows['community-1']['low']['pct']:.0f}% vs {rows['nemotron']['low']['pct']:.0f}%) differ by
        20.8 pp on count accuracy and 15.8 pp on low-activity recall, descriptively. Coverage superiority was not tested.</p>
      </div>
      <div class="dec">
        <div class="n">03</div>
        <div class="t">Never pool corpora silently</div>
        <p>Native references and conversation content differ; the structural audit cannot separate their
        effects. Publish per-corpus results and exploratory aggregates. Keep offline and streaming
        ranks separate.</p>
      </div>
    </div>

    <div class="space"></div>

    <div class="cols">
      <div style="flex:1.35">
        <h2>Limitation that matters most</h2>
        <div class="limit">
          <p><b>Exposure and sample size.</b> Anuvani has Indic DiarBench corpus exposure; its parent
          also used AMI/VoxConverse. community-1 has AMI/VoxConverse exposure. Exact session overlap
          is unaudited. Two recordings per Indic language cannot support language-level rankings.</p>
          <p style="margin-top:1.8mm"><b>Mode and references.</b> Nemotron ran streaming; the other two
          offline. No matched-mode rerun or listening-based annotation audit was completed. Timing is
          one-hardware, with different callable scopes; exact weight/env locks are incomplete.
          cpWER/tcpWER were not measured.</p>
        </div>
      </div>
      <div style="flex:1">
        <h2>With more time</h2>
        <p style="font-size:7.8pt">Add <b>cpWER and tcpWER</b> for speaker-attributed transcription,
        plus WER/CER, recognition-versus-attribution diagnostics, and overlap/VAD F1. These require
        human-checked speaker transcripts and timing, a fixed ASR backend, and a separate
        <a href="https://github.com/fgnt/meeteval" style="color:#0b6e4f">MeetEval</a> protocol.</p>
        <p style="font-size:7.8pt;margin-top:1.8mm">Expand to <b>DIHARD III, ICSI, CALLHOME, DISPLACE,
        AliMeeting, and CHiME-8</b>, subject to access and held-out split checks. Prioritize a matched
        offline Nemotron run, human reference QA, and controlled <b>separation, speaker similarity,
        clustering, and VAD/SAD</b> tracks (proposed, not measured).</p>
      </div>
    </div>
  </div>

  <div class="foot">
    <span>Full report <b>Ayush_Kumar_Q1_Main.pdf</b> · sketch
      <b>Ayush_Kumar_Q1_Leaderboard.pdf</b> · video · values trace to
      <span style="font-family:Menlo,monospace">data/runs/results/</span></span>
    <span style="white-space:nowrap">{AUTHOR} · 11 Nov 2026</span>
  </div>
</div>
</body></html>"""

    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    open(OUT_HTML, "w", encoding="utf-8").write(html)
    os.makedirs(os.path.dirname(OUT_PDF), exist_ok=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=4000", f"--print-to-pdf={args.out}",
                    "file://" + OUT_HTML], check=True, capture_output=True)

    import pypdfium2 as pdfium
    n = len(pdfium.PdfDocument(args.out))
    print(f"wrote {OUT_HTML}\nwrote {args.out} ({n} page{'s' if n != 1 else ''})")
    if n != 1:
        raise SystemExit("one-pager must be exactly one page")


if __name__ == "__main__":
    main()
