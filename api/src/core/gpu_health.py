"""CUDA health tracking shared across uvicorn workers.

Each uvicorn worker is a separate process with its own CUDA context, and a
health probe only reaches one of them. When any worker hits a CUDA
out-of-memory error it records a timestamp in a file under the temp directory.
Every worker's /health endpoint reads that file, so the whole container
reports unhealthy no matter which worker serves the probe. The file lives in
the container filesystem, so a restarted container starts clean.
"""

import os
import tempfile
import time
from typing import Optional

import torch
from loguru import logger

from .config import settings

OOM_MARKER_PATH = os.environ.get(
    "CUDA_OOM_MARKER_PATH",
    os.path.join(tempfile.gettempdir(), "kokoro_cuda_oom"),
)
# Must outlast the liveness probe's failure window (period * threshold) so a
# failing instance is restarted rather than flapping back to ready.
OOM_UNHEALTHY_SECONDS = float(os.environ.get("CUDA_OOM_UNHEALTHY_SECONDS", "120"))


def is_cuda_oom(error: BaseException) -> bool:
    """Whether an exception is a CUDA out-of-memory failure."""
    if isinstance(error, torch.cuda.OutOfMemoryError):
        return True
    return "cuda out of memory" in str(error).lower()


def record_cuda_oom() -> None:
    """Mark the container as having hit a CUDA OOM, visible to all workers."""
    try:
        with open(OOM_MARKER_PATH, "w") as f:
            f.write(str(time.time()))
    except OSError as e:
        logger.warning(f"Could not write CUDA OOM marker {OOM_MARKER_PATH}: {e}")


def recent_cuda_oom_age() -> Optional[float]:
    """Seconds since the last recorded CUDA OOM, or None if none is recent."""
    try:
        with open(OOM_MARKER_PATH) as f:
            age = time.time() - float(f.read().strip())
    except (OSError, ValueError):
        return None
    return age if age < OOM_UNHEALTHY_SECONDS else None


def probe_cuda() -> Optional[str]:
    """Try a small fresh CUDA allocation in this process.

    Returns an error message if CUDA is unusable, otherwise None.
    """
    if settings.get_device() != "cuda":
        return None
    try:
        tensor = torch.empty(1024 * 1024, dtype=torch.uint8, device="cuda")
        del tensor
        return None
    except Exception as e:
        if is_cuda_oom(e):
            record_cuda_oom()
        return str(e)


def check_health() -> Optional[str]:
    """Return a reason the instance is unhealthy, or None when healthy."""
    age = recent_cuda_oom_age()
    if age is not None:
        return f"CUDA out of memory recorded {age:.0f}s ago"
    error = probe_cuda()
    if error is not None:
        return f"CUDA allocation probe failed: {error}"
    return None
