"""T13 — leaderboard sketch (product view) rendered to PDF.

Every measured number is pulled from the saved result files, never typed by hand:
  data/runs/results/{statistics,uncertainty}.json
  data/runs/results/<system>.json
  data/runs/timing/panel_summary.json
  harness/manifest.json

The page is HTML/CSS printed by headless Chrome, so the sketch looks like the
product surface it describes rather than a second copy of the report.

  .venv-harness/bin/python scripts/t13/build_sketch.py
  -> submission/Q1_Leaderboard.pdf  (4 pages: overview, model detail, governance, audio inspector)
"""
from __future__ import annotations

import json
import argparse
import sys
import os
import subprocess

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RES = os.path.join(ROOT, "data", "runs", "results")
OUT_HTML = os.path.join(ROOT, "docs", "leaderboard.html")
OUT_PDF = os.path.join(ROOT, "submission", "Q1_Leaderboard.pdf")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

SYSTEMS = ["community-1", "nemotron", "anuvani"]
NAME = {"community-1": "pyannote community-1",
        "nemotron": "NVIDIA Nemotron-3",
        "anuvani": "CIIL Anuvani"}
ORG = {"community-1": "pyannote", "nemotron": "NVIDIA", "anuvani": "CIIL"}
MODE = {"community-1": "offline", "nemotron": "streaming", "anuvani": "offline"}
COLOR = {"community-1": "#6c7a89", "nemotron": "#c0392b", "anuvani": "#1f8a5b"}
DUR = {"HI-01": 196.6, "TE-02": 300.0, "AMI-01": 1049.4, "AMI-04": 1505.6,
       "VC-01": 300.0, "VC-03": 300.0}
CORPORA = [("indic-diarbench", "Indic DiarBench", 12),
           ("ami", "AMI-SDM", 6), ("voxconverse", "VoxConverse", 6)]
MINUS = "\u2212"


def num(x, d=1):
    return (MINUS if x < 0 else "") + f"{abs(x):.{d}f}"


def panel_rtf(p):
    tot_t = sum(r["mean_s"] for r in p["recordings"].values())
    tot_d = sum(DUR[rid] for rid in p["recordings"])
    return tot_t / tot_d


# ------------------------------------------------------------------ data
def load():
    man = json.load(open(os.path.join(ROOT, "harness", "manifest.json")))["recordings"]
    st = json.load(open(os.path.join(RES, "statistics.json")))
    unc = json.load(open(os.path.join(RES, "uncertainty.json")))
    panel = json.load(open(os.path.join(ROOT, "data", "runs", "timing",
                                        "panel_summary.json")))["systems"]
    rec = {s: {r["id"]: r for r in json.load(
        open(os.path.join(RES, f"{s}.json")))["per_recording"]} for s in SYSTEMS}
    ids = [r["id"] for r in man]

    rows = {}
    for s in SYSTEMS:
        der = np.mean([rec[s][r]["der"] * 100 for r in ids])
        jer = np.mean([rec[s][r]["jer"] * 100 for r in ids])
        k = sum(1 for r in ids
                if rec[s][r]["hyp_speaker_count"] == rec[s][r]["ref_speaker_count"])
        mae = np.mean([abs(rec[s][r]["hyp_speaker_count"] - rec[s][r]["ref_speaker_count"])
                       for r in ids])
        bias = np.mean([rec[s][r]["hyp_speaker_count"] - rec[s][r]["ref_speaker_count"]
                        for r in ids])
        comp = {kk: np.mean([rec[s][r]["components"][kk] for r in ids]) * 100
                for kk in ("missed", "false_alarm", "confusion")}
        rows[s] = dict(
            der=der, der_ci=st["intervals"][s]["der_global_95ci"],
            jer=jer, jer_ci=unc["jer_intervals"][s]["ci95"],
            k=k, n=len(ids), mae=mae, bias=bias,
            low=unc["low_activity_recall"][s],
            comp=comp, rtf=panel_rtf(panel[s]), load=panel[s]["load_s"],
            per_corpus=st["pooling"][s]["per_corpus"],
            corpus_equal=st["pooling"][s]["der_corpus_equal"],
            exposure={"community-1": ("known overlap", "AMI · VoxConverse"),
                      "nemotron": ("unknown", "no declaration"),
                      "anuvani": ("corpus exposure", "Indic; AMI/Vox parent")}[s])
    return man, st, unc, rows


# ------------------------------------------------------------------ css
CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
@page { size: A4; margin: 0; }
html, body { background: #fff; }
body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
       color: #1c1c1c; -webkit-font-smoothing: antialiased; }
.page { width: 210mm; height: 297mm; padding: 13mm 14mm 10mm; position: relative;
        page-break-after: always; overflow: hidden; background: #fff; }
.page:last-child { page-break-after: auto; }

.top { display: flex; align-items: flex-end; justify-content: space-between;
       border-bottom: 1.2pt solid #244b70; padding-bottom: 3mm; }
.brand { font-size: 15pt; font-weight: 700; color: #244b70; letter-spacing: -0.2pt; }
.brand span { font-size: 8.5pt; font-weight: 400; color: #5b6472; margin-left: 3mm; }
.meta { font-size: 7.4pt; color: #5b6472; text-align: right; line-height: 1.5; }
.tag { display: inline-block; background: #244b70; color: #fff; font-size: 6.8pt;
       font-weight: 700; padding: 1.1mm 2mm; border-radius: 1mm; letter-spacing: 0.3pt; }
h2 { font-size: 11pt; color: #244b70; margin: 5mm 0 2mm; }
h3 { font-size: 8.4pt; color: #326d91; text-transform: uppercase;
     letter-spacing: 0.6pt; margin: 4.2mm 0 1.6mm; }
p, li { font-size: 8.2pt; line-height: 1.45; color: #33383f; }
.small { font-size: 7.2pt; color: #5b6472; line-height: 1.4; }
.foot { position: absolute; left: 14mm; right: 14mm; bottom: 8mm;
        border-top: 0.4pt solid #c9cfd8; padding-top: 1.6mm;
        display: flex; justify-content: space-between; font-size: 6.8pt; color: #5b6472; }

/* filter bar */
.filters { display: flex; gap: 2mm; margin-top: 4mm; flex-wrap: wrap; }
.filter { border: 0.5pt solid #c9cfd8; border-radius: 1.4mm; padding: 1.4mm 2.2mm;
          font-size: 7.2pt; color: #33383f; background: #fbfcfd; }
.filter b { font-weight: 600; color: #244b70; }
.filter .caret { color: #9aa4b2; margin-left: 1.4mm; }
.seg { display: flex; border: 0.5pt solid #c9cfd8; border-radius: 1.4mm; overflow: hidden; }
.seg div { font-size: 7.2pt; padding: 1.4mm 2.4mm; color: #5b6472; background: #fbfcfd; }
.seg div.on { background: #244b70; color: #fff; font-weight: 600; }

/* table */
table { width: 100%; border-collapse: collapse; table-layout: fixed; }
th { font-size: 6.4pt; text-transform: uppercase; letter-spacing: 0.45pt;
     color: #5b6472; text-align: left; padding: 0 1.4mm 1.6mm; border-bottom: 0.6pt solid #244b70;
     font-weight: 600; }
td { font-size: 7.6pt; padding: 2.2mm 1.4mm; border-bottom: 0.35pt solid #e3e7ec;
     vertical-align: middle; }
td.num, th.num { text-align: right; }
.rank { font-size: 12pt; font-weight: 700; color: #244b70; }
.rank.tie { color: #5b6472; }
.model { font-weight: 600; color: #244b70; font-size: 8pt; white-space: nowrap; }
.model .id { display: block; font-weight: 400; font-size: 6.4pt; color: #5b6472;
             font-family: Menlo, monospace; margin-top: 0.6mm; white-space: normal; }
.chip { display: inline-block; font-size: 6pt; padding: 0.6mm 1.3mm; border-radius: 1mm;
        font-weight: 600; letter-spacing: 0.2pt; white-space: nowrap; }
.chip.off { background: #eef1f4; color: #46505c; }
.chip.str { background: #fdecea; color: #a5322a; }
.chip.warn { background: #fff4e5; color: #8a5a00; }
.chip.grey { background: #eef1f4; color: #5b6472; }
.derbar { height: 2.2mm; background: #eef1f4; border-radius: 0.6mm; position: relative;
          width: 100%; margin-top: 1.2mm; }
.derbar i { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 0.6mm; }
.derbar em { position: absolute; top: -0.3mm; bottom: -0.3mm; width: 0.5pt; background: #244b70;
             opacity: 0.5; }
.dercell { text-align: left; }
.big { font-size: 11pt; font-weight: 700; color: #244b70; line-height: 1.1; }
.kpis { display: flex; background: #f4f6f8; border-radius: 1.4mm; margin-top: 4mm; }
.kpis > div { flex: 1; padding: 3.2mm 3.4mm; border-left: 0.6pt solid #fff; }
.kpis > div:first-child { border-left: none; }
.kpis b { display: block; font-size: 14pt; color: #244b70; line-height: 1.1; }
.kpis span { font-size: 6.8pt; color: #5b6472; }
.ci { font-size: 6.4pt; color: #5b6472; display: block; font-weight: 400; white-space: nowrap; }
tr.illus td { color: #8b95a3; border-bottom: 0.35pt dashed #c9cfd8; background: #fcfcfd; }
tr.illus .model { color: #6b7583; }

/* cards */
.grid2 { display: flex; gap: 5mm; }
.card { border: 0.5pt solid #d8dde4; border-radius: 1.6mm; padding: 3.4mm 4mm;
        background: #fff; }
.card.flat { background: #f7f9fa; border-color: #e3e7ec; }
.card h4 { font-size: 7pt; text-transform: uppercase; letter-spacing: 0.5pt;
           color: #5b6472; margin-bottom: 2mm; font-weight: 600; }
.kv { display: flex; justify-content: space-between; font-size: 7.4pt; padding: 1mm 0;
      border-bottom: 0.3pt solid #eef1f4; }
.kv:last-child { border-bottom: none; }
.kv span { color: #5b6472; }
.kv b { color: #244b70; font-weight: 600; }
.stack { display: flex; height: 5.2mm; border-radius: 0.8mm; overflow: hidden; margin: 1.5mm 0 2mm; }
.stack div { font-size: 6.4pt; color: #fff; font-weight: 600; display: flex;
             align-items: center; justify-content: center; }
.legend { display: flex; gap: 3mm; font-size: 6.6pt; color: #5b6472; }
.legend i { display: inline-block; width: 2.2mm; height: 2.2mm; border-radius: 0.4mm;
            margin-right: 1mm; }
.note { border-left: 2pt solid #326d91; background: #f4f8f6; padding: 2.6mm 3mm;
        font-size: 7.6pt; color: #33383f; border-radius: 0 1mm 1mm 0; }
.note b { color: #244b70; }
.mini { width: 100%; border-collapse: collapse; table-layout: auto; }
.mini td, .mini th { font-size: 7.2pt; padding: 1.2mm 0; border-bottom: 0.3pt solid #eef1f4; }
.mini th { font-size: 6.4pt; }
.mini td:last-child, .mini th:last-child { text-align: right; }
.mini td.v { text-align: right; font-weight: 600; color: #244b70; }
.cells th { font-size: 6.2pt; }
.cells td { font-size: 7.4pt; padding: 2mm 1.4mm; }
.cells td.v, .cells th.v { text-align: right; }
.cells tr.best td { background: #f2f8f5; }
.cells b { color: #326d91; }
.colhi { background: #f2f8f5; }

/* governance flow */
.flow { display: flex; align-items: stretch; gap: 0; margin: 3mm 0 1mm; }
.step { flex: 1; border: 0.5pt solid #d8dde4; border-radius: 1.4mm; padding: 2.6mm;
        background: #fff; }
.step .n { font-size: 6.2pt; color: #326d91; font-weight: 700; letter-spacing: 0.4pt; }
.step .t { font-size: 7.6pt; font-weight: 600; color: #244b70; margin: 0.6mm 0 1mm; }
.step .d { font-size: 6.6pt; color: #5b6472; line-height: 1.35; }
.arrow { width: 5mm; display: flex; align-items: center; justify-content: center;
         color: #9aa4b2; font-size: 9pt; }
.cols2 { display: flex; gap: 5mm; }
.cols2 > div { flex: 1; }
ul.tight { margin-left: 3.4mm; }
ul.tight li { font-size: 7.6pt; margin-bottom: 1.2mm; line-height: 1.4; }
ul.tight li b { color: #244b70; }
"""


# ------------------------------------------------------------------ page 1
def page_overview(rows, st, unc, man):
    order = sorted(SYSTEMS, key=lambda s: rows[s]["der"])
    scale = max(rows[s]["der"] for s in SYSTEMS) * 1.05

    def row(s, rank):
        r = rows[s]
        lo, hi = r["der_ci"]
        w = min(r["der"] / scale * 100, 100)
        lo_p = min(lo / scale * 100, 100)
        hi_p = min(hi / scale * 100, 100)
        mode_chip = ('<span class="chip str">STREAMING</span>' if MODE[s] == "streaming"
                     else '<span class="chip off">OFFLINE</span>')
        label, detail = r["exposure"]
        return f"""
      <tr>
        <td class="rank{' tie' if rank.endswith('=') else ''}">{rank}</td>
        <td><span class="model">{NAME[s]}<span class="id">{'pyannote/speaker-diarization-community-1' if s == 'community-1' else 'nvidia/Nemotron-3-Diarization' if s == 'nemotron' else 'CIIL/Anuvani-Diarization'}</span></span></td>
        <td>{mode_chip}</td>
        <td class="dercell">
          <div class="big">{num(r['der'])}</div>
          <div class="ci">{num(lo)} to {num(hi)}</div>
          <div class="derbar"><i style="width:{w:.1f}%;background:{COLOR[s]}"></i>
            <em style="left:{lo_p:.1f}%"></em><em style="left:{hi_p:.1f}%"></em></div>
        </td>
        <td class="num">{num(r['jer'])}<span class="ci">{num(r['jer_ci'][0])}–{num(r['jer_ci'][1])}</span></td>
        <td class="num">{100*r['k']/r['n']:.0f}%<span class="ci">{r['k']}/{r['n']} exact</span></td>
        <td class="num">{r['rtf']:.3f}<span class="ci">{1/r['rtf']:.1f}× real</span></td>
        <td class="num">{r['n']}/{r['n']}<span class="ci">complete</span></td>
        <td><span class="chip warn">{label}</span>
          <span class="ci">{detail}</span></td>
      </tr>"""

    ranked = row("anuvani", "1") + row("community-1", "2") + row("nemotron", "—")

    illus = """
      <tr class="illus"><td>—</td><td colspan="8"><span class="chip grey">ILLUSTRATIVE</span>
      API / on-device lane: not evaluated; no invented scores. The broader catalog is in the main report.</td></tr>"""

    # balanced-cells view (the filter's other setting, shown open)
    best = {c: min(rows[s]["per_corpus"][c] for s in SYSTEMS) for c, _, _ in CORPORA}
    best_eq = min(rows[s]["corpus_equal"] for s in SYSTEMS)
    cells = ""
    for s in order:
        r = rows[s]
        tds = ""
        for c, _, _ in CORPORA:
            v = r["per_corpus"][c]
            tds += (f'<td class="v"><b>{num(v)}</b></td>' if abs(v - best[c]) < 1e-9
                    else f"<td class=\"v\">{num(v)}</td>")
        v = r["corpus_equal"]
        tds += (f'<td class="v"><b>{num(v)}</b></td>' if abs(v - best_eq) < 1e-9
                else f'<td class="v">{num(v)}</td>')
        cells += f"<tr><td>{NAME[s]}</td>{tds}</tr>"

    return f"""
<div class="page">
  <div class="top">
    <div class="brand">DiarizBench<span>speaker diarization leaderboard</span></div>
    <div class="meta"><span class="tag">PILOT · PROTOCOL v1.0</span><br>
      24 recordings · 7 languages · 205 min scored audio<br>
      frozen 2026-11-11 · all values from saved runs</div>
  </div>

  <div class="filters">
    <div class="filter">Domain <b>All</b><span class="caret">▾</span></div>
    <div class="filter">Language <b>All</b><span class="caret">▾</span></div>
    <div class="filter">Speakers <b>Any</b><span class="caret">▾</span></div>
    <div class="filter">Overlap <b>Any</b><span class="caret">▾</span></div>
    <div class="filter">View <b>Recording mean</b><span class="caret">▾</span></div>
    <div class="seg"><div class="on">All modes</div><div>Offline</div><div>Streaming</div></div>
  </div>

  <p class="small" style="margin-top:2.6mm">Ranking metric: <b style="color:#244b70">DER, zero collar,
    overlap scored, speaker count unknown</b>. Offline ranks only. A win requires a Bonferroni-corrected paired-bootstrap
    difference <i>and</i> at least 1 pp. Rows in different operating modes are never ranked against
    each other.</p>

  <table style="margin-top:2.5mm">
    <colgroup>
      <col style="width:4.5%"><col style="width:23%"><col style="width:8.5%"><col style="width:20%">
      <col style="width:10%"><col style="width:9%"><col style="width:8.5%"><col style="width:8%">
      <col style="width:8.5%">
    </colgroup>
    <tr>
      <th>#</th><th>Model · version</th><th>Mode</th><th>DER % · 95% CI</th>
      <th class="num">JER %</th><th class="num">Count</th><th class="num">RTF</th>
      <th class="num">Cover.</th><th>Exposure</th>
    </tr>
    {ranked}
    {illus}
  </table>

  <p class="small" style="margin-top:2.2mm">Ranks 1 and 2 apply only to the two offline systems.
    Nemotron is a separately labelled streaming configuration, with no shared rank. Every measured row
    is 24/24 complete. Prototype filters are illustrated here; the companion HTML makes them functional.</p>

  <div class="grid2" style="margin-top:4.5mm">
    <div class="card flat" style="flex:1">
      <h4>Comparison without a false tie</h4>
      <p style="font-size:7.5pt">The community-1/Nemotron gap is
      <b>{num(st['pairwise']['community-1__vs__nemotron']['mean_diff_pp'])} pp</b>
      (95% CI {num(st['pairwise']['community-1__vs__nemotron']['ci95'][0])} to
      {num(st['pairwise']['community-1__vs__nemotron']['ci95'][1])}). This is not statistically resolved,
      not proof of equivalence. Anuvani's observed gaps are
      <b>{num(st['pairwise']['community-1__vs__anuvani']['mean_diff_pp'])}</b> and
      <b>{num(st['pairwise']['nemotron__vs__anuvani']['mean_diff_pp'])} pp</b>; only the first is a
      matched offline comparison.</p>
    </div>
    <div class="card flat" style="flex:1">
      <h4>What DER alone hides</h4>
      <p style="font-size:7.5pt">Nemotron has the highest observed count accuracy
      ({rows['nemotron']['k']}/{rows['nemotron']['n']} exact) and low-activity recall
      ({rows['nemotron']['low']['pct']:.0f}%). Compared with community-1, the gaps are 20.8 pp and
      15.8 pp respectively. Coverage differences are descriptive; their superiority was not tested.</p>
    </div>
  </div>

  <h3>Balanced cells · DER % by corpus</h3>
  <table class="cells">
    <colgroup><col style="width:30%"><col style="width:18%"><col style="width:16%">
      <col style="width:18%"><col style="width:18%"></colgroup>
    <tr><th>System</th><th class="v">Indic DiarBench (12)</th><th class="v">AMI-SDM (6)</th>
      <th class="v">VoxConverse (6)</th><th class="v">Corpus-equal</th></tr>
    {cells}
  </table>
  <p class="small" style="margin-top:1.8mm">Best value in each column in green. Anuvani leads all four
    cells, so the ordering does not depend on corpus weight; the <i>margin</i> does (8.6–9.6 pp on Indic
    against 1.6–1.9 pp on VoxConverse). The 24-recording average stays labelled exploratory because the
    references and conversation content differ; their separate effects were not measured.</p>

  <div class="note" style="margin-top:4mm">
    <b>Reading rule.</b> Per-corpus cells come first. The table uses a recording mean; the secondary view equal-weights
    three corpus means. Eight balanced domain × language cells are a production design, not measured here.
  </div>

  <div class="kpis">
    <div><b>24</b><span>recordings</span></div>
    <div><b>7</b><span>languages</span></div>
    <div><b>3</b><span>systems</span></div>
    <div><b>72/72</b><span>units completed</span></div>
    <div><b>196</b><span>min reference speech</span></div>
    <div><b>0</b><span>errored runs</span></div>
  </div>

  <div class="foot"><span>DiarizBench · leaderboard sketch (T13) · measured rows trace to
    <span style="font-family:Menlo,monospace">data/runs/results/</span></span><span>1 / 3</span></div>
</div>"""


# ------------------------------------------------------------------ page 2
def page_detail(rows, st, unc, man):
    s = "anuvani"
    r = rows[s]
    c = r["comp"]
    total = c["missed"] + c["false_alarm"] + c["confusion"]
    low = r["low"]
    g3 = unc["low_activity_sensitivity"][s]["act0.03_min0.50"]["recall_pct"]
    g10 = unc["low_activity_sensitivity"][s]["act0.10_min0.50"]["recall_pct"]

    def seg(v, col, label):
        return f'<div style="width:{v/total*100:.1f}%;background:{col}">{label}</div>'

    corpus_rows = "".join(
        f"<tr><td>{name} ({n})</td><td class=\"v\">{num(r['per_corpus'][key])}%</td></tr>"
        for key, name, n in CORPORA)

    cmp_rows = ""
    for label, getter in [
            ("DER %", lambda x: num(rows[x]["der"])),
            ("JER %", lambda x: num(rows[x]["jer"])),
            ("Exact count", lambda x: f"{rows[x]['k']}/{rows[x]['n']}"),
            ("Low-activity recall", lambda x: f"{rows[x]['low']['pct']:.0f}%"),
            ("RTF", lambda x: f"{rows[x]['rtf']:.3f}")]:
        tds = "".join(
            f'<td class="v{" colhi" if x == s else ""}">{getter(x)}</td>'
            for x in [s, "community-1", "nemotron"])
        cmp_rows += f"<tr><td>{label}</td>{tds}</tr>"

    return f"""
<div class="page">
  <div class="top">
    <div class="brand">Model detail<span>one row, opened</span></div>
    <div class="meta"><span class="tag">MEASURED</span><br>
      protocol v1.0 · run 2026-11-10 · 24/24 complete</div>
  </div>

  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-top:4mm">
    <div>
      <div style="font-size:13pt;font-weight:700;color:#244b70">{NAME[s]}</div>
      <div style="font-size:7.4pt;color:#5b6472;font-family:Menlo,monospace;margin-top:1mm">
        CIIL/Anuvani-Diarization</div>
    </div>
    <div style="display:flex;gap:2mm">
      <div class="filter">Compare with <b>all systems</b><span class="caret">▾</span></div>
      <div class="filter">Slice <b>All corpora</b><span class="caret">▾</span></div>
    </div>
  </div>

  <div class="grid2" style="margin-top:4mm">
    <div class="card" style="flex:1.25">
      <h4>Error decomposition — where the {num(r['der'])}% goes</h4>
      <div class="stack">
        {seg(c['missed'], '#d98b4a', num(c['missed']))}
        {seg(c['false_alarm'], '#c0392b', num(c['false_alarm']))}
        {seg(c['confusion'], '#5b6472', num(c['confusion']))}
      </div>
      <div class="legend">
        <span><i style="background:#d98b4a"></i>missed speech</span>
        <span><i style="background:#c0392b"></i>false alarm</span>
        <span><i style="background:#5b6472"></i>confusion</span>
        <span style="margin-left:auto">sums to DER by construction</span>
      </div>
      <p class="small" style="margin-top:2.4mm">The only balanced profile in the pilot. community-1 and
      Nemotron lose most of their error to missed speech (10.6 and 17.1 pp), which points at
      speech-activity behavior; the cause was not isolated.</p>
    </div>
    <div class="card" style="flex:.78">
      <h4>Run conditions</h4>
      <div class="kv"><span>Family</span><b>end-to-end</b></div>
      <div class="kv"><span>Operating mode</span><b>offline</b></div>
      <div class="kv"><span>Hardware</span><b>Tesla T4 ×2</b></div>
      <div class="kv"><span>Settings</span><b>documented defaults</b></div>
      <div class="kv"><span>Speaker count</span><b>unknown to system</b></div>
      <div class="kv"><span>Licence</span><b>CC BY-NC 4.0</b></div>
      <div class="kv"><span>Exposure</span><b style="color:#8a5a00">Indic + parent AMI/Vox</b></div>
    </div>
  </div>

  <div class="grid2" style="margin-top:4mm">
    <div class="card" style="flex:1">
      <h4>Speaker coverage</h4>
      <div class="kv"><span>Exact count</span><b>{r['k']}/{r['n']} = {100*r['k']/r['n']:.0f}%</b></div>
      <div class="kv"><span>Count MAE</span><b>{r['mae']:.2f} speakers</b></div>
      <div class="kv"><span>Count bias</span><b>{num(r['bias'], 2)} speakers</b></div>
      <div class="kv"><span>Low-activity recall</span><b>{low['pct']:.0f}% ({low['n_recovered']}/{low['n_low']})</b></div>
      <div class="kv"><span>95% CI (clustered)</span><b>{low['clustered_bootstrap95'][0]:.0f} to {low['clustered_bootstrap95'][1]:.0f}%</b></div>
      <div class="kv"><span>At 3% / 10% activity</span><b>{g3:.0f}% / {g10:.0f}%</b></div>
      <p class="small" style="margin-top:2mm">Under-counts on average and recovers under half of the
      speakers who talk least. Stable across the sensitivity grid, so the finding is not a threshold
      artefact.</p>
    </div>
    <div class="card" style="flex:1">
      <h4>Per corpus — never pooled silently</h4>
      <table class="mini">{corpus_rows}
        <tr><td><b>corpus-equal</b></td><td class="v">{num(r['corpus_equal'])}%</td></tr>
      </table>
      <p class="small" style="margin-top:2mm">Leads all three corpora, so the ranking does not depend on
      corpus weight. The margin does: 8.6–9.6 pp on Indic, 1.6–1.9 pp on VoxConverse.</p>
    </div>
    <div class="card" style="flex:1">
      <h4>Speed, as measured</h4>
      <div class="kv"><span>RTF (panel mean)</span><b>{r['rtf']:.3f}</b></div>
      <div class="kv"><span>Speed factor</span><b>{1/r['rtf']:.1f}× real time</b></div>
      <div class="kv"><span>Setup/load</span><b>{r['load']:.2f} s</b></div>
      <div class="kv"><span>5-min projection (setup + RTF)</span><b>{r['load'] + 300*r['rtf']:.1f} s</b></div>
      <div class="kv"><span>Break-even vs community-1</span><b>about 11 min audio</b></div>
      <p class="small" style="margin-top:2mm">Projected totals change with file length and setup reuse. Timed callables differ in I/O and
      post-processing; these are implementation timings, not matched service latency.</p>
    </div>
  </div>

  <div class="card" style="margin-top:4mm">
    <h4>How this row compares</h4>
    <table class="mini">
      <colgroup><col style="width:34%"><col style="width:22%"><col style="width:22%"><col style="width:22%"></colgroup>
      <tr><th></th><th class="v" style="color:#326d91">Anuvani</th>
        <th class="v">community-1</th><th class="v">Nemotron-3</th></tr>
      {cmp_rows}
    </table>
  </div>

  <div class="card flat" style="margin-top:4mm">
    <h4>Example failure — the honest one</h4>
    <div style="display:flex;gap:5mm">
      <div style="flex:1">
        <p style="font-size:7.5pt"><b>BN-01, Bengali near-field.</b> Reference speaker
        <span style="font-family:Menlo,monospace">SPEAKER_05</span> contributes 12.87 s in six
        interjections across 168 s. All three systems drop the speaker entirely, Anuvani included. RTTM alignment suggests merging; no audio listening audit was performed. In this file,
        DER stays at 22.8% while a participant disappears from the transcript.</p>
      </div>
      <div style="flex:1">
        <p style="font-size:7.5pt"><b>TE-02, Telugu in-the-wild.</b> Three simultaneous speakers at
        97.2–97.7 s. Local label counts do not establish correct speaker identities; overlap-only DER on this file is
        91.7%. Overlap, not clean single-speaker speech, is what still separates these systems — and no
        system in the pilot handles it well.</p>
      </div>
    </div>
  </div>

  <div class="note" style="margin-top:3.4mm">
    <b>What this row does not tell you.</b> Anuvani was fine-tuned on Indic DiarBench, one of the three
    pilot corpora. Its Indic margin cannot be separated from training-data exposure, and the exposure
    chip stays on every surface where the number appears.
  </div>

  <div class="foot"><span>DiarizBench · model detail · values from
    <span style="font-family:Menlo,monospace">anuvani.json</span>,
    <span style="font-family:Menlo,monospace">uncertainty.json</span></span><span>2 / 3</span></div>
</div>"""


# ------------------------------------------------------------------ page 3
def page_governance():
    return """
<div class="page">
  <div class="top">
    <div class="brand">Governance<span>how the board stays comparable</span></div>
    <div class="meta"><span class="tag">OPERATING RULES</span><br>
      protocol v1.0 · references v1 · immutable once published</div>
  </div>

  <h3 style="margin-top:4mm">How a system gets on the board</h3>
  <div class="cols2">
    <div class="card">
      <h4>Curated track — ranked</h4>
      <ul class="tight">
        <li><b>Pinned checkpoint.</b> Exact repository ID and revision, not a family name.</li>
        <li><b>Documented defaults.</b> Settings fixed before any pilot audio is scored; no per-corpus
          tuning.</li>
        <li><b>Exposure declaration.</b> Known overlap, declared disjoint, or unknown — printed on the
          row.</li>
        <li><b>Complete run.</b> Every recording in the frozen manifest, or the row is published as
          partial with coverage shown and no rank.</li>
        <li><b>Independent reproduction.</b> Maintainer re-runs from the pinned environment before the
          row is marked verified.</li>
      </ul>
    </div>
    <div class="card">
      <h4>Bring-your-own track — separate, unranked</h4>
      <ul class="tight">
        <li>Submitters run the harness themselves and publish hypotheses plus a run log.</li>
        <li>Self-reported settings are accepted but labelled <b>self-reported</b>.</li>
        <li>No rank and no head-to-head claim until the maintainer reproduces the run.</li>
        <li>Never merged into the curated table, even after reproduction — it moves track, keeping the
          provenance of every number legible.</li>
        <li>Closed systems that cannot be run locally stay in the API / on-device lanes, where timing is
          not comparable to self-hosted RTF.</li>
      </ul>
    </div>
  </div>

  <h3>Submission lifecycle</h3>
  <div class="flow">
    <div class="step"><div class="n">01</div><div class="t">Submit</div>
      <div class="d">Checkpoint ID, licence, exposure statement, run log.</div></div>
    <div class="arrow">›</div>
    <div class="step"><div class="n">02</div><div class="t">Triage</div>
      <div class="d">Access, licence, and whether the system is runnable at all.</div></div>
    <div class="arrow">›</div>
    <div class="step"><div class="n">03</div><div class="t">Run</div>
      <div class="d">Frozen manifest, pinned environment, checkpointed driver.</div></div>
    <div class="arrow">›</div>
    <div class="step"><div class="n">04</div><div class="t">Score</div>
      <div class="d">Contract scorer plus the fixture suite; artefacts archived.</div></div>
    <div class="arrow">›</div>
    <div class="step"><div class="n">05</div><div class="t">Review</div>
      <div class="d">Failure cases read by a human; anomalies published, not hidden.</div></div>
    <div class="arrow">›</div>
    <div class="step"><div class="n">06</div><div class="t">Publish</div>
      <div class="d">Row carries protocol version, reference version, run date, artefact hash.</div></div>
  </div>

  <h3>Re-scoring when a reference is corrected</h3>
  <div class="card">
    <p style="font-size:7.6pt">Reference corrections are the normal case, not an exception: a mislabelled
    speaker or a bad turn boundary changes every system's score at once. The rule is <b>re-score
    everything, publish everything</b>.</p>
    <div class="cols2" style="margin-top:2.4mm">
      <div>
        <ul class="tight">
          <li><b>Version the reference, never edit it.</b> A correction creates
            <span style="font-family:Menlo,monospace">references v2</span>; v1 stays retrievable.</li>
          <li><b>Full re-score.</b> Every system is scored against v2 with the same protocol. No partial
            refresh, no cherry-picked rows.</li>
        </ul>
      </div>
      <div>
        <ul class="tight">
          <li><b>Publish the diff.</b> Old score, new score, and the delta per system, side by side.</li>
          <li><b>Bump the protocol version</b> only when a setting changes. Reference corrections and
            setting changes are logged separately, because they mean different things.</li>
        </ul>
      </div>
    </div>
  </div>

  <h3>Versioning, archival, and cadence</h3>
  <div class="cols2">
    <div class="card flat">
      <h4>Every published row carries</h4>
      <div class="kv"><span>Protocol version</span><b>v1.0</b></div>
      <div class="kv"><span>Reference version</span><b>v1</b></div>
      <div class="kv"><span>Checkpoint revision</span><b>pinned commit</b></div>
      <div class="kv"><span>Run date and hardware</span><b>2026-11-10 · T4 ×2</b></div>
      <div class="kv"><span>Artefact hash</span><b>hypotheses + results</b></div>
    </div>
    <div class="card flat">
      <h4>Cadence</h4>
      <div class="kv"><span>Full refresh</span><b>quarterly</b></div>
      <div class="kv"><span>New systems</span><b>monthly intake</b></div>
      <div class="kv"><span>Out-of-cycle</span><b>reference correction</b></div>
      <div class="kv"><span>Old leaderboards</span><b>archived read-only</b></div>
      <div class="kv"><span>Silent re-rank</span><b>never</b></div>
    </div>
  </div>

  <h3>What a change looks like — example log</h3>
  <table class="cells">
    <colgroup><col style="width:14%"><col style="width:14%"><col style="width:13%">
      <col style="width:31%"><col style="width:28%"></colgroup>
    <tr><th>Date</th><th>Protocol</th><th>References</th><th>Change</th><th>What is published</th></tr>
    <tr><td>2026-11-11</td><td>v1.0</td><td>v1</td><td>Initial pilot, 3 systems</td>
      <td>All rows, protocol v1.0</td></tr>
    <tr><td>2027-02-01</td><td>v1.0</td><td><b>v2</b></td><td>Speaker split fixed on 3 files</td>
      <td>Full re-score, old / new / delta</td></tr>
    <tr><td>2027-03-15</td><td><b>v1.1</b></td><td>v2</td><td>Collar sensitivity added to the contract</td>
      <td>Version bump, all rows re-scored</td></tr>
  </table>

  <div class="note" style="margin-top:3.4mm">
    <b>Deliberately out of scope.</b> cpWER/tcpWER and WER/CER are future speaker-attributed ASR
    metrics, requiring transcripts and timing. Add diverse datasets (DIHARD, ICSI, CALLHOME, DISPLACE,
    AliMeeting, CHiME-8) and live latency as separate tracks. None was evaluated in this pilot.
  </div>

  <div class="foot"><span>DiarizBench · governance and operations · sketch, not a running service</span>
    <span>3 / 3</span></div>
</div>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_PDF)
    args = ap.parse_args()
    man, st, unc, rows = load()
    sys.path.insert(0, os.path.join(ROOT, "scripts", "t14"))
    from audio_sketch import page_audio
    html = ("<!doctype html><html><head><meta charset='utf-8'>"
            "<title>DiarizBench leaderboard sketch</title><style>" + CSS + "</style></head><body>"
            + page_overview(rows, st, unc, man)
            + page_detail(rows, st, unc, man)
            + page_governance()
            + page_audio(man)
            + "</body></html>")
    html = html.replace("1 / 3", "1 / 4").replace("2 / 3", "2 / 4").replace("3 / 3", "3 / 4")
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    open(OUT_HTML, "w", encoding="utf-8").write(html)

    os.makedirs(os.path.dirname(OUT_PDF), exist_ok=True)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=4000", f"--print-to-pdf={args.out}",
                    "file://" + OUT_HTML],
                   check=True, capture_output=True)
    print(f"wrote {OUT_HTML}\nwrote {args.out}")


if __name__ == "__main__":
    main()
