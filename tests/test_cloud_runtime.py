"""Hosted first-run preparation and actual Streamlit/CAD smoke verification."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from contorno_cad import cloud_runtime

ROOT = Path(__file__).resolve().parents[1]


def stub_runtime(monkeypatch, tmp_path):
    calls = []
    marker = tmp_path / cloud_runtime.runtime.MARCADOR
    monkeypatch.setattr(cloud_runtime, "_process_lock", nullcontext)
    monkeypatch.setattr(cloud_runtime.runtime, "_localizar", lambda: tmp_path)

    def prepare():
        calls.append("prepare")
        marker.write_text("valid")

    def verify():
        calls.append("verify")
        if marker.read_text() != "valid":
            raise RuntimeError("Changed runtime")
        return {"verified": True}

    monkeypatch.setattr(cloud_runtime.runtime, "preparar", prepare)
    monkeypatch.setattr(cloud_runtime.runtime, "verificar_instalacao", verify)
    return marker, calls


def test_missing_manifest_prepares_once_for_concurrent_visitors(monkeypatch, tmp_path):
    _, calls = stub_runtime(monkeypatch, tmp_path)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: cloud_runtime.ensure_cloud_runtime(), range(2)))
    assert results == [{"verified": True}] * 2
    assert calls.count("prepare") == 1
    assert calls.count("verify") == 2


def test_changed_manifest_is_not_automatically_repaired(monkeypatch, tmp_path):
    marker, calls = stub_runtime(monkeypatch, tmp_path)
    marker.write_text("changed")
    with pytest.raises(RuntimeError, match="Changed runtime"):
        cloud_runtime.ensure_cloud_runtime()
    assert calls == ["verify"]
    assert marker.read_text() == "changed"


def test_online_entry_runs_real_cad_example_and_exports():
    at = AppTest.from_file(str(ROOT / "online_cad.py"), default_timeout=90).run()
    assert not at.exception and not at.error
    assert any("Online evaluation demo" in x.value for x in at.caption)
    next(b for b in at.button if b.label == "Open calibrated end cap example").click().run()
    next(r for r in at.radio if r.label == "Workflow").set_value("Editor CAD").run()
    next(b for b in at.button if b.label == "Generate / update model").click().run()
    assert not at.exception and not at.error
    assert at.session_state["model"].val().isValid()
    next(r for r in at.radio if r.label == "Workflow").set_value("Exportar projeto").run()
    next(b for b in at.button if b.label == "Validate geometry and prepare files").click().run()
    assert not at.exception and not at.error
    assert {"modelo.step", "modelo.stl"} <= at.session_state["exports"].keys()
