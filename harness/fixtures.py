"""Validation fixtures (plan.md §5) with hand-computed expected values.

Each fixture is a (reference, hypothesis) RTTM pair chosen to isolate one
failure mode. Expected DER/JER are computed by hand; the tests assert both the
expected value AND that pyannote.metrics and nryant/dscore agree.

RTTM fields: SPEAKER <file> 1 <onset> <dur> <NA> <NA> <speaker> <NA> <NA>
"""
from __future__ import annotations


def _line(file_id, onset, dur, spk):
    return f"SPEAKER {file_id} 1 {onset} {dur} <NA> <NA> {spk} <NA> <NA>"


FIXTURES = [
    {
        "id": "perfect",
        "ref": [_line("f", 0.0, 10.0, "A"), _line("f", 10.0, 10.0, "B")],
        "hyp": [_line("f", 0.0, 10.0, "A"), _line("f", 10.0, 10.0, "B")],
        "der": 0.0,
        "jer": 0.0,
    },
    {
        "id": "permuted_labels",
        "ref": [_line("f", 0.0, 10.0, "A"), _line("f", 10.0, 10.0, "B")],
        "hyp": [_line("f", 0.0, 10.0, "spk1"), _line("f", 10.0, 10.0, "spk2")],
        "der": 0.0,
        "jer": 0.0,
    },
    {
        # brief 0.5s speaker dropped entirely -> missed speech + count error + low-activity miss
        "id": "missing_brief_speaker",
        "ref": [_line("f", 0.0, 20.0, "A"), _line("f", 20.0, 0.5, "B")],
        "hyp": [_line("f", 0.0, 20.0, "A")],
        "der": 0.5 / 20.5,  # 0.02439...
        "jer": 0.5,          # A perfect, B fully missed -> (0 + 1)/2
    },
    {
        # two reference speakers collapsed into one hypothesis speaker -> confusion
        "id": "merged_speakers",
        "ref": [_line("f", 0.0, 10.0, "A"), _line("f", 10.0, 10.0, "B")],
        "hyp": [_line("f", 0.0, 20.0, "X")],
        "der": 0.5,          # 10s correct + 10s confusion, total 20
        "jer": None,
    },
    {
        # one reference speaker split into two hypothesis speakers -> confusion
        "id": "split_speaker",
        "ref": [_line("f", 0.0, 20.0, "A")],
        "hyp": [_line("f", 0.0, 10.0, "X"), _line("f", 10.0, 10.0, "Y")],
        "der": 0.5,
        "jer": None,
    },
    {
        # overlapping speech reproduced exactly -> DER 0 and overlap scored as correct
        "id": "overlap_perfect",
        "ref": [_line("f", 0.0, 10.0, "A"), _line("f", 5.0, 10.0, "B")],
        "hyp": [_line("f", 0.0, 10.0, "A"), _line("f", 5.0, 10.0, "B")],
        "der": 0.0,
        "jer": 0.0,
    },
    {
        # hypothesis adds 5s of silence as speech -> false alarm
        "id": "silence_false_alarm",
        "ref": [_line("f", 0.0, 10.0, "A")],
        "hyp": [_line("f", 0.0, 15.0, "A")],
        "der": 0.5,          # 5s FA / 10s total
        "jer": 1.0 / 3.0,    # Jaccard: 1 - inter/union = 1 - 10/15
    },
    {
        # empty hypothesis -> everything missed
        "id": "empty_hypothesis",
        "ref": [_line("f", 0.0, 10.0, "A")],
        "hyp": [],
        "der": 1.0,
        "jer": 1.0,
    },
]

# Invalid RTTM cases: the parser must reject them, not silently skip.
INVALID_RTTM = {
    "bad_onset": "SPEAKER f 1 -1.0 5.0 <NA> <NA> A <NA> <NA>\n",
    "zero_duration": "SPEAKER f 1 0.0 0.0 <NA> <NA> A <NA> <NA>\n",
    "non_numeric": "SPEAKER f 1 abc 5.0 <NA> <NA> A <NA> <NA>\n",
    "too_few_fields": "SPEAKER f 1 0.0 <NA>\n",
}


def fixture_rttm(case: dict) -> tuple[str, str]:
    return "\n".join(case["ref"]) + "\n", "\n".join(case["hyp"]) + "\n"
