import json
import tempfile
from pathlib import Path
from datetime import date

from src.metrics import DailyMetrics


def test_increment_counter():
    with tempfile.TemporaryDirectory() as tmpdir:
        dm = DailyMetrics(metrics_dir=Path(tmpdir))
        dm.increment("drafts_approved")
        dm.increment("drafts_approved")
        dm.increment("drafts_approved")
        dm.flush()

        filepath = Path(tmpdir) / f"{date.today().isoformat()}.json"
        assert filepath.exists()
        with open(filepath) as f:
            data = json.load(f)
        assert data["counters"]["drafts_approved"] == 3


def test_latency_p95():
    with tempfile.TemporaryDirectory() as tmpdir:
        dm = DailyMetrics(metrics_dir=Path(tmpdir))
        for i in range(20):
            dm.record_latency(0.1 * (i + 1))
        dm.flush()

        filepath = Path(tmpdir) / f"{date.today().isoformat()}.json"
        with open(filepath) as f:
            data = json.load(f)
        assert "api_latency_p95" in data
        sorted_lats = sorted([0.1 * (i + 1) for i in range(20)])
        index = int(len(sorted_lats) * 0.95)
        expected = sorted_lats[index]
        assert data["api_latency_p95"] == expected


def test_approve_reject_ratio():
    dm = DailyMetrics(metrics_dir=Path(tempfile.mkdtemp()))
    dm.increment("drafts_approved")
    dm.increment("drafts_approved")
    dm.increment("drafts_approved")
    dm.increment("drafts_rejected")
    ratio = dm.approve_reject_ratio()
    assert ratio == 0.75


def test_flush_file_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        dm = DailyMetrics(metrics_dir=Path(tmpdir))
        dm.increment("drafts_approved")
        dm.flush()

        filepath = Path(tmpdir) / f"{date.today().isoformat()}.json"
        assert filepath.exists()
        with open(filepath) as f:
            data = json.load(f)
        assert "date" in data
        assert data["date"] == date.today().isoformat()
        assert "counters" in data
        assert data["counters"]["drafts_approved"] == 1


def test_merge_on_write():
    with tempfile.TemporaryDirectory() as tmpdir:
        dm = DailyMetrics(metrics_dir=Path(tmpdir))
        dm.increment("drafts_approved")
        dm.increment("drafts_approved")
        dm.increment("drafts_approved")
        dm.flush()

        dm2 = DailyMetrics(metrics_dir=Path(tmpdir))
        dm2.increment("drafts_approved")
        dm2.increment("drafts_approved")
        dm2.flush()

        filepath = Path(tmpdir) / f"{date.today().isoformat()}.json"
        with open(filepath) as f:
            data = json.load(f)
        assert data["counters"]["drafts_approved"] == 5


def test_empty_metrics():
    with tempfile.TemporaryDirectory() as tmpdir:
        dm = DailyMetrics(metrics_dir=Path(tmpdir))
        dm.flush()

        filepath = Path(tmpdir) / f"{date.today().isoformat()}.json"
        with open(filepath) as f:
            data = json.load(f)
        assert data["counters"] == {}
        assert "api_latency_p95" not in data
