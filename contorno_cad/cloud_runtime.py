"""Prepare a dedicated hosted environment before importing the CAD kernel.

Only an absent manifest triggers automatic first-run preparation. A changed or
invalid prepared environment is rejected, preserving the local runtime guard.
"""
from contextlib import contextmanager
from pathlib import Path
import sys
import threading

from scripts import preparar_casadi as runtime

_BOOTSTRAP_LOCK = threading.Lock()


@contextmanager
def _process_lock():
    # Hosted instances can start multiple processes. Keep the lock outside the
    # package because preparation deliberately removes optional package files.
    lock_path = Path(sys.prefix) / ".contorno-cloud-runtime.lock"
    with lock_path.open("a") as handle:
        if sys.platform != "win32":
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if sys.platform != "win32":
                fcntl.flock(handle, fcntl.LOCK_UN)


def ensure_cloud_runtime():
    """Prepare once if missing; verify on every call and reject changed cores."""
    with _BOOTSTRAP_LOCK, _process_lock():
        package = runtime._localizar()  # Enforces dedicated venv/version/platform.
        if not (package / runtime.MARCADOR).exists():
            runtime.preparar()
        return runtime.verificar_instalacao()
