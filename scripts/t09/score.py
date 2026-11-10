"""Score completed pilot runs against references.

Reads data/runs/state.json to find recordings marked done per system, then
scores each against its reference using the locked settings (zero collar,
overlap scored, unknown speaker count) and prints + writes results.

Usage:
  .venv-harness/bin/python scripts/t09/score.py --system community-1
  .venv-harness/bin/python scripts/t09/score.py --system nemotron --collar 0.25
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "harness"))

from loaders import load_manifest, ref_loader, hyp_loader  # noqa: E402
from pipeline import run_manifest, format_table  # noqa: E402

STATE_PATH = os.path.join(ROOT, "data", "runs", "state.json")
OUT = os.path.join(ROOT, "data", "runs", "results")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True)
    ap.add_argument("--collar", type=float, default=0.0)
    ap.add_argument("--skip-overlap", action="store_true")
    args = ap.parse_args()

    manifest = load_manifest()
    with open(STATE_PATH, encoding="utf-8") as f:
        state = json.load(f)

    done_ids = {
        rid for rid, u in state["units"][args.system].items()
        if u.get("status") == "done"
    }
    done = [r for r in manifest if r["id"] in done_ids]
    print(f"scoring {len(done)}/24 done recordings for {args.system}", flush=True)

    results = run_manifest(
        done,
        ref_loader=ref_loader(),
        hyp_loader=hyp_loader(args.system),
        collar=args.collar,
        skip_overlap=args.skip_overlap,
    )
    print(format_table(results))

    os.makedirs(OUT, exist_ok=True)
    suffix = f"_collar{args.collar}" if args.collar else ""
    path = os.path.join(OUT, f"{args.system}{suffix}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
