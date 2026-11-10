"""Build the self-contained submission UI from saved pilot results; no demo scores."""
from __future__ import annotations

import importlib.util
import json
import argparse
import base64
import io
import wave
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_turns(path, start, end):
    turns = []
    for line in path.read_text().splitlines():
        p = line.split()
        if not p or p[0] != "SPEAKER":
            continue
        lo, hi = max(start, float(p[3])), min(end, float(p[3]) + float(p[4]))
        if hi > lo:
            turns.append({"start": round(lo-start, 3), "end": round(hi-start, 3), "speaker": p[7]})
    return turns


def audio_examples(manifest, include_audio=True):
    examples = []
    lookup = {r["id"]: r for r in manifest}
    for rid, start, end, title in [("BN-01", 15, 30, "A brief Bengali speaker is not recovered"),
                                   ("TE-02", 92, 104, "Three reference speakers overlap"),
                                   ("TA-02", 0, 20, "Tamil conversation: compare speaker turns")]:
        rec = lookup[rid]
        encoded, peaks = None, []
        if include_audio:
            with wave.open(str(ROOT / f"data/audio/{rid}.wav"), "rb") as source:
                rate = source.getframerate()
                if source.getnchannels() != 1 or source.getsampwidth() != 2:
                    raise ValueError("Expected canonical mono PCM16 input")
                source.setpos(round(start*rate))
                raw = source.readframes(round((end-start)*rate))
            out = io.BytesIO()
            with wave.open(out,"wb") as target:
                target.setnchannels(1);target.setsampwidth(2);target.setframerate(rate);target.writeframes(raw)
            samples = np.frombuffer(raw, dtype="<i2").astype(float)/32768
            peaks = [round(float(np.max(np.abs(chunk))),4) for chunk in np.array_split(samples,260)]
            encoded = "data:audio/wav;base64,"+base64.b64encode(out.getvalue()).decode()
        reference = read_turns(ROOT/f"data/references/indic/{rid}.rttm",start,end)
        hypotheses = {s: read_turns(ROOT/f"data/hypotheses/{s}/{rid}.rttm",start,end)
                      for s in ["community-1","nemotron","anuvani"]}
        examples.append(dict(id=rid,title=title,language=rec["language"],source_id=rec["recording_id"],
                             sample_id=rec["sample_id"],source_start=start,duration=end-start,
                             audio=encoded,
                             waveform=peaks,reference=reference,hypotheses=hypotheses))
    return examples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-audio", action="store_true", help="Publish a design without embedded audio; no source WAVs needed")
    parser.add_argument("--out", type=Path, help="Write one output instead of the private listening-demo defaults")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("sketch", ROOT / "scripts/t13/build_sketch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    manifest, stats, uncertainty, rows = mod.load()
    systems = mod.SYSTEMS
    recordings = []
    for r in manifest:
        folder = "indic" if r["corpus"] == "indic-diarbench" else r["corpus"]
        source_id = r["id"] if folder == "indic" else r["recording_id"]
        lo, hi = r["scoring_region"]
        events = []
        for line in (ROOT / f"data/references/{folder}/{source_id}.rttm").read_text().splitlines():
            cols = line.split()
            if not cols or cols[0] != "SPEAKER":
                continue
            start = max(lo, float(cols[3]))
            end = min(hi, float(cols[3]) + float(cols[4]))
            if end > start:
                events.extend([(start, 1), (end, -1)])
        active, previous, overlap = 0, lo, 0.0
        for time, delta in sorted(events):
            if active >= 2:
                overlap += time - previous
            active += delta
            previous = time
        recordings.append({"id": r["id"], "corpus": r["corpus"], "language": r["language"],
                           "duration": hi - lo, "overlap_percent_of_region": 100 * overlap / (hi - lo)})
    results = {s: json.loads((ROOT / f"data/runs/results/{s}.json").read_text())["per_recording"]
               for s in systems}
    payload = dict(recordings=recordings, results=results, rows=rows, stats=stats,
                   names=mod.NAME, modes=mod.MODE, audio_examples=audio_examples(manifest, not args.no_audio),
                   runs=json.loads((ROOT / "data/runs/summary.json").read_text()),
                   ids={"community-1": "pyannote/speaker-diarization-community-1",
                        "nemotron": "nvidia/Nemotron-3-Diarization",
                        "anuvani": "CIIL/Anuvani-Diarization"})
    template = (ROOT / "docs/frontend-template.html").read_text()
    template = template.replace("__PRODUCT_SECTIONS__", (ROOT / "docs/product-sections.html").read_text())
    template = template.replace("__PRODUCT_CSS__", (ROOT / "docs/product.css").read_text())
    template = template.replace("__PRODUCT_SCRIPT__", (ROOT / "docs/product.js").read_text())
    html = template.replace("__PILOT_DATA__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    if args.no_audio:
        html = html.replace("Hear the Bengali example", "Inspect the Bengali example").replace("Hear this model’s examples", "Inspect this model’s turns")
        html = html.replace("These are real pilot excerpts, not generated voices. Speaker preview buttons play the source mixture, not separated stems.",
                            "These examples identify real pilot recordings. Audio is not bundled in the GitHub version; use Open local audio to listen to your own file.")
        html = html.replace("Bengali, Telugu and Tamil examples are embedded, so playback requires no network.",
                            "Speaker-turn examples are included; source audio must be obtained separately.")
    targets = [args.out] if args.out else ([ROOT / "submission/Ayush_Kumar_Q1_Leaderboard_Design.html"] if args.no_audio else
               [ROOT / "docs/leaderboard-interactive.html", ROOT / "submission/Ayush_Kumar_Q1_Leaderboard.html"])
    for path in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
