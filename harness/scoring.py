"""Primary scoring: DER/JER + extended metrics, via pyannote.metrics.

Settings are locked in metrics.md: zero collar, overlap scored
(skip_overlap=False), unknown speaker count. This module is the single source
of truth for the pilot's numbers; nryant/dscore is used only to cross-check
(see crosscheck.py).
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
from pyannote.core import Annotation, Segment, Timeline
from pyannote.metrics.diarization import DiarizationErrorRate, JaccardErrorRate


def uem_to_timeline(uem: List[Tuple[float, float]] | None) -> Timeline | None:
    if uem is None:
        return None
    return Timeline(segments=[Segment(s, e) for (s, e) in uem])


def _active_speaker_count_overlaps(ref: Annotation, uem) -> List[Tuple[float, float]]:
    """Return intervals where >=2 reference speakers are simultaneously active.

    Boundary points are collected from all reference segments (clipped to the
    scoring region); each sub-interval's active-speaker count is computed.
    """
    if uem is None:
        bounds = [seg.start for seg in ref.itersegments()] + [seg.end for seg in ref.itersegments()]
    else:
        bounds = [s for (s, e) in uem] + [e for (s, e) in uem]
        for seg in ref.itersegments():
            bounds += [max(seg.start, s) for (s, e) in uem if seg.end > s and seg.start < e]
            bounds += [min(seg.end, e) for (s, e) in uem if seg.end > s and seg.start < e]
    if not bounds:
        return []
    bounds = sorted(set(round(b, 6) for b in bounds))
    overlaps: List[Tuple[float, float]] = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a <= 1e-9:
            continue
        mid = (a + b) / 2.0
        n = 0
        for seg in ref.itersegments():
            if seg.start < mid < seg.end and (uem is None or any(s < mid < e for (s, e) in uem)):
                n += 1
        if n >= 2:
            overlaps.append((a, b))
    return overlaps


def _restrict(ann: Annotation, regions: List[Tuple[float, float]]) -> Annotation:
    out = Annotation(uri=ann.uri)
    for seg, _, label in ann.itertracks(yield_label=True):
        for (s, e) in regions:
            cs, ce = max(seg.start, s), min(seg.end, e)
            if ce > cs:
                out[Segment(cs, ce)] = label
    return out


def speaker_durations(ann: Annotation, uem) -> Dict[str, float]:
    """Per-speaker active duration (clipped to UEM)."""
    dur: Dict[str, float] = {}
    for seg, _, label in ann.itertracks(yield_label=True):
        s, e = seg.start, seg.end
        if uem is not None:
            for (us, ue) in uem:
                d = max(0.0, min(e, ue) - max(s, us))
                if d > 0:
                    dur[label] = dur.get(label, 0.0) + d
        else:
            dur[label] = dur.get(label, 0.0) + (e - s)
    return dur


def optimal_mapping(ref: Annotation, hyp: Annotation, uem) -> Dict[str, str | None]:
    """One-to-one ref->hyp speaker mapping maximising total temporal overlap.

    Unmatched reference speakers map to None. Built on the intersection matrix
    and scipy's linear_sum_assignment (Hungarian).
    """
    from scipy.optimize import linear_sum_assignment

    ref_spks = sorted({label for _, _, label in ref.itertracks(yield_label=True)})
    hyp_spks = sorted({label for _, _, label in hyp.itertracks(yield_label=True)})
    if not ref_spks:
        return {}
    if not hyp_spks:
        return {r: None for r in ref_spks}

    def intersection(r, h):
        tot = 0.0
        for seg, _, label in ref.itertracks(yield_label=True):
            if label != r:
                continue
            s, e = seg.start, seg.end
            if uem is not None:
                for (us, ue) in uem:
                    s2, e2 = max(s, us), min(e, ue)
                    if e2 <= s2:
                        continue
                    for hseg, _, hlabel in hyp.itertracks(yield_label=True):
                        if hlabel == h:
                            hs, he = hseg.start, hseg.end
                            tot += max(0.0, min(e2, he) - max(s2, hs))
            else:
                for hseg, _, hlabel in hyp.itertracks(yield_label=True):
                    if hlabel == h:
                        hs, he = hseg.start, hseg.end
                        tot += max(0.0, min(e, he) - max(s, hs))
        return tot

    n, m = len(ref_spks), len(hyp_spks)
    # pad to square; cost = -overlap (maximize overlap)
    cost = np.zeros((n, n + m))
    for i, r in enumerate(ref_spks):
        for j, h in enumerate(hyp_spks):
            cost[i, j] = -intersection(r, h)
    # columns n..n+m-1 are dummy (cost 0 = no match)
    rows, cols = linear_sum_assignment(cost)
    mapping: Dict[str, str | None] = {}
    for i, j in zip(rows, cols):
        r = ref_spks[i]
        mapping[r] = hyp_spks[j] if j < m else None
    return mapping


def score_pair(
    ref: Annotation,
    hyp: Annotation,
    uem: List[Tuple[float, float]] | None = None,
    collar: float = 0.0,
    skip_overlap: bool = False,
) -> Dict[str, float | Dict]:
    """Score one reference/hypothesis pair.

    Returns DER, JER, DER components, overlap-only DER, speaker counts, and the
    low-activity diagnostic.
    """
    tl = uem_to_timeline(uem)
    der_metric = DiarizationErrorRate(collar=collar, skip_overlap=skip_overlap)
    jer_metric = JaccardErrorRate(collar=collar, skip_overlap=skip_overlap)

    der = der_metric(ref, hyp, uem=tl)
    jer = jer_metric(ref, hyp, uem=tl)
    components = der_metric.compute_components(ref, hyp, uem=tl)
    total = float(components.get("total", 0.0) or 0.0)
    if total > 0:
        missed = float(components["missed detection"]) / total
        fa = float(components["false alarm"]) / total
        confusion = float(components["confusion"]) / total
    else:
        missed = fa = confusion = 0.0

    # overlap-only DER
    ov_regions = _active_speaker_count_overlaps(ref, uem)
    overlap_der = None
    if ov_regions:
        ref_ov = _restrict(ref, ov_regions)
        hyp_ov = _restrict(hyp, ov_regions)
        overlap_der = float(DiarizationErrorRate(collar=collar, skip_overlap=False)(ref_ov, hyp_ov))

    # counts (speakers with positive activity inside scoring region)
    ref_durs = speaker_durations(ref, uem)
    hyp_durs = speaker_durations(hyp, uem)
    ref_count = len(ref_durs)
    hyp_count = len(hyp_durs)

    # low-activity diagnostic (thresholds from metrics.md)
    low = low_activity(ref, hyp, uem, activity_threshold=0.05, min_dur=0.5, recovery=0.5)

    return {
        "der": der,
        "jer": jer,
        "components": {"missed": missed, "false_alarm": fa, "confusion": confusion,
                       "total": total},
        "overlap_der": overlap_der,
        "ref_speaker_count": ref_count,
        "hyp_speaker_count": hyp_count,
        "low_activity": low,
    }


def low_activity(
    ref: Annotation,
    hyp: Annotation,
    uem,
    activity_threshold: float = 0.05,
    min_dur: float = 0.5,
    recovery: float = 0.5,
) -> Dict:
    """Low-activity-speaker diagnostic (metrics.md §2).

    A speaker is low-activity if their reference time <= activity_threshold of
    the total AND >= min_dur seconds. Recovery requires >= recovery fraction of
    their reference speech to overlap the optimally-matched hypothesis speaker.
    """
    ref_durs = speaker_durations(ref, uem)
    total = sum(ref_durs.values())
    if total <= 0:
        return {"n_low": 0, "n_recovered": 0, "recall": None, "speakers": []}

    mapping = optimal_mapping(ref, hyp, uem)
    low_spks = [s for s, d in ref_durs.items() if d >= min_dur and d <= activity_threshold * total]

    recovered = []
    for spk in low_spks:
        h = mapping.get(spk)
        if h is None:
            recovered.append(False)
            continue
        # fraction of spk's reference time overlapping h
        spk_time = ref_durs[spk]
        inter = _speaker_intersection(ref, hyp, spk, h, uem)
        recovered.append(inter / spk_time >= recovery)

    n_low = len(low_spks)
    n_rec = sum(recovered)
    return {
        "n_low": n_low,
        "n_recovered": n_rec,
        "recall": (n_rec / n_low) if n_low else None,
        "speakers": low_spks,
        "recovered": recovered,
    }


def _speaker_intersection(ref, hyp, r, h, uem) -> float:
    tot = 0.0
    for seg, _, label in ref.itertracks(yield_label=True):
        if label != r:
            continue
        s, e = seg.start, seg.end
        regions = uem if uem is not None else [(s, e)]
        for (us, ue) in (uem if uem is not None else [(s, e)]):
            s2, e2 = max(s, us), min(e, ue)
            if e2 <= s2:
                continue
            for hseg, _, hlabel in hyp.itertracks(yield_label=True):
                if hlabel == h:
                    tot += max(0.0, min(e2, hseg.end) - max(s2, hseg.start))
    return tot


def count_metrics(results: List[Dict]) -> Dict[str, float]:
    """Aggregate exact-count accuracy, MAE, and signed bias across recordings."""
    diffs = [r["hyp_speaker_count"] - r["ref_speaker_count"] for r in results]
    exact = sum(1 for d in diffs if d == 0) / len(diffs) if diffs else None
    mae = float(np.mean([abs(d) for d in diffs])) if diffs else None
    bias = float(np.mean(diffs)) if diffs else None
    return {"exact_count_accuracy": exact, "count_mae": mae, "count_bias": bias}
