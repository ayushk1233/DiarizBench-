"""Timing panel: warm-up + 3 timed reps per system on a fixed 6-recording set.

One kernel per system (same GPU instance for all reps). Results land in
data/runs/timing/<system>/panel.json.

Usage:
  .venv-harness/bin/python scripts/t09/timing_panel.py --systems community-1,nemotron,anuvani
  .venv-harness/bin/python scripts/t09/timing_panel.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

import orchestrate as O  # noqa: E402
from loaders import load_manifest  # noqa: E402

# Fixed 6-recording set: 2 Indic (nf + itw), 2 AMI (short + long), 2 VoxConverse.
TIMING_RIDS = ["HI-01", "TE-02", "AMI-01", "AMI-04", "VC-01", "VC-03"]


def build_timing_kernel(system, jobs, title):
    with open(os.path.join(O.KERNEL_DIR, "kernel_timing.py"), encoding="utf-8") as f:
        src = f.read()
    src = src.replace("__SYSTEM__", repr(system))
    src = src.replace("__HF_TOKEN__", repr(O.hf_token()))
    src = src.replace("__JOBS__", repr(jobs))
    with open(os.path.join(O.KERNEL_DIR, "run.py"), "w", encoding="utf-8") as f:
        f.write(src)
    meta = {
        "id": f"ayuwat/{title}", "title": title, "code_file": "run.py",
        "language": "python", "kernel_type": "script", "is_private": True,
        "enable_gpu": True, "enable_internet": True,
        "dataset_sources": [O.AUDIO_DATASET],
        "competition_sources": [], "model_sources": [], "kernel_sources": [],
    }
    with open(os.path.join(O.KERNEL_DIR, "kernel-metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return f"ayuwat/{title}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="community-1,nemotron,anuvani")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    systems = [s.strip() for s in args.systems.split(",") if s.strip()]
    manifest = load_manifest()
    rec_by_id = {r["id"]: r for r in manifest}

    for system in systems:
        jobs = [{"rid": rid, "file_id": rec_by_id[rid]["recording_id"]} for rid in TIMING_RIDS]
        title = f"diarizbench-timing-{system}"
        print(f"\n[{system}] timing panel on {TIMING_RIDS}", flush=True)
        if args.dry_run:
            print("  (dry run)", jobs)
            continue
        slug = build_timing_kernel(system, jobs, title)
        O.push(slug)
        status = O.wait_status(slug)
        print(f"  status: {status}", flush=True)
        outdir = os.path.join(ROOT, "kaggle", "pilot-runs", "out", f"timing-{system}")
        shutil.rmtree(outdir, ignore_errors=True)
        O.sh(["kaggle", "kernels", "output", slug, "-p", outdir])
        src = os.path.join(outdir, "output", "timing.json")
        if os.path.exists(src):
            dst = os.path.join(ROOT, "data", "runs", "timing", system, "panel.json")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(src, dst)
            print(f"  saved panel -> {dst}", flush=True)
        else:
            print("  !! timing.json not produced", flush=True)

    print("timing panel done.")


if __name__ == "__main__":
    main()
