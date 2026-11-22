"""CUDA health tracking shared across uvicorn workers.

Each uvicorn worker is a separate process with its own CUDA context, and a
health probe only reaches one of them. When any worker hits a CUDA
out-of-memory error it records a timestamp in a file under the temp directory.
Every worker's /health endpoint reads that file, so the whole container
reports unhealthy no matter which worker serves the probe. The marker is
cleared as soon as a probe sees the GPU has headroom again, so a transient OOM
does not keep the pod failing its probes. The file lives in the container
filesystem, so a restarted container starts clean.

Recording an OOM and the recover-and-clear step both run under an interprocess
file lock, so a recovery check can never delete an OOM recorded after it
started.
"""

import os
import tempfile
import time
from contextlib import contextmanager
from typing import Iterator, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX platforms
    fcntl = None

import torch
from loguru import logger

from .config import settings

OOM_MARKER_PATH = os.environ.get(
    "CUDA_OOM_MARKER_PATH",
    os.path.join(tempfile.gettempdir(), "kokoro_cuda_oom"),
)
# Upper bound on how long a marker counts; recovery normally clears it sooner.
OOM_UNHEALTHY_SECONDS = float(os.environ.get("CUDA_OOM_UNHEALTHY_SECONDS", "300"))
# Free GPU memory required before an OOM marker is considered recovered.
MIN_FREE_BYTES = int(float(os.environ.get("CUDA_MIN_FREE_MIB", "256")) * 1024 * 1024)


def is_cuda_oom(error: BaseException) -> bool:
    """Whether an exception is a CUDA out-of-memory failure."""
    if isinstance(error, torch.cuda.OutOfMemoryError):
        return True
    return "cuda out of memory" in str(error).lower()


@contextmanager
def _marker_lock() -> Iterator[None]:
    """Exclusive interprocess lock guarding marker publication and clearing."""
    if fcntl is None:
        yield
        return
    try:
        lock_path = f"{OOM_MARKER_PATH}.lock"
        lock_file = open(lock_path, "a")
    except OSError as e:
        logger.warning(f"Could not open CUDA OOM lock {lock_path}: {e}")
        yield
        return
    with lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        yield


def record_cuda_oom() -> None:
    """Mark the container as having hit a CUDA OOM, visible to all workers."""
    tmp_path = f"{OOM_MARKER_PATH}.{os.getpid()}.tmp"
    try:
        with _marker_lock():
            with open(tmp_path, "w") as f:
                f.write(str(time.time()))
            os.replace(tmp_path, OOM_MARKER_PATH)
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


def clear_cuda_oom() -> None:
    """Forget a recorded OOM once the GPU has recovered."""
    try:
        os.remove(OOM_MARKER_PATH)
    except FileNotFoundError:
        pass
    except OSError as e:
        logger.warning(f"Could not clear CUDA OOM marker {OOM_MARKER_PATH}: {e}")


def probe_cuda(min_free_bytes: int = 0, record_oom: bool = True) -> Optional[str]:
    """Try a small fresh CUDA allocation in this process.

    When min_free_bytes is set, also require that much free GPU memory
    (device-wide, so it reflects the other workers too).
    Returns an error message if CUDA is unusable, otherwise None.
    """
    if settings.get_device() != "cuda":
        return None
    try:
        tensor = torch.empty(1024 * 1024, dtype=torch.uint8, device="cuda")
        del tensor
        if min_free_bytes:
            free, _ = torch.cuda.mem_get_info()
            if free < min_free_bytes:
                return f"only {free / 1024**2:.0f} MiB of GPU memory free"
        return None
    except Exception as e:
        if record_oom and is_cuda_oom(e):
            record_cuda_oom()
        return str(e)


def _check_recovery() -> Optional[str]:
    """Clear the OOM marker if the GPU has recovered, else report why not.

    The marker is re-read under the lock, so an OOM recorded by another worker
    after the caller's first read is honoured and never deleted by mistake.
    """
    with _marker_lock():
        age = recent_cuda_oom_age()
        if age is None:
            return None
        error = probe_cuda(MIN_FREE_BYTES, record_oom=False)
        if error is not None:
            return f"CUDA out of memory recorded {age:.0f}s ago and not recovered: {error}"
        clear_cuda_oom()
    logger.info(f"GPU recovered from CUDA OOM recorded {age:.0f}s ago")
    return None


def check_health() -> Optional[str]:
    """Return a reason the instance is unhealthy, or None when healthy."""
    if recent_cuda_oom_age() is not None:
        return _check_recovery()
    error = probe_cuda()
    if error is not None:
        return f"CUDA allocation probe failed: {error}"
    return None
