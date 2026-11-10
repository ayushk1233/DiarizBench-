"""Merge a downloaded `diarizbench_output.zip` into the local checkpoint.

The Kaggle notebook writes `output/<system>/<rid>.rttm|.json` for every finished
unit, then zips the whole `output/` tree. This script unpacks that zip and
applies the same "done" rule as `orchestrate.merge`:

  done  <=>  {rid}.json has status == "ok"  AND  {rid}.rttm is non-empty

Files land in the canonical locations (`data/hypotheses/<system>/<rid>.rttm`,
`data/runs/timing/<system>/<rid>.json`) and `data/runs/state.json` is updated,
so `score.py` and `timing_panel.py` can run immediately afterwards.

Usage:
  .venv-harness/bin/python scripts/t09/merge_output.py --zip ~/Downloads/diarizbench_output.zip
  .venv-harness/bin/python scripts/t09/merge_output.py --zip ... --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "harness"))

import orchestrate as O  # noqa: E402
from loaders import load_manifest, hyp_path, timing_path  # noqa: E402


def find_output_root(extracted: str) -> str:
    """Locate the directory that directly contains `<system>/<rid>.rttm`."""
    for base, dirs, _files in os.walk(extracted):
        if any(s in dirs for s in O.SYSTEMS):
            return base
    raise SystemExit(f"no system folders ({', '.join(O.SYSTEMS)}) found under {extracted}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True, help="path to diarizbench_output.zip")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep", default=None, help="extract here instead of a temp dir")
    args = ap.parse_args()

    manifest = load_manifest()
    rec_by_id = {r["id"]: r for r in manifest}
    state = O.load_state(manifest)

    tmp = args.keep or tempfile.mkdtemp(prefix="diarizbench_out_")
    os.makedirs(tmp, exist_ok=True)
    with zipfile.ZipFile(args.zip) as zf:
        zf.extractall(tmp)
    outdir = find_output_root(tmp)
    print(f"zip:  {args.zip}")
    print(f"root: {outdir}\n")

    total = 0
    for system in O.SYSTEMS:
        sdir = os.path.join(outdir, system)
        if not os.path.isdir(sdir):
            print(f"{system:<12} missing from zip")
            continue
        done = failed = 0
        for rid in sorted(state["units"][system]):
            jp = os.path.join(sdir, f"{rid}.json")
            rp = os.path.join(sdir, f"{rid}.rttm")
            if not os.path.exists(jp):
                continue
            with open(jp, encoding="utf-8") as f:
                job = json.load(f)
            ok = job.get("status") == "ok" and os.path.exists(rp) and os.path.getsize(rp) > 0
            if ok:
                done += 1
                if not args.dry_run:
                    hp = hyp_path(system, rec_by_id[rid])
                    os.makedirs(os.path.dirname(hp), exist_ok=True)
                    shutil.copy(rp, hp)
                    tp = timing_path(system, rec_by_id[rid])
                    os.makedirs(os.path.dirname(tp), exist_ok=True)
                    with open(tp, "w", encoding="utf-8") as f:
                        json.dump(job, f, indent=1)
                    state["units"][system][rid] = {**job, "status": "done"}
            else:
                failed += 1
                state["units"][system][rid] = {**job, "status": "failed"}
                print(f"  FAILED {system}/{rid}: {job.get('error', 'empty rttm')}")
        total += done
        print(f"{system:<12} merged={done:>2}/24  failed={failed}")

    # keep the run-level summary for provenance
    summary = os.path.join(outdir, "summary.json")
    if os.path.exists(summary) and not args.dry_run:
        dst = os.path.join(ROOT, "data", "runs", "summary.json")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(summary, dst)
        print(f"\nsummary.json -> {dst}")

    if not args.dry_run:
        O.save_state(state)
        print(f"state -> {O.STATE_PATH}")
    print(f"\nmerged {total} units{' (dry run)' if args.dry_run else ''}")
    O.report(state)


if __name__ == "__main__":
    main()
