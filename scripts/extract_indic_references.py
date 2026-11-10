"""Extract reference RTTM for the 12 Indic pilot recordings from Indic DiarBench.

Reads only the small columns (sample_id, recording_id, annotated_transcript),
not the audio. Converts annotated_transcript (list of speaker-attributed
utterances) to RTTM SPEAKER lines, one file per manifest id.

The RTTM file_id is the manifest ``recording_id`` (universal file id used by the
harness and by the hypothesis kernels), NOT the ``sample_id``.
"""
import json
import os

import pyarrow.parquet as pq
import fsspec

fs = fsspec.filesystem("http", client_kwargs={"headers": {"User-Agent": "diarizbench"}})
BASE = "https://huggingface.co/datasets/sarvamai/indic-diarbench/resolve/refs%2Fconvert%2Fparquet"
COLS = ["sample_id", "recording_id", "annotated_transcript", "num_speakers", "duration_seconds"]

with open("harness/manifest.json", encoding="utf-8") as f:
    manifest = json.load(f)["recordings"]

# (rid, language, recording_id, sample_id) for Indic rows only
TARGETS = [
    (r["id"], r["language"], r["recording_id"], r["sample_id"])
    for r in manifest if r["corpus"] == "indic-diarbench"
]

OUT = "data/references/indic"
os.makedirs(OUT, exist_ok=True)

by_lang = {}
for rid, lang, recid, sample in TARGETS:
    by_lang.setdefault(lang, []).append((rid, recid, sample))

summary = {}
for lang, triples in by_lang.items():
    want = {sample for _, _, sample in triples}
    url = f"{BASE}/{lang}/test/0000.parquet"
    with fs.open(url, "rb") as f:
        tbl = pq.ParquetFile(f).read(columns=COLS).to_pylist()
    for row in tbl:
        sid = row["sample_id"]
        if sid not in want:
            continue
        rid, recid, sample = next((r, c, s) for r, c, s in triples if s == sid)
        lines = []
        speakers = set()
        for seg in row["annotated_transcript"]:
            raw = seg["speaker_id"]
            # RTTM is whitespace-delimited: sanitize speaker ids that contain
            # spaces (in-the-wild samples use "Speaker A", "New speaker A").
            spk = "_".join(str(raw).split())
            s, e = seg["start_time"], seg["end_time"]
            if e <= s:
                continue
            speakers.add(spk)
            lines.append(f"SPEAKER {recid} 1 {s:.3f} {e - s:.3f} <NA> <NA> {spk} <NA> <NA>")
        with open(os.path.join(OUT, f"{rid}.rttm"), "w") as fout:
            fout.write("\n".join(lines) + ("\n" if lines else ""))
        summary[rid] = {
            "recording_id": recid,
            "sample_id": sid,
            "language": lang,
            "n_segments": len(lines),
            "n_speakers": len(speakers),
            "dataset_num_speakers": row["num_speakers"],
            "dataset_duration_s": round(row["duration_seconds"], 1),
        }
        print(f"{rid}  {lang:<9} file_id={recid} (sample {sid})  segs={len(lines):4d}  "
              f"spk={len(speakers)} (dataset says {row['num_speakers']})  dur={row['duration_seconds']:.1f}s")

with open("scripts/indic_reference_summary.json", "w") as f:
    json.dump(summary, f, indent=1)
print(f"\nwrote {len(summary)} reference RTTMs to {OUT}")
