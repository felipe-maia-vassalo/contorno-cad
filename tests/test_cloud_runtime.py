"""Cloud copy/guard regressions and an actual Streamlit/CAD smoke test."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

import pytest
from streamlit.testing.v1 import AppTest

from contorno_cad import cloud_runtime

ROOT = Path(__file__).resolve().parents[1]


def fake_source(monkeypatch, tmp_path):
    source = tmp_path / "read-only-managed" / "casadi"
    source.mkdir(parents=True)
    for name in ["__init__.py", "casadi.py", "_casadi.so", "libcoinmetis.so"]:
        (source / name).write_text("test fixture: " + name)
    (source / "LICENSE.txt").write_text("fixture core notice")
    monkeypatch.setattr(cloud_runtime.runtime, "_localizar", lambda: source)
    monkeypatch.setattr(cloud_runtime, "_state_root", lambda: tmp_path / "owned")
    (tmp_path / "owned").mkdir()
    calls = []
    monkeypatch.setattr(cloud_runtime, "_import_test", lambda package: calls.append(package))
    monkeypatch.delitem(sys.modules, "casadi", raising=False)
    monkeypatch.setattr(sys, "path", list(sys.path))
    return source, calls


def test_read_only_source_is_unchanged_and_optional_solver_is_not_copied(monkeypatch, tmp_path):
    source, calls = fake_source(monkeypatch, tmp_path)
    before = {p.name: p.read_bytes() for p in source.iterdir()}
    source.chmod(0o555)
    try:
        report = cloud_runtime.ensure_cloud_runtime()
        target = tmp_path / "owned/site/casadi"
        assert report["core_import_test_passed"]
        assert not (target / "libcoinmetis.so").exists()
        assert (target / "contorno_legal/LICENSE.txt").read_text() == "fixture core notice"
        assert {p.name: p.read_bytes() for p in source.iterdir()} == before
        assert len(calls) == 1
    finally:
        source.chmod(0o755)


def test_concurrent_visitors_build_one_selected_copy(monkeypatch, tmp_path):
    _, calls = fake_source(monkeypatch, tmp_path)
    with ThreadPoolExecutor(2) as pool:
        reports = list(pool.map(lambda _: cloud_runtime.ensure_cloud_runtime(), range(2)))
    assert len(calls) == 1
    assert all(r["hosting_mode"] == "app-owned-selected-copy" for r in reports)


def test_changed_copy_is_rejected_without_repair(monkeypatch, tmp_path):
    _, calls = fake_source(monkeypatch, tmp_path)
    cloud_runtime.ensure_cloud_runtime()
    altered = tmp_path / "owned/site/casadi/casadi.py"
    altered.write_text("changed")
    with pytest.raises(RuntimeError, match="Changed or external"):
        cloud_runtime.ensure_cloud_runtime()
    assert altered.read_text() == "changed" and len(calls) == 1


def test_real_selected_copy_loads_native_core_in_fresh_process(monkeypatch, tmp_path):
    source = cloud_runtime.runtime._localizar()
    monkeypatch.setattr(cloud_runtime, "_state_root", lambda: tmp_path)
    target = tmp_path / "selected/casadi"
    cloud_runtime._create_selected_copy(source, target)
    report = cloud_runtime.runtime.verificar_pacote(target)
    assert report["core_import_test_passed"]
    assert "libcoinmetis.so" not in report["retained_files"]


def test_online_entry_runs_real_cad_example_and_exports():
    at = AppTest.from_file(str(ROOT / "online_cad.py"), default_timeout=90).run()
    assert not at.exception and not at.error
    assert any("Online evaluation demo" in x.value for x in at.caption)
    assert any(x.value == "Assisted reconstruction · online · mm" for x in at.caption)
    next(b for b in at.button if b.label == "Open calibrated end cap example").click().run()
    next(r for r in at.radio if r.label == "Workflow").set_value("Editor CAD").run()
    next(b for b in at.button if b.label == "Generate / update model").click().run()
    assert not at.exception and not at.error
    assert at.session_state["model"].val().isValid()
    next(r for r in at.radio if r.label == "Workflow").set_value("Exportar projeto").run()
    next(b for b in at.button if b.label == "Validate geometry and prepare files").click().run()
    assert not at.exception and not at.error
    assert {"modelo.step", "modelo.stl"} <= at.session_state["exports"].keys()
