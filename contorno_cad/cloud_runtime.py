"""Use an audited core without modifying a host's read-only Python packages."""
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

from scripts import preparar_casadi as runtime

_BOOTSTRAP_LOCK = threading.Lock()


def _state_root():
    identity = hashlib.sha256(sys.prefix.encode()).hexdigest()[:16]
    root = Path(tempfile.gettempdir()) / f"contorno-cad-runtime-{identity}"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


@contextmanager
def _process_lock():
    # The managed venv can be read-only; lock only app-owned temporary storage.
    with (_state_root() / "bootstrap.lock").open("a") as handle:
        if sys.platform != "win32":
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if sys.platform != "win32":
                fcntl.flock(handle, fcntl.LOCK_UN)


def _import_test(package):
    env = dict(os.environ, PYTHONPATH=str(package.parent))
    code = (
        "import casadi as c; from pathlib import Path; "
        "assert Path(c.__file__).resolve().parent == Path(__import__('sys').argv[1]).resolve(); "
        "assert c.__version__ == '3.8.1'; assert float(c.DM(2)+3)==5"
    )
    result = subprocess.run([sys.executable, "-c", code, str(package)],
                            env=env, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError("The selected cloud core could not load: " + result.stderr[-3000:])


def _create_selected_copy(source, destination):
    # Build outside the published path. Failed/incomplete builds are never used.
    with tempfile.TemporaryDirectory(prefix="build-", dir=_state_root()) as temp:
        package = Path(temp) / "casadi"
        package.mkdir()
        retained = {}
        for item in source.iterdir():
            if item.is_file() and runtime._permitido(item.name):
                if not item.resolve().is_relative_to(source):
                    raise RuntimeError("Core file points outside its source package.")
                shutil.copy2(item, package / item.name)
                retained[item.name] = runtime._hash(package / item.name)
        if not {"__init__.py", "casadi.py"}.issubset(retained) or not any(
            name.startswith("_casadi.") for name in retained
        ):
            raise RuntimeError("The installed wheel lacks the audited core structure.")
        legal = package / runtime.PASTA_LEGAL
        legal.mkdir()
        notices = []
        for item in source.rglob("*"):
            if item.is_file() and any(word in item.name.upper() for word in (
                "LICENSE", "COPYING", "NOTICE", "COPYRIGHT"
            )):
                if not item.resolve().is_relative_to(source):
                    raise RuntimeError("Legal notice points outside its source package.")
                rel = item.relative_to(source)
                target = legal / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
                notices.append({"original_path": rel.as_posix(), "sha256": runtime._hash(target)})
        info = {
            "schema": runtime.ESQUEMA, "version": runtime.VERSAO,
            "platform": sys.platform, "selection": "core-only-no-optional-solvers",
            "retained_files": retained, "archived_notices": notices,
            "removed_top_level": [],
            "excluded_from_copy": sorted(item.name for item in source.iterdir()
                                         if not runtime._permitido(item.name)),
            "core_import_test_passed": False,
            "hosting_mode": "app-owned-selected-copy",
        }
        marker = package / runtime.MARCADOR
        marker.write_text(json.dumps(info, indent=2))
        _import_test(package)
        info["core_import_test_passed"] = True
        marker.write_text(json.dumps(info, indent=2))
        runtime.verificar_pacote(package)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(package, destination)


def ensure_cloud_runtime():
    """Prefer prepared local core; otherwise select an app-owned hosted copy."""
    with _BOOTSTRAP_LOCK:
        source = runtime._localizar()
        if (source / runtime.MARCADOR).exists():
            # Do not repair changed existing installations automatically.
            return runtime.verificar_instalacao()
        with _process_lock():
            package = _state_root() / "site" / "casadi"
            if not package.exists():
                _create_selected_copy(source, package)
            report = runtime.verificar_pacote(package)
            for name, digest in report["retained_files"].items():
                if runtime._hash(source / name) != digest:
                    raise RuntimeError("The installed wheel changed; rebuild the hosted runtime.")
            loaded = sys.modules.get("casadi")
            if loaded and Path(loaded.__file__).resolve().parent != package:
                raise RuntimeError("CAD was imported before the selected hosted runtime.")
            site = str(package.parent)
            if site not in sys.path:
                sys.path.insert(0, site)
                importlib.invalidate_caches()
            return report
