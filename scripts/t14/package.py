"""T14 — build the submission under the required Firstname_Lastname_Q1_* names.

  .venv-harness/bin/python scripts/t14/package.py --name "First Last"

Rebuilds the main report and the one-pager with that name in the page header and
title page, copies the leaderboard sketch across, and lists what is ready.
The video is recorded by hand; drop its URL in submission/VIDEO_LINK.txt.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SUB = os.path.join(ROOT, "submission")
PY = sys.executable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help='e.g. "Asha Menon"')
    args = ap.parse_args()

    parts = args.name.split()
    if len(parts) < 2:
        raise SystemExit("--name needs a first and last name")
    slug = "_".join(parts)

    targets = {
        "main": os.path.join(SUB, f"{slug}_Q1_Main.pdf"),
        "one": os.path.join(SUB, f"{slug}_Q1_OnePager.pdf"),
        "board": os.path.join(SUB, f"{slug}_Q1_Leaderboard.pdf"),
    }

    figure_env = os.environ.copy()
    figure_env.setdefault("MPLCONFIGDIR", os.path.join(ROOT, "data", "runs", ".matplotlib"))
    subprocess.run([PY, os.path.join(ROOT, "scripts", "t14", "build_figures.py")],
                   check=True, env=figure_env)

    subprocess.run([PY, os.path.join(ROOT, "scripts", "t12", "build_main.py"),
                    "--author", args.name, "--out", targets["main"]], check=True)
    subprocess.run([PY, os.path.join(ROOT, "scripts", "t14", "build_onepager.py"),
                    "--author", args.name, "--out", targets["one"]], check=True)

    # the sketch carries no author line; rebuild so it is never stale
    subprocess.run([PY, os.path.join(ROOT, "scripts", "t13", "build_sketch.py"),
                    "--out", targets["board"]], check=True, capture_output=True)
    subprocess.run([PY, os.path.join(ROOT, "scripts", "t14", "build_frontend.py")], check=True)

    print("\nsubmission/")
    for p in sorted(os.listdir(SUB)):
        full = os.path.join(SUB, p)
        if os.path.isfile(full):
            print(f"  {os.path.getsize(full)/1024:8.0f} KB  {p}")
    print(f"\nvideo: add the unlisted URL to {os.path.join(SUB, 'VIDEO_LINK.txt')}")


if __name__ == "__main__":
    main()
