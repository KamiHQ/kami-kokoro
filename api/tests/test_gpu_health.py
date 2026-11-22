import os
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.src.core import gpu_health
from api.src.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def marker_path(tmp_path):
    path = str(tmp_path / "kokoro_cuda_oom")
    with patch.object(gpu_health, "OOM_MARKER_PATH", path):
        yield path


def test_is_cuda_oom_matches_message():
    assert gpu_health.is_cuda_oom(RuntimeError("CUDA out of memory. Tried to allocate"))
    assert not gpu_health.is_cuda_oom(RuntimeError("something else"))


def test_health_ok_without_oom():
    with patch.object(gpu_health, "probe_cuda", return_value=None):
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_health_503_after_recorded_oom_until_recovered(marker_path):
    gpu_health.record_cuda_oom()
    with patch.object(gpu_health, "probe_cuda", return_value="only 3 MiB free"):
        response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert os.path.exists(marker_path)

    with patch.object(gpu_health, "probe_cuda", return_value=None):
        response = client.get("/health")
    assert response.status_code == 200
    assert not os.path.exists(marker_path)


def test_recovery_does_not_delete_oom_recorded_during_probe(marker_path):
    gpu_health.record_cuda_oom()
    original = open(marker_path).read()
    time.sleep(0.01)

    def probe_then_other_worker_records(min_free_bytes=0, record_oom=True):
        # Simulates another worker publishing a newer OOM while we probe. The
        # lock makes that writer wait, so recovery completes first and the
        # newer marker survives.
        import threading

        writer = threading.Thread(target=gpu_health.record_cuda_oom)
        writer.start()
        writer.join(timeout=0.2)
        assert writer.is_alive()
        probe_then_other_worker_records.writer = writer
        return None

    with patch.object(gpu_health, "probe_cuda", probe_then_other_worker_records):
        assert gpu_health.check_health() is None

    probe_then_other_worker_records.writer.join(timeout=5)
    assert os.path.exists(marker_path)
    assert open(marker_path).read() != original


def test_record_cuda_oom_leaves_no_temp_files(marker_path):
    gpu_health.record_cuda_oom()
    gpu_health.record_cuda_oom()
    leftovers = [f for f in os.listdir(os.path.dirname(marker_path)) if f.endswith(".tmp")]
    assert leftovers == []


def test_oom_marker_expires(marker_path):
    gpu_health.record_cuda_oom()
    old = time.time() - gpu_health.OOM_UNHEALTHY_SECONDS - 1
    with open(marker_path, "w") as f:
        f.write(str(old))
    assert gpu_health.recent_cuda_oom_age() is None


def test_health_503_when_probe_fails():
    with patch.object(gpu_health, "probe_cuda", return_value="CUDA out of memory"):
        response = client.get("/health")
    assert response.status_code == 503
