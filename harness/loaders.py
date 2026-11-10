"""Path resolution + loaders for references and hypotheses.

Convention (single source of truth):

  reference RTTM   : data/references/<corpus>/<name>.rttm
                     - indic:       <name> = manifest id  (e.g. HI-01)
                     - ami:         <name> = recording_id (e.g. ES2004a)
                     - voxconverse: <name> = recording_id (e.g. cjfer)
  hypothesis RTTM  : data/hypotheses/<system>/<rid>.rttm
  per-rec timing   : data/runs/timing/<system>/<rid>.json

The RTTM file_id inside every file (reference AND hypothesis) is the manifest
``recording_id`` — this is what makes ref/hyp match during scoring.
"""
from __future__ import annotations

import json
import os
from typing import Callable, Dict, List

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_manifest(path: str = None) -> List[dict]:
    path = path or os.path.join(ROOT, "harness", "manifest.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["recordings"]


def ref_path(rec: dict) -> str:
    corpus = rec["corpus"]
    if corpus == "indic-diarbench":
        name = rec["id"]
        dirname = "indic"  # references stored under the short corpus dir
    else:  # ami, voxconverse: file named by recording_id
        name = rec["recording_id"]
        dirname = corpus
    return os.path.join(ROOT, "data", "references", dirname, f"{name}.rttm")


def hyp_path(system: str, rec: dict) -> str:
    return os.path.join(ROOT, "data", "hypotheses", system, f"{rec['id']}.rttm")


def timing_path(system: str, rec: dict) -> str:
    return os.path.join(ROOT, "data", "runs", "timing", system, f"{rec['id']}.json")


def ref_loader() -> Callable[[dict], str]:
    def _load(rec: dict) -> str:
        with open(ref_path(rec), encoding="utf-8") as f:
            return f.read()
    return _load


def hyp_loader(system: str) -> Callable[[dict], str]:
    def _load(rec: dict) -> str:
        with open(hyp_path(system, rec), encoding="utf-8") as f:
            return f.read()
    return _load
