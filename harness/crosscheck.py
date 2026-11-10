"""Cross-check scoring against nryant/dscore (the DIHARD reference scorer).

This exists to prove the primary scorer correct: the same reference/hypothesis
RTTM scored with nryant/dscore (md-eval, 0 ms collar, overlap included) must
match pyannote.metrics to within a small tolerance. See test_scoring.py.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "third_party", "dscore"))

import scorelib.rttm as rttm  # noqa: E402
import scorelib.score as sc  # noqa: E402
import scorelib.uem as uem  # noqa: E402


def nryant_der_jer(
    ref_rttm: str, hyp_rttm: str, file_id: str = "f", uem_regions: List[Tuple[float, float]] | None = None
) -> Dict[str, float]:
    """Score one pair with nryant/dscore and return {'der', 'jer'}.

    Uses a temp dir so the RTTM files and UEM can be passed as paths (nryant's
    loader opens paths). DER is computed by the bundled NIST md-eval Perl script
    with the default 0 ms collar and overlap included.
    """
    with tempfile.TemporaryDirectory() as d:
        rp = os.path.join(d, "ref.rttm")
        hp = os.path.join(d, "hyp.rttm")
        with open(rp, "w", encoding="utf-8") as f:
            f.write(ref_rttm)
        with open(hp, "w", encoding="utf-8") as f:
            f.write(hyp_rttm)

        rt, _, _ = rttm.load_rttm(rp)
        ht, _, _ = rttm.load_rttm(hp)

        if uem_regions:
            u = uem.UEM()
            u[file_id] = list(uem_regions)
        else:
            u = uem.UEM()
            # auto-derive scoring regions from the turns (nryant's UEM() default
            # is empty -> score() would find no regions). Build from ref/hyp extents.
            bounds = []
            for t in list(rt) + list(ht):
                bounds += [t.onset, t.onset + t.dur]
            if bounds:
                u[file_id] = [(min(bounds), max(bounds))]

        file_scores, global_scores = sc.score(rt, ht, u)
        # nryant/dscore reports DER/JER in percent (0-100); convert to fractions.
        return {"der": float(global_scores.der) / 100.0,
                "jer": float(global_scores.jer) / 100.0}


def nryant_available() -> bool:
    """True if the NIST md-eval Perl script is callable (DER depends on it)."""
    script = os.path.join(os.path.dirname(__file__), "..", "third_party", "dscore",
                          "scorelib", "md-eval-22.pl")
    try:
        r = subprocess.run(["perl", script, "-h"], capture_output=True, text=True, timeout=30)
        return r.returncode == 0 or "Usage" in (r.stdout + r.stderr)
    except Exception:
        return False
