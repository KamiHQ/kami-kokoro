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


def test_health_503_after_recorded_oom():
    gpu_health.record_cuda_oom()
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"


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
