"""Extract all 24 pilot recordings' audio to data/audio/<recording_id>.wav.

Normalizes to 16 kHz mono 16-bit PCM, truncates to the scoring region, computes
a canonical SHA-256 checksum (over the decoded int16 PCM), and back-fills
harness/manifest.json.

Sources:
  - AMI:         official public mirror URL (Array1-01.wav, already 16k mono)
  - VoxConverse: diarizers-community/voxconverse (dev parquet, raw bytes)
  - Indic:       sarvamai/indic-diarbench (per-language test parquet, raw bytes)

Audio bytes are decoded with soundfile (WAV/FLAC) with an ffmpeg fallback, so
no torch/torchcodec is needed.

Resumable: a recording whose <id>.wav already exists is skipped.

Run with: .venv-extract/bin/python scripts/extract_audio.py
"""
import io
import json
import hashlib
import os
import shutil
import subprocess
import sys
import time
import urllib.request

import numpy as np
import soundfile as sf
import fsspec
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "data", "audio")
os.makedirs(OUT, exist_ok=True)

MANIFEST = os.path.join(ROOT, "harness", "manifest.json")
with open(MANIFEST, encoding="utf-8") as f:
    manifest = json.load(f)["recordings"]

AMI_URL = "https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/{m}/audio/{m}.Array1-01.wav"
FS = fsspec.filesystem("http", client_kwargs={"headers": {"User-Agent": "diarizbench"}})
HF_RESOLVE = "https://huggingface.co/datasets/{ds}/resolve/refs%2Fconvert%2Fparquet"


def checksum_pcm(pcm: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(pcm, dtype=np.int16).tobytes()).hexdigest()


def to_16k_mono(arr, sr):
    if arr.ndim > 1:
        arr = arr.mean(axis=1)
    arr = np.asarray(arr, dtype=np.float64)
    if sr != 16000:
        n = int(round(len(arr) * 16000 / sr))
        x_old = np.linspace(0, len(arr) - 1, len(arr))
        x_new = np.linspace(0, len(arr) - 1, n)
        arr = np.interp(x_new, x_old, arr)
    peak = np.max(np.abs(arr)) if arr.size else 1.0
    if peak > 1.0:
        arr = arr / peak
    arr = np.clip(arr, -1.0, 1.0)
    return np.round(arr * 32767).astype(np.int16)


def decode_bytes(raw):
    """Decode raw encoded audio bytes to (float array, sr)."""
    raw = bytes(raw)
    try:
        return sf.read(io.BytesIO(raw), dtype="float64", always_2d=False)
    except Exception:
        pass
    # ffmpeg fallback (handles mp3/ogg/etc.)
    tmp = os.path.join(OUT, "_ffmpeg_tmp.bin")
    out = tmp + ".wav"
    with open(tmp, "wb") as f:
        f.write(raw)
    subprocess.run(["ffmpeg", "-y", "-i", tmp, "-ar", "16000", "-ac", "1", out],
                   capture_output=True)
    arr, sr = sf.read(out, dtype="float64", always_2d=False)
    os.remove(tmp)
    os.remove(out)
    return arr, sr


def write(rec, arr, sr):
    rid = rec["id"]
    region = rec.get("scoring_region")
    if region and arr.size:
        arr = arr[: int(round(region[1] * sr))]
    pcm = to_16k_mono(arr, sr)
    path = os.path.join(OUT, f"{rid}.wav")
    sf.write(path, pcm, 16000, subtype="PCM_16")
    return path, checksum_pcm(pcm), 16000, len(pcm) / 16000.0


def finish(rec, path, ck, sr, dur):
    rec["checksum"] = ck
    return {"checksum": ck, "source_sr": sr, "duration_s": round(dur, 3),
            "n_samples": int(round(dur * 16000)), "file": os.path.basename(path)}


results = {}
for rec in manifest:
    rid = rec["id"]
    fpath = os.path.join(OUT, f"{rid}.wav")
    if os.path.exists(fpath) and os.path.getsize(fpath) > 0:
        pcm, sr = sf.read(fpath, dtype="int16", always_2d=False)
        if pcm.ndim > 1:
            pcm = pcm.mean(axis=1).astype(np.int16)
        rec["checksum"] = checksum_pcm(np.asarray(pcm, dtype=np.int16))
        results[rid] = {"checksum": rec["checksum"], "reused": True, "file": f"{rid}.wav"}
        print(f"[{rid}] reused existing (sr={sr})", flush=True)
    else:
        rec["checksum"] = None


# ---- AMI (direct URL, one per meeting, with retry) ----
for rec in [r for r in manifest if r["corpus"] == "ami" and r["id"] not in results]:
    rid, m = rec["id"], rec["recording_id"]
    print(f"[{rid}] ami {m} ...", flush=True)
    try:
        tmp = os.path.join(OUT, f"_tmp_{rid}.wav")
        req = urllib.request.Request(AMI_URL.format(m=m),
                                     headers={"User-Agent": "Mozilla/5.0 (Diarizbench pilot)"})
        last = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as fh:
                    shutil.copyfileobj(r, fh)
                break
            except Exception as e:
                last = e
                time.sleep(5 * (attempt + 1))
        else:
            raise last
        arr, sr = sf.read(tmp, dtype="float64", always_2d=False)
        path, ck, sr2, dur = write(rec, arr, sr)
        os.remove(tmp)
        results[rid] = finish(rec, path, ck, sr2, dur)
        print(f"    -> {ck[:16]}… sr={sr2} dur={dur:.1f}s", flush=True)
    except Exception as e:
        print(f"    FAIL {type(e).__name__}: {str(e)[:200]}", flush=True)


# ---- Indic (per-language test parquet, match sample_id) ----
indic_by_lang = {}
for r in manifest:
    if r["corpus"] == "indic-diarbench" and r["id"] not in results:
        indic_by_lang.setdefault(r["language"], []).append(r)
for lang, recs in indic_by_lang.items():
    want = {r["sample_id"]: r for r in recs}
    url = f"{HF_RESOLVE.format(ds='sarvamai/indic-diarbench')}/{lang}/test/0000.parquet"
    print(f"[indic {lang}] reading {url.split('/')[-1]} for {len(want)} sample(s) ...", flush=True)
    try:
        with FS.open(url, "rb") as f:
            tbl = pq.ParquetFile(f).read(columns=["audio", "sample_id"]).to_pylist()
        for row in tbl:
            sid = row["sample_id"]
            if sid not in want:
                continue
            rec = want[sid]
            arr, sr = decode_bytes(row["audio"]["bytes"])
            path, ck, sr2, dur = write(rec, arr, sr)
            results[rec["id"]] = finish(rec, path, ck, sr2, dur)
            print(f"    [{rec['id']}] -> {ck[:16]}… sr={sr2} dur={dur:.1f}s", flush=True)
    except Exception as e:
        print(f"    [{lang}] FAIL {type(e).__name__}: {str(e)[:200]}", flush=True)


# ---- VoxConverse (dev parquet shards, match file id in audio path) ----
vc_recs = {r["recording_id"]: r for r in manifest
           if r["corpus"] == "voxconverse" and r["id"] not in results}
if vc_recs:
    print(f"[voxconverse] scanning 5 dev shards for {len(vc_recs)} file(s) ...", flush=True)
    for part in range(5):
        if not vc_recs:
            break
        url = f"{HF_RESOLVE.format(ds='diarizers-community/voxconverse')}/default/partial-dev/{part:04d}.parquet"
        try:
            with FS.open(url, "rb") as f:
                tbl = pq.ParquetFile(f).read(columns=["audio"]).to_pylist()
            for row in tbl:
                p = (row["audio"].get("path") or "")
                for fid, rec in list(vc_recs.items()):
                    if fid in p:
                        arr, sr = decode_bytes(row["audio"]["bytes"])
                        path, ck, sr2, dur = write(rec, arr, sr)
                        results[rec["id"]] = finish(rec, path, ck, sr2, dur)
                        del vc_recs[fid]
                        print(f"    [{rec['id']}] -> {ck[:16]}… sr={sr2} dur={dur:.1f}s", flush=True)
                        break
        except Exception as e:
            print(f"    [shard {part}] FAIL {type(e).__name__}: {str(e)[:200]}", flush=True)
    for fid in vc_recs:
        print(f"    [{fid}] NOT FOUND", flush=True)


# ---- persist ----
with open(os.path.join(HERE, "audio_manifest.json"), "w") as f:
    json.dump(results, f, indent=1)
with open(MANIFEST, "w", encoding="utf-8") as f:
    json.dump({"comment": json.load(open(MANIFEST))["comment"], "recordings": manifest}, f, indent=1)

missing = [r["id"] for r in manifest if r["id"] not in results]
print(f"\nOK {len(results)}/24  missing {len(missing)}: {missing}", flush=True)
sys.exit(1 if missing else 0)
