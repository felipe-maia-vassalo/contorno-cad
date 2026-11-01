"""Fluxos reais Streamlit via AppTest, sem alegar interação visual de navegador.

Os projetos/GLB usados em session_state são fixtures explícitas. O caminho da
fotografia usa o botão real de exemplo, não simula um upload de arquivo.
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from contorno_cad import imaging, project as storage
from contorno_cad.cad import validate_solid
from contorno_cad.io3d import export_project_zip


ROOT = Path(__file__).resolve().parents[1]
PAGES = ["Painel inicial", "Imagem para CAD", "Editor de perfil 2D", "Editor CAD",
         "Importar Modelo 3D", "Visualizador 3D", "Exportar projeto"]


def _app(project=None):
    at = AppTest.from_file(str(ROOT / "iniciar_cad.py"), default_timeout=45)
    at.session_state["language"] = "pt"  # Exercise the optional Portuguese UI explicitly.
    if project is not None:
        at.session_state["project"] = storage.clone(project)
    return at.run()


def _clean(at):
    assert not at.exception, [e.message for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    return at


def _widget(items, label):
    return next(widget for widget in items if widget.label == label)


def _click(at, label):
    _widget(at.button, label).click().run()
    return at


def _page(at, name):
    _widget(at.radio, "Fluxo de trabalho").set_value(name).run()
    return at


def _demo():
    return storage.loads((ROOT / "examples/demo_project.json").read_bytes())


def _downloads(at):
    return {item.label: item.proto.url for item in at.get("download_button")}


def test_all_seven_pages_run_with_real_photo_project_fixture():
    at = _clean(_app(_demo()))
    for page in PAGES:
        _clean(_page(at, page))
        assert any(title.value == ("Contorno CAD" if page == PAGES[0] else page)
                   for title in at.title)
    assert at.session_state["project"]["image"]["filename"].endswith(".jpeg")
    assert len(at.session_state["project"]["profile"]) >= 2


def test_real_example_image_button_processes_contour_and_calibrates():
    at = _clean(_page(_app(), "Imagem para CAD"))
    _clean(_click(at, "Carregar fotografia preta"))
    p = at.session_state["project"]
    data = storage.image_bytes(p)
    assert data == (ROOT / "examples/ponteira_referencia.jpeg").read_bytes()
    rgb = imaging.read_image(data)
    assert rgb.shape == (619, 936, 3)
    assert any("Imagem recebida:" in item.value and "936 × 619" in item.value for item in at.success)
    # Os controles executam o próprio process_image utilizado pela interface.
    _widget(at.slider, "Recorte horizontal (pixels)").set_value((20, 495))
    _widget(at.slider, "Recorte vertical (pixels)").set_value((25, 600))
    _widget(at.selectbox, "Método").set_value("Escuro")
    _widget(at.slider, "Limiar claro/escuro (0 = Otsu)").set_value(180)
    _clean(at.run())
    computed = imaging.process_image(rgb, p["image_settings"])
    assert computed["contours"]
    assert np.count_nonzero(computed["mask"]) > 1000
    assert not np.array_equal(computed["overlay"], rgb)
    # Três imagens efetivamente emitidas: original, contornos e máscara OpenCV.
    assert len(at.get("image")) == 3
    assert at.get("image")[0].proto.imgs[0].caption == "Original recebida"
    assert at.get("image")[1].proto.imgs[0].caption == f'Contornos detectados: {len(computed["contours"])}'
    _clean(_click(at, "Usar lateral direita (revolução / ponteira)"))
    assert len(p["pixel_profile"]) >= 2
    _clean(_click(at, "Marcar extremos verticais do contorno para calibrar"))
    _clean(_click(at, "Confirmar calibração e converter perfil para mm"))
    assert p["calibration"]["scale"] > 0
    assert p["calibration"]["distance_mm"] == 45
    assert len(p["profile"]) == len(p["pixel_profile"])
    assert all(point["x"] > 0 for point in p["profile"])
    assert any("Escala confirmada:" in item.value for item in at.success)
    _clean(_click(at, "Continuar para o perfil 2D"))
    _clean(_click(at, "Aplicar coordenadas do perfil"))
    _clean(_click(at, "Continuar para o Editor CAD"))
    _clean(_click(at, "Gerar / atualizar modelo"))
    assert validate_solid(at.session_state["model"])["valid"]


def test_generate_change_invalidates_export_and_save_reopens_in_new_session():
    # Fixture paramétrica calibrada; não é upload via navegador.
    at = _clean(_page(_app(_demo()), "Editor CAD"))
    _clean(_click(at, "Gerar / atualizar modelo"))
    before = validate_solid(at.session_state["model"])
    signature_before = at.session_state["model_signature"]
    assert before["valid"] and before["dimensions_mm"]["z"] == pytest.approx(45, abs=1e-5)
    assert len(at.get("plotly_chart")) == 1
    _clean(_page(at, "Exportar projeto"))
    _clean(_click(at, "Validar geometria e preparar arquivos"))
    files = at.session_state["exports"]
    report = json.loads(files["relatorio_geometria.json"])
    assert report["stl_reimportado"]["fabricavel"] and report["step_reimportado"]["valido"]
    links = _downloads(at)
    assert links["Baixar modelo.stl"] and links["Baixar modelo.step"]
    assert links["Baixar ZIP completo deste projeto"].endswith(".zip")
    with zipfile.ZipFile(io.BytesIO(export_project_zip(files))) as archive:
        assert set(archive.namelist()) == set(files)
        assert archive.read("modelo.step") == files["modelo.step"]
    _clean(_page(at, "Editor CAD"))
    _widget(at.number_input, "Elevação do topo (mm)").set_value(9.0).run()
    _clean(at)
    assert storage.signature(at.session_state["project"]) != signature_before
    assert any("Há alterações no projeto" in item.value for item in at.warning)
    _clean(_page(at, "Exportar projeto"))
    assert "Baixar modelo.stl" not in _downloads(at)
    assert "Baixar modelo.step" not in _downloads(at)
    assert not any(b.label == "Validar geometria e preparar arquivos" for b in at.button)
    _clean(_page(at, "Editor CAD"))
    _clean(_click(at, "Gerar / atualizar modelo"))
    after = validate_solid(at.session_state["model"])
    assert after["dimensions_mm"]["z"] == pytest.approx(48, abs=1e-5)
    assert after["volume_mm3"] > before["volume_mm3"]
    _clean(_page(at, "Exportar projeto"))
    _clean(_click(at, "Validar geometria e preparar arquivos"))
    assert json.loads(at.session_state["exports"]["relatorio_geometria.json"])["step_reimportado"]["valido"]
    saved = storage.dumps(at.session_state["project"])
    restored = storage.loads(saved)
    assert storage.signature(restored) == storage.signature(at.session_state["project"])
    # Nova AppTest = nova sessão. Reabertura via parser real e fixture explícita,
    # sem representar isto como clique no file_uploader do navegador.
    reopened = _clean(_page(_app(restored), "Editor CAD"))
    _clean(_click(reopened, "Gerar / atualizar modelo"))
    reopened_report = validate_solid(reopened.session_state["model"])
    assert reopened_report["volume_mm3"] == pytest.approx(after["volume_mm3"], rel=1e-9)
    assert reopened_report["dimensions_mm"] == pytest.approx(after["dimensions_mm"], abs=1e-6)
    assert storage.image_bytes(reopened.session_state["project"]) == storage.image_bytes(restored)


def test_imported_glb_fixture_selects_component_transforms_and_exports_mesh():
    data = (ROOT / "examples/importacao/duas_ponteiras.glb").read_bytes()
    p = storage.new_project()
    p.update(mode="import", import_source={"filename": "duas_ponteiras.glb",
             "base64": base64.b64encode(data).decode()}, component_index=0,
             transform={"translation": [0, 0, 0], "rotation": [0, 0, 0], "scale": 1.0})
    at = _clean(_page(_app(p), "Importar Modelo 3D"))
    assert len(at.session_state["imported"]["components"]) == 2
    _widget(at.selectbox, "Componente ativo").set_value(1).run()
    _clean(at)
    _clean(_click(at, "Aplicar transformação ao componente"))
    original = at.session_state["model"]
    original_volume, center = float(original.volume), original.bounds.mean(axis=0)
    _widget(at.number_input, "Translação X (mm)").set_value(10.0)
    _widget(at.number_input, "Translação Y (mm)").set_value(5.0)
    _widget(at.number_input, "Translação Z (mm)").set_value(2.0)
    _widget(at.number_input, "Rotação Z (graus)").set_value(90.0)
    _widget(at.number_input, "Escala uniforme / conversão de unidade").set_value(1.1)
    _clean(at.run())
    _clean(_click(at, "Aplicar transformação ao componente"))
    changed = at.session_state["model"]
    expected_center = np.array([-center[1], center[0], center[2]]) * 1.1 + [10, 5, 2]
    assert changed.volume == pytest.approx(original_volume * 1.1**3, rel=1e-6)
    assert changed.bounds.mean(axis=0) == pytest.approx(expected_center, abs=1e-5)
    assert at.session_state["kind"] == "mesh"
    _clean(_page(at, "Exportar projeto"))
    _clean(_click(at, "Validar geometria e preparar arquivos"))
    assert "Baixar modelo.stl" in _downloads(at)
    assert "Baixar modelo.step" not in _downloads(at)
    assert "modelo.step" not in at.session_state["exports"]
    report = json.loads(at.session_state["exports"]["relatorio_geometria.json"])
    assert report["stl_reimportado"]["fabricavel"]


def test_invalid_geometry_explains_failure_and_blocks_outdated_model_export():
    at = _clean(_page(_app(_demo()), "Editor CAD"))
    _clean(_click(at, "Gerar / atualizar modelo"))
    _widget(at.number_input, "Diâmetro interno do encaixe (mm)").set_value(1000.0).run()
    _clean(at)
    _click(at, "Gerar / atualizar modelo")
    assert not at.exception
    assert any("parede" in error.value.lower() or "atravessa" in error.value.lower() for error in at.error)
    _clean(_page(at, "Exportar projeto"))
    assert "Baixar modelo.stl" not in _downloads(at)
    assert "Baixar modelo.step" not in _downloads(at)
    assert not any(b.label == "Validar geometria e preparar arquivos" for b in at.button)
