"""Harness validation: fixtures + pyannote.metrics <-> nryant/dscore cross-check.

Run with:  .venv-harness/bin/python -m pytest harness/test_scoring.py -v
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from rttm import parse_rttm, turns_to_annotation  # noqa: E402
from scoring import score_pair, count_metrics  # noqa: E402
from fixtures import FIXTURES, INVALID_RTTM, fixture_rttm  # noqa: E402

FILE_ID = "f"


def _ann(rttm_text: str, uem=None):
    turns = parse_rttm(rttm_text)
    return turns_to_annotation(turns, FILE_ID, uem=uem)


@pytest.mark.parametrize("case", FIXTURES, ids=[c["id"] for c in FIXTURES])
def test_fixture_der_jer(case):
    ref_rttm, hyp_rttm = fixture_rttm(case)
    ref = _ann(ref_rttm)
    hyp = _ann(hyp_rttm)
    r = score_pair(ref, hyp)

    if case["der"] is not None:
        assert r["der"] == pytest.approx(case["der"], abs=1e-6), (
            f"{case['id']}: DER {r['der']} != expected {case['der']}")
    if case["jer"] is not None:
        assert r["jer"] == pytest.approx(case["jer"], abs=1e-6), (
            f"{case['id']}: JER {r['jer']} != expected {case['jer']}")


@pytest.mark.parametrize("name", list(INVALID_RTTM), ids=list(INVALID_RTTM))
def test_invalid_rttm_rejected(name):
    with pytest.raises(ValueError):
        parse_rttm(INVALID_RTTM[name])


def test_missing_brief_speaker_counts_and_low_activity():
    case = next(c for c in FIXTURES if c["id"] == "missing_brief_speaker")
    ref_rttm, hyp_rttm = fixture_rttm(case)
    ref, hyp = _ann(ref_rttm), _ann(hyp_rttm)
    r = score_pair(ref, hyp)
    assert r["ref_speaker_count"] == 2
    assert r["hyp_speaker_count"] == 1
    low = r["low_activity"]
    assert low["n_low"] == 1
    assert low["n_recovered"] == 0
    assert low["recall"] == 0.0


def test_overlap_der_computed():
    case = next(c for c in FIXTURES if c["id"] == "overlap_perfect")
    ref_rttm, hyp_rttm = fixture_rttm(case)
    ref, hyp = _ann(ref_rttm), _ann(hyp_rttm)
    r = score_pair(ref, hyp)
    # ref has overlap in [5,10]; perfect hyp -> overlap DER 0
    assert r["overlap_der"] == pytest.approx(0.0, abs=1e-6)


def test_der_components_sum():
    case = next(c for c in FIXTURES if c["id"] == "silence_false_alarm")
    ref_rttm, hyp_rttm = fixture_rttm(case)
    ref, hyp = _ann(ref_rttm), _ann(hyp_rttm)
    r = score_pair(ref, hyp)
    c = r["components"]
    # missed + false alarm + confusion should equal DER
    assert c["missed"] + c["false_alarm"] + c["confusion"] == pytest.approx(r["der"], abs=1e-6)


def test_count_metrics_aggregate():
    results = [
        {"ref_speaker_count": 3, "hyp_speaker_count": 3},
        {"ref_speaker_count": 3, "hyp_speaker_count": 4},
        {"ref_speaker_count": 2, "hyp_speaker_count": 1},
        {"ref_speaker_count": 2, "hyp_speaker_count": 2},
    ]
    agg = count_metrics(results)
    assert agg["exact_count_accuracy"] == 0.5
    assert agg["count_mae"] == pytest.approx(0.5)
    assert agg["count_bias"] == pytest.approx(0.0)


def test_zero_collar_penalizes_boundary_error():
    # A 50ms boundary shift must be scored as error at 0 collar.
    ref = _ann("SPEAKER f 1 0.0 10.0 <NA> <NA> A <NA> <NA>\n")
    hyp = _ann("SPEAKER f 1 0.0 9.95 <NA> <NA> A <NA> <NA>\n")
    r = score_pair(ref, hyp, collar=0.0)
    assert r["der"] > 0.0
    # and forgiven at 250 ms collar
    r250 = score_pair(ref, hyp, collar=0.250)
    assert r250["der"] == pytest.approx(0.0, abs=1e-6)


# --- cross-check against nryant/dscore (DIHARD reference scorer) ---

def test_crosscheck_available():
    from crosscheck import nryant_available
    assert nryant_available(), "nryant/dscore md-eval Perl script is not runnable"


@pytest.mark.parametrize(
    "case", [c for c in FIXTURES if c["id"] != "empty_hypothesis"],
    ids=[c["id"] for c in FIXTURES if c["id"] != "empty_hypothesis"],
)
def test_crosscheck_pyannote_vs_nryant(case):
    from crosscheck import nryant_der_jer
    ref_rttm, hyp_rttm = fixture_rttm(case)
    ref, hyp = _ann(ref_rttm), _ann(hyp_rttm)
    py = score_pair(ref, hyp)
    n = nryant_der_jer(ref_rttm, hyp_rttm, file_id=FILE_ID)
    assert py["der"] == pytest.approx(n["der"], abs=2e-2), (
        f"{case['id']}: pyannote DER {py['der']} vs nryant {n['der']}")
    assert py["jer"] == pytest.approx(n["jer"], abs=3e-2), (
        f"{case['id']}: pyannote JER {py['jer']} vs nryant {n['jer']}")
