"""Manifest -> score -> tables pipeline (the T09 interface, stubbed here).

T07 proves the scorer correct. This module wires the full interface so T08/T09
can drop in real reference and hypothesis RTTM without touching scoring logic:

    manifest.json
        -> reference RTTM per recording (from corpus, T08)
        -> hypothesis RTTM per recording (from model inference, T08/T09)
        -> scoring.scoring.score_pair per recording (locked settings)
        -> per-recording + aggregate results

Loaders are callables ``fn(recording: dict) -> str`` returning RTTM text for
one manifest row, so real data plugs in without code changes.
"""
from __future__ import annotations

import json
from typing import Callable, Dict, List

from rttm import parse_rttm, turns_to_annotation
from scoring import score_pair, count_metrics


def load_manifest(path: str = "harness/manifest.json") -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)["recordings"]


def run_manifest(
    manifest: List[dict],
    ref_loader: Callable[[dict], str],
    hyp_loader: Callable[[dict], str],
    collar: float = 0.0,
    skip_overlap: bool = False,
) -> Dict:
    """Score every recording in the manifest and aggregate.

    Returns {"per_recording": [...], "aggregate": {...}}.
    """
    per_recording: List[dict] = []
    for rec in manifest:
        rid = rec["id"]
        file_id = rec["recording_id"]  # RTTM file_id == manifest recording_id
        uem = rec.get("scoring_region")
        uem = [uem] if uem else None

        ref = turns_to_annotation(parse_rttm(ref_loader(rec)), file_id, uem=uem)
        hyp = turns_to_annotation(parse_rttm(hyp_loader(rec)), file_id, uem=uem)
        r = score_pair(ref, hyp, uem=uem, collar=collar, skip_overlap=skip_overlap)
        r["id"] = rid
        r["ref_speaker_count_true"] = rec.get("ref_speakers")
        per_recording.append(r)

    agg = {
        "n_recordings": len(per_recording),
        "counts": count_metrics(per_recording),
        "der": _weighted_mean(per_recording, "der"),
        "jer": _weighted_mean(per_recording, "jer"),
    }
    # low-activity recall pooled across recordings with any low-activity speaker
    low_n = sum(r["low_activity"]["n_low"] for r in per_recording)
    low_rec = sum(r["low_activity"]["n_recovered"] for r in per_recording)
    agg["low_activity_recall"] = (low_rec / low_n) if low_n else None
    agg["low_activity_n"] = low_n
    return {"per_recording": per_recording, "aggregate": agg}


def _weighted_mean(rows: List[dict], key: str) -> float | None:
    """Equal-weight mean over recordings (the plan's cell-average base unit)."""
    vals = [r[key] for r in rows if r.get(key) is not None]
    return sum(vals) / len(vals) if vals else None


def format_table(results: Dict) -> str:
    """Human-readable per-recording table."""
    header = (f"{'id':<7}{'ref':>4}{'hyp':>4}{'DER%':>8}{'JER%':>8}"
              f"{'miss':>7}{'FA':>7}{'conf':>7}{'ovDER':>8}")
    lines = [header, "-" * len(header)]
    for r in results["per_recording"]:
        ov = f"{r['overlap_der']*100:7.1f}" if r["overlap_der"] is not None else "     -"
        lines.append(
            f"{r['id']:<7}{r['ref_speaker_count']:>4}{r['hyp_speaker_count']:>4}"
            f"{r['der']*100:>8.1f}{r['jer']*100:>8.1f}"
            f"{r['components']['missed']*100:>7.1f}{r['components']['false_alarm']*100:>7.1f}"
            f"{r['components']['confusion']*100:>7.1f}{ov:>8}"
        )
    a = results["aggregate"]
    low = a.get("low_activity_recall")
    low_s = f"{low * 100:.0f}%" if low is not None else "n/a"
    count_acc = a["counts"].get("exact_count_accuracy")
    count_s = f"{count_acc * 100:.0f}%" if count_acc is not None else "n/a"
    lines.append("-" * len(header))
    lines.append(f"aggregate DER {a['der']*100:.1f}%  JER {a['jer']*100:.1f}%  "
                 f"count-acc {count_s}  "
                 f"low-activity recall {low_s} (n={a['low_activity_n']})")
    return "\n".join(lines)
