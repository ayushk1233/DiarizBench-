"""RTTM parsing/serialization and conversion to pyannote.core.Annotation.

The harness uses RTTM as the single interchange format. References and
hypotheses both arrive as RTTM (SPEAKER lines); scoring operates on
pyannote.core.Annotation objects built from those segments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Tuple

from pyannote.core import Annotation, Segment


@dataclass
class Turn:
    file_id: str
    speaker_id: str
    onset: float
    duration: float

    @property
    def offset(self) -> float:
        return self.onset + self.duration


def parse_rttm(text: str) -> List[Turn]:
    """Parse RTTM text (SPEAKER lines) into Turn objects.

    Invalid lines (bad onset, non-positive duration) raise ValueError so the
    harness fails loudly rather than silently skipping malformed hypotheses.
    """
    turns: List[Turn] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("SPKR-INFO"):
            continue
        fields = line.split()
        if fields[0] != "SPEAKER":
            continue
        if len(fields) < 9:
            raise ValueError(f"line {i}: fewer than 9 fields: {line!r}")
        try:
            onset = float(fields[3])
            duration = float(fields[4])
        except ValueError as e:
            raise ValueError(f"line {i}: bad onset/duration: {line!r}") from e
        if onset < 0:
            raise ValueError(f"line {i}: negative onset: {line!r}")
        if duration <= 0:
            raise ValueError(f"line {i}: non-positive duration: {line!r}")
        turns.append(Turn(fields[1], fields[7], onset, duration))
    return turns


def load_rttm(path: str) -> List[Turn]:
    with open(path, encoding="utf-8") as f:
        return parse_rttm(f.read())


def format_rttm(turns: Iterable[Turn], n_digits: int = 3) -> str:
    """Serialize turns back to RTTM (SPEAKER lines)."""
    out = []
    for t in sorted(turns, key=lambda t: (t.file_id, t.speaker_id, t.onset)):
        out.append(
            f"SPEAKER {t.file_id} 1 {t.onset:.{n_digits}f} {t.duration:.{n_digits}f} "
            f"<NA> <NA> {t.speaker_id} <NA> <NA>"
        )
    return "\n".join(out) + ("\n" if out else "")


def _coalesce(turns: Iterable[Turn], file_id: str) -> List[Turn]:
    """Merge overlapping/touching segments of the same speaker within one file.

    pyannote.core.Annotation cannot hold two overlapping segments with the same
    label, so same-speaker overlaps must be coalesced first. Different speakers
    may still overlap (which is exactly what we want to preserve for scoring).
    """
    by_speaker: dict = {}
    for t in turns:
        if t.file_id != file_id:
            continue
        by_speaker.setdefault(t.speaker_id, []).append(t)

    merged: List[Turn] = []
    for spk, segs in by_speaker.items():
        segs = sorted(segs, key=lambda t: t.onset)
        cur_start, cur_end = segs[0].onset, segs[0].offset
        for t in segs[1:]:
            if t.onset <= cur_end:  # overlap or touch -> merge
                cur_end = max(cur_end, t.offset)
            else:
                merged.append(Turn(file_id, spk, cur_start, cur_end - cur_start))
                cur_start, cur_end = t.onset, t.offset
        merged.append(Turn(file_id, spk, cur_start, cur_end - cur_start))
    return merged


def turns_to_annotation(
    turns: Iterable[Turn],
    file_id: str,
    uem: List[Tuple[float, float]] | None = None,
) -> Annotation:
    """Build a pyannote.core.Annotation for one file.

    Same-speaker overlaps are coalesced; different-speaker overlaps are kept.
    If ``uem`` is given, segments are clipped to those regions first.
    """
    ann = Annotation(uri=file_id)
    for t in _coalesce(turns, file_id):
        start, end = t.onset, t.offset
        if uem is not None:
            # clip to the union of UEM regions
            clipped = False
            for (us, ue) in uem:
                s, e = max(start, us), min(end, ue)
                if e > s:
                    ann[Segment(s, e)] = t.speaker_id
                    clipped = True
            if not clipped:
                continue
        else:
            if end > start:
                ann[Segment(start, end)] = t.speaker_id
    return ann


def reference_speaker_time(ann: Annotation, uem: List[Tuple[float, float]] | None = None) -> float:
    """Total reference speech time (duration-weighted, counting overlap once per
    speaker)."""
    if uem is None:
        return sum(seg.duration for seg in ann.itersegments())
    total = 0.0
    for seg, _, _ in ann.itertracks(yield_label=True):
        s, e = seg.start, seg.end
        for (us, ue) in uem:
            total += max(0.0, min(e, ue) - max(s, us))
    return total
