"""Audit the 24 reference RTTMs: parse, count speakers/segments, speech time,
and overlap ratio. Validates the T06 coverage targets against real references.
"""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "harness"))

from rttm import load_rttm, turns_to_annotation  # noqa: E402
from scoring import _active_speaker_count_overlaps, speaker_durations  # noqa: E402


def audit(path: str) -> dict:
    turns = load_rttm(path)
    file_id = turns[0].file_id if turns else os.path.basename(path)
    ann = turns_to_annotation(turns, file_id)
    durs = speaker_durations(ann, None)
    total = sum(durs.values())
    ov = _active_speaker_count_overlaps(ann, None)
    ov_time = sum(e - s for s, e in ov)
    return {
        "file": os.path.basename(path),
        "segments": len(turns),
        "speakers": len(durs),
        "speech_s": round(total, 1),
        "overlap_s": round(ov_time, 1),
        "overlap_ratio": round(ov_time / total, 4) if total else 0.0,
    }


rows = []
for path in sorted(glob.glob("data/references/**/*.rttm", recursive=True)):
    rows.append(audit(path))

print(f"{'file':<22}{'seg':>5}{'spk':>4}{'speech_s':>9}{'ovlp_s':>8}{'ovlp%':>7}")
for r in rows:
    print(f"{r['file']:<22}{r['segments']:>5}{r['speakers']:>4}{r['speech_s']:>9.1f}"
          f"{r['overlap_s']:>8.1f}{r['overlap_ratio']*100:>6.1f}%")

crowded = [r for r in rows if r["speakers"] >= 5]
overlap = [r for r in rows if r["overlap_ratio"] >= 0.05]
print(f"\ncrowded (>=5 spk): {len(crowded)}/24   substantial-overlap (>=5%): {len(overlap)}/24")
print(f"total speech: {sum(r['speech_s'] for r in rows):.0f}s "
      f"({sum(r['speech_s'] for r in rows)/60:.1f} min)")
