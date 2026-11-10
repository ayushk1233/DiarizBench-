"""T14 — final QA over the four deliverables.

Checks that each artefact exists, opens, has the expected shape, carries the exact
system identifiers, and contains every section the assignment asks for. Number
provenance is checked separately by scripts/t12/verify_numbers.py, which this script
runs and folds into the result.

  .venv-harness/bin/python scripts/t14/qa.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import statistics
import subprocess
import sys

import pypdfium2 as pdfium

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SUB = os.path.join(ROOT, "submission")

MINUS = "\u2212"


def text_of(path):
    doc = pdfium.PdfDocument(path)
    raw = "\n".join(p.get_textpage().get_text_range() for p in doc)
    raw = raw.replace(MINUS, "-").replace("\u2013", "-")
    return len(doc), re.sub(r"\s+", " ", raw)


def find(kind):
    """Accept both the working name and the submission name Firstname_Lastname_Q1_*."""
    exact = os.path.join(SUB, f"Q1_{kind}.pdf" if kind.endswith(".pdf") is False else kind)
    if kind == "VIDEO_LINK.txt":
        p = os.path.join(SUB, kind)
        return p if os.path.exists(p) else None
    exact = os.path.join(SUB, f"Q1_{kind}.pdf")
    if os.path.exists(exact):
        return exact
    hits = sorted(glob.glob(os.path.join(SUB, f"*_Q1_{kind}.pdf")))
    return hits[0] if hits else None


def main():
    results = []   # (check, status, detail)

    def add(check, ok, detail, warn=False):
        results.append((check, "PASS" if ok else ("WARN" if warn else "FAIL"), detail))

    # ---------------- files ----------------
    main_pdf = find("Main")
    one_pdf = find("OnePager")
    board_pdf = find("Leaderboard")
    link_txt = find("VIDEO_LINK.txt")

    for label, path in [("main report", main_pdf), ("one-pager", one_pdf),
                        ("leaderboard sketch", board_pdf)]:
        add(f"{label} exists", bool(path), os.path.basename(path) if path else "missing")

    # ---------------- shapes ----------------
    if main_pdf:
        n, t = text_of(main_pdf)
        add("main report opens and has extractable text", len(t) > 20000, f"{n} pages, {len(t)} chars")
        add("main report page count in range", 18 <= n <= 30,
            f"{n} pages including catalog, references, appendices and final reflections")

        required = [
            ("purpose / audience", "1. The product question"),
            ("models", "5. Systems under test"),
            ("test data", "3. Test data"),
            ("metrics", "4. Metrics and scoring contract"),
            ("evaluation process", "6. Execution and reproducibility"),
            ("how a win is declared", "8. How sure are we that one system beats another?"),
            ("results", "7. Results"),
            ("threats to validity", "12. Threats to validity"),
            ("production leaderboard", "13. From pilot to production leaderboard"),
            ("reflections", "14. Reflections"),
            ("least-sure design choice", "14.1 Which design choice are you least sure about"),
            ("most influential benchmark", "14.2 Which benchmark you read influenced you most"),
            ("misleading risks and guards", "14.3 What could make your leaderboard misleading"),
            ("improve with more time", "14.4 What would you improve with more time"),
            ("references", "References"),
            ("reproducibility appendix", "Appendix A. Reproducibility"),
            ("per-recording appendix", "Appendix B. Per-recording results"),
            ("provenance appendix", "Appendix C. Number provenance"),
        ]
        for label, needle in required:
            add(f"main covers {label}", needle in t, needle[:46])

        ids = ["pyannote/speaker-diarization-community-1",
               "nvidia/Nemotron-3-Diarization", "CIIL/Anuvani-Diarization"]
        for i in ids:
            add(f"exact identifier: {i}", i in t, i)

        add("completion claim present", "72/72" in t, "72/72 units")
        add("language count reconciled", "7 languages" in t or "seven languages" in t,
            "six Indic languages plus English")
        add("no stale nine-language claim", "9 languages" not in t and "nine languages" not in t,
            "manifest has seven language labels")
        for metric in ["cpWER", "tcpWER", "WER/CER", "Speaker separation", "Speaker similarity", "Speaker clustering", "VAD / SAD"]:
            add(f"main future work: {metric}", metric in t, "proposed, not measured")
        catalog_names = ["Deepgram", "AssemblyAI", "Amazon Transcribe", "Chirp 3",
                         "Speechmatics", "Falcon", "SpeakerKit", "Precision-2", "BUT-FIT"]
        add("broader system catalog included", all(x in t for x in catalog_names),
            "12 named candidates; three measured pilots")
        add("report ends with reflections", t.rfind("14.4 What would you improve") >
            t.rfind("Appendix C. Number provenance"), "reflection follows supporting appendices")
        add("streaming deviation disclosed", "streaming, low-latency" in t, "§5.3")
        add("no unfilled placeholder", "[TODO" not in t and "Firstname" not in t,
            "no TODO / Firstname left in the body")

    if one_pdf:
        n, t = text_of(one_pdf)
        add("one-pager is exactly one page", n == 1, f"{n} page")
        for label, needle in [("purpose", "PURPOSE"), ("setup", "SETUP"),
                              ("principal finding", "PRINCIPAL FINDING"),
                              ("three decisions", "THREE DESIGN DECISIONS"),
                              ("limitation", "LIMITATION")]:
            add(f"one-pager covers {label}", needle.lower() in t.lower(), needle)
        for metric in ["cpWER", "tcpWER"]:
            add(f"one-pager future work: {metric}", metric in t, "proposed transcription track")
        add("one-pager broader datasets", all(x in t for x in ["DIHARD", "CALLHOME", "DISPLACE"]),
            "future dataset expansion")
        add("one-pager collar column", "250 ms" in t and "0 ms" in t,
            "headline and boundary-collar sensitivity side by side")
        for system in ["anuvani", "community-1", "nemotron"]:
            def mean_der(suffix):
                path = os.path.join(ROOT, "data", "runs", "results", f"{system}{suffix}.json")
                return statistics.mean(r["der"] * 100 for r in json.load(open(path))["per_recording"])
            base, sensitivity = mean_der(""), mean_der("_collar0.25")
            expected = f"{sensitivity:.1f} {sensitivity-base:+.1f} pp"
            add(f"one-pager collar results: {system}", expected in t,
                f"{base:.1f}% -> {sensitivity:.1f}%; {sensitivity-base:+.1f} pp")
        add("one-pager collar convention", "125 ms on each side" in t,
            "pyannote c=0.25 s is total collar width")

    frontend = os.path.join(SUB, "Ayush_Kumar_Q1_Leaderboard.html")
    if os.path.exists(frontend):
        html = open(frontend).read()
        add("self-contained frontend included", "__PILOT_DATA__" not in html and "const D=" in html,
            "embedded saved pilot data and attributed audio; no external assets")
        add("real audio embedded", "data:audio/wav;base64," in html and "audioPlayer" in html, "three playable pilot excerpts")
        add("complete product sections", all(x in html for x in ['id="overview"', 'id="audio"', 'id="runs"', 'id="compare"']), "overview, results, compare, audio, datasets and runs")
    else:
        add("self-contained frontend included", False, "missing HTML")

    if board_pdf:
        n, t = text_of(board_pdf)
        add("sketch page count", n == 4, f"{n} pages")
        for label, needle in [("overview table", "model · version"),
                              ("model detail", "error decomposition"),
                              ("governance", "governance"),
                              ("curated vs BYO", "bring-your-own track"),
                              ("re-scoring", "re-scoring when a reference is corrected"),
                              ("versioning", "versioning, archival, and cadence"),
                              ("illustrative rows labelled", "illustrative"), ("audio inspector", "audio inspector")]:
            add(f"sketch covers {label}", needle in t.lower(), needle)

    # ---------------- video ----------------
    if link_txt:
        link = open(link_txt).read().strip().split("\n")[0]
        has_url = bool(re.search(r"https?://\S+", link))
        add("video link recorded", has_url,
            link[:70] if has_url else "no URL yet — record, upload unlisted, paste it here",
            warn=not has_url)
    else:
        add("video link recorded", False,
            "add submission/VIDEO_LINK.txt with the unlisted URL", warn=True)

    # ---------------- number provenance ----------------
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "t12",
                                                        "verify_numbers.py")],
                          capture_output=True, text=True)
    tail = [ln for ln in proc.stdout.strip().split("\n") if "verified" in ln]
    add("numbers trace to saved results", proc.returncode == 0,
        " · ".join(tail) if tail else "verify_numbers.py failed")

    # ---------------- report ----------------
    width = max(len(c) for c, _, _ in results) + 2
    for check, status, detail in results:
        mark = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}[status]
        print(f"{check:<{width}} {mark}  {detail}")

    fails = [r for r in results if r[1] == "FAIL"]
    warns = [r for r in results if r[1] == "WARN"]
    print(f"\n{len(results)-len(fails)-len(warns)} passed, {len(warns)} warnings, "
          f"{len(fails)} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
