"""GPU-free checks for interrupted Kaggle recording checkpoints."""
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kaggle"))
from run_pilot import completed


def test_orphaned_rttm_is_retried(tmp_path):
    (tmp_path / 'HI-01.rttm').write_text('SPEAKER f 1 0 1 <NA> <NA> S0 <NA> <NA>\n')
    assert not completed(str(tmp_path), 'HI-01')


def test_error_metadata_is_retried_even_with_output(tmp_path):
    (tmp_path / 'HI-01.rttm').write_text('SPEAKER f 1 0 1 <NA> <NA> S0 <NA> <NA>\n')
    (tmp_path / 'HI-01.json').write_text(json.dumps({'status': 'error'}))
    assert not completed(str(tmp_path), 'HI-01')


def test_empty_rttm_is_retried_even_with_success_metadata(tmp_path):
    (tmp_path / 'HI-01.rttm').touch()
    (tmp_path / 'HI-01.json').write_text(json.dumps({'status': 'ok'}))
    assert not completed(str(tmp_path), 'HI-01')


def test_successful_complete_unit_is_resumable(tmp_path):
    (tmp_path / 'HI-01.rttm').write_text('SPEAKER f 1 0 1 <NA> <NA> S0 <NA> <NA>\n')
    (tmp_path / 'HI-01.json').write_text(json.dumps({'status': 'ok'}))
    assert completed(str(tmp_path), 'HI-01')
