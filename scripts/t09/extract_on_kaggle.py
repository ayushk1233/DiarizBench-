"""Extract the 24 recordings' audio on Kaggle (fast HF network), then pull the
WAVs down locally and back-fill checksums into harness/manifest.json.

Usage:
  .venv-harness/bin/python scripts/t09/extract_on_kaggle.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "harness"))

from loaders import load_manifest  # noqa: E402

KERNEL_DIR = os.path.join(ROOT, "kaggle", "pilot-runs")
OUT = os.path.join(ROOT, "data", "audio")
os.makedirs(OUT, exist_ok=True)


def main():
    manifest = load_manifest()
    jobs = [
        {k: r[k] for k in ("id", "corpus", "language", "recording_id", "sample_id", "scoring_region")}
        for r in manifest
    ]
    with open(os.path.join(KERNEL_DIR, "kernel_extract_audio.py"), encoding="utf-8") as f:
        src = f.read()
    src = src.replace("__MANIFEST__", repr(jobs))
    with open(os.path.join(KERNEL_DIR, "run.py"), "w", encoding="utf-8") as f:
        f.write(src)
    meta = {
        "id": "ayuwat/diarizbench-extract-audio", "title": "diarizbench-extract-audio",
        "code_file": "run.py", "language": "python", "kernel_type": "script",
        "is_private": True, "enable_gpu": False, "enable_internet": True,
        "dataset_sources": [], "competition_sources": [], "model_sources": [], "kernel_sources": [],
    }
    with open(os.path.join(KERNEL_DIR, "kernel-metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    import subprocess
    slug = "ayuwat/diarizbench-extract-audio"
    subprocess.run(["kaggle", "kernels", "push", "-p", KERNEL_DIR], check=True)
    print("pushed", slug, flush=True)

    import time
    for _ in range(120):  # poll up to ~2h
        r = subprocess.run(["kaggle", "kernels", "status", slug], capture_output=True, text=True)
        out = (r.stdout or "") + (r.stderr or "")
        if "COMPLETE" in out or "ERROR" in out or "CANCELLED" in out:
            print(out.strip(), flush=True)
            break
        time.sleep(45)

    outdir = os.path.join(KERNEL_DIR, "out", "extract")
    shutil.rmtree(outdir, ignore_errors=True)
    subprocess.run(["kaggle", "kernels", "output", slug, "-p", outdir], check=True)

    src_audio = os.path.join(outdir, "audio")
    if not os.path.isdir(src_audio):
        print("!! no audio/ in output; listing:", os.listdir(outdir), flush=True)
        sys.exit(1)
    for wav in os.listdir(src_audio):
        if wav.endswith(".wav"):
            shutil.copy(os.path.join(src_audio, wav), os.path.join(OUT, wav))
    print(f"pulled {len(os.listdir(src_audio))} files to {OUT}", flush=True)

    # back-fill checksums from audio_manifest.json
    am = os.path.join(outdir, "audio_manifest.json")
    if os.path.exists(am):
        with open(am, encoding="utf-8") as f:
            kaggle_checksums = json.load(f)
        for r in manifest:
            if r["id"] in kaggle_checksums:
                r["checksum"] = kaggle_checksums[r["id"]]["checksum"]
        with open(os.path.join(ROOT, "harness", "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"comment": "Machine-readable pilot manifest (checksums from Kaggle extraction).",
                       "recordings": manifest}, f, indent=1)
        print("back-filled checksums into manifest.json", flush=True)


if __name__ == "__main__":
    main()
