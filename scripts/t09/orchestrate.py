"""Checkpointable pilot-run orchestrator.

Drives the 3 systems over the 24-recording manifest as batches of Kaggle kernel
runs. State is persisted to data/runs/state.json after every batch, so an
interrupted run resumes from exactly where it stopped: only recordings whose
{rid}.json is "ok" AND {rid}.rttm is non-empty are marked done.

Usage:
  .venv-harness/bin/python scripts/t09/orchestrate.py --systems community-1 --batch 6
  .venv-harness/bin/python scripts/t09/orchestrate.py --systems nemotron,anuvani
  .venv-harness/bin/python scripts/t09/orchestrate.py --only HI-01,AMI-01 --systems community-1   # smoke
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "harness"))

from loaders import load_manifest, hyp_path, timing_path  # noqa: E402

STATE_PATH = os.path.join(ROOT, "data", "runs", "state.json")
KERNEL_DIR = os.path.join(ROOT, "kaggle", "pilot-runs")
AUDIO_DATASET = "ayuwat/diarizbench-pilot-audio"
SYSTEMS = ["community-1", "nemotron", "anuvani"]

TEMPLATES = {
    "community-1": "kernel_community1.py",
    "nemotron": "kernel_nemotron.py",
    "anuvani": "kernel_anuvani.py",
}


def hf_token() -> str:
    p = os.path.expanduser("~/.cache/huggingface/token")
    with open(p, encoding="utf-8") as f:
        return f.read().strip()


def load_state(manifest):
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {"systems": SYSTEMS, "units": {s: {} for s in SYSTEMS}}
    # ensure every system + recording key exists
    for s in SYSTEMS:
        for rec in manifest:
            state["units"].setdefault(s, {}).setdefault(rec["id"], {"status": "pending"})
    return state


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, STATE_PATH)


def pending(state, system):
    return [rid for rid, u in state["units"][system].items() if u.get("status") != "done"]


def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def build_kernel(system, jobs, title):
    """Inject token + jobs into the template, write run.py + metadata, return slug."""
    with open(os.path.join(KERNEL_DIR, TEMPLATES[system]), encoding="utf-8") as f:
        src = f.read()
    src = src.replace("__HF_TOKEN__", repr(hf_token()))
    src = src.replace("__JOBS__", repr(jobs))
    with open(os.path.join(KERNEL_DIR, "run.py"), "w", encoding="utf-8") as f:
        f.write(src)
    meta = {
        "id": f"ayuwat/{title}",
        "title": title,
        "code_file": "run.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "dataset_sources": [AUDIO_DATASET],
        "competition_sources": [],
        "model_sources": [],
        "kernel_sources": [],
    }
    with open(os.path.join(KERNEL_DIR, "kernel-metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return f"ayuwat/{title}"


def push(title):
    r = sh(["kaggle", "kernels", "push", "-p", KERNEL_DIR, "--accelerator", "NvidiaTeslaT4"])
    if r.returncode != 0:
        print(r.stdout, r.stderr, file=sys.stderr)
        raise RuntimeError("kernels push failed")
    return title


def wait_status(slug, poll_s=60, max_wait_s=3600):
    """Poll until COMPLETE or ERROR; returns the final status string."""
    t0 = time.time()
    while True:
        r = sh(["kaggle", "kernels", "status", slug])
        out = (r.stdout or "") + (r.stderr or "")
        if "COMPLETE" in out:
            return "COMPLETE"
        if "ERROR" in out or "CANCELLED" in out:
            return out.strip()
        if time.time() - t0 > max_wait_s:
            return "TIMEOUT"
        time.sleep(poll_s)


def merge(system, outdir, state, rec_by_id):
    odir = os.path.join(outdir, "output")
    if not os.path.isdir(odir):
        return 0
    done = 0
    for rid in list(state["units"][system].keys()):
        jp = os.path.join(odir, f"{rid}.json")
        rp = os.path.join(odir, f"{rid}.rttm")
        if not os.path.exists(jp):
            continue
        job = json.load(open(jp, encoding="utf-8"))
        if job.get("status") == "ok" and os.path.exists(rp) and os.path.getsize(rp) > 0:
            shutil.copy(rp, hyp_path(system, rec_by_id[rid]))
            os.makedirs(os.path.dirname(timing_path(system, rec_by_id[rid])), exist_ok=True)
            with open(timing_path(system, rec_by_id[rid]), "w", encoding="utf-8") as f:
                json.dump(job, f, indent=1)
            state["units"][system][rid] = {**job, "status": "done"}
            done += 1
        elif job.get("status") == "error":
            state["units"][system][rid] = {**job, "status": "failed"}
    return done


def report(state):
    print("\n=== state ===")
    for s in SYSTEMS:
        units = state["units"][s]
        d = sum(1 for u in units.values() if u.get("status") == "done")
        f = sum(1 for u in units.values() if u.get("status") == "failed")
        print(f"  {s:<12} done={d:>2}/24  failed={f}  pending={24 - d - f}")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="community-1,nemotron,anuvani")
    ap.add_argument("--batch", type=int, default=6)
    ap.add_argument("--only", default=None, help="comma list of rids (smoke)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    systems = [s.strip() for s in args.systems.split(",") if s.strip()]
    manifest = load_manifest()
    rec_by_id = {r["id"]: r for r in manifest}
    state = load_state(manifest)
    report(state)

    for system in systems:
        pend = pending(state, system)
        if args.only:
            only = [r.strip() for r in args.only.split(",") if r.strip()]
            pend = [r for r in pend if r in only]
        if not pend:
            print(f"[{system}] nothing pending")
            continue

        # build job objects with file_id = recording_id
        pend.sort()
        batches = [pend[i:i + args.batch] for i in range(0, len(pend), args.batch)]
        for bi, batch in enumerate(batches, 1):
            jobs = [{"rid": rid, "file_id": rec_by_id[rid]["recording_id"]} for rid in batch]
            title = f"diarizbench-{system}-{bi:03d}"
            print(f"\n[{system}] batch {bi}/{len(batches)} -> {batch}", flush=True)
            if args.dry_run:
                print("  (dry run) jobs:", jobs)
                continue
            slug = build_kernel(system, jobs, title)
            push(slug)
            status = wait_status(slug)
            print(f"  status: {status}", flush=True)
            outdir = os.path.join(ROOT, "kaggle", "pilot-runs", "out", f"{system}-{bi:03d}")
            shutil.rmtree(outdir, ignore_errors=True)
            sh(["kaggle", "kernels", "output", slug, "-p", outdir])
            n = merge(system, outdir, state, rec_by_id)
            save_state(state)
            print(f"  merged {n} recording(s)", flush=True)
            report(state)

    print("done.")


if __name__ == "__main__":
    main()
