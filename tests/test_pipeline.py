"""Fluxo integrado com fotos reais até STL/STEP reimportados e projeto reaberto."""
import io
import json
from pathlib import Path
import zipfile

import pytest

from contorno_cad.cad import build_model, validate_solid
from contorno_cad.project import loads
from scripts.demonstrar import run_demo


def test_complete_real_jpeg_to_cad_pipeline(tmp_path):
    report = run_demo(tmp_path)
    photo = report["fotografia_principal"]
    assert photo["formato"] == "JPEG" and photo["contornos_detectados"] >= 1
    assert photo["calibracao"]["mm_per_pixel"] == pytest.approx(45 / 542)
    assert photo["pontos_perfil"] == 12
    assert report["cad_original"]["valid"] and report["cad_modificado"]["valid"]
    assert report["cad_original"]["dimensions_mm"]["z"] == pytest.approx(45, abs=.001)
    assert report["cad_modificado"]["dimensions_mm"]["z"] == pytest.approx(48, abs=.001)
    assert report["modificacao"]["diferenca_volume_mm3"] > 100
    assert report["exportacao_original"]["stl_reimportado"]["fabricavel"]
    assert report["exportacao_modificada"]["stl_reimportado"]["fabricavel"]
    assert report["exportacao_original"]["step_reimportado"]["valido"]
    assert report["exportacao_original"]["diferenca_volume_step_mm3"] < 1e-5
    assert report["persistencia"]["json_roundtrip_identico"]
    assert report["persistencia"]["jpeg_preservado"]
    restored = loads((tmp_path / "demo_project.json").read_bytes())
    assert validate_solid(build_model(restored))["volume_mm3"] == pytest.approx(report["cad_original"]["volume_mm3"])
    assert len(restored["profile"]) == 12
    assert report["segunda_fotografia"]["marcacao_verde"]["pixels_verdes"] > 5000
    assert len(report["segunda_fotografia"]["marcacao_verde"]["controles_relativos"]) == 4
    assert report["cad_curva_verde"]["valid"]
    imported = report["importacao_intermediaria"]
    assert imported["componentes_glb"] == 2 and imported["componentes_obj"] == 1
    assert imported["volume_depois_mm3"] == pytest.approx(imported["volume_antes_mm3"] * 1.1**3)
    assert imported["malha_transformada"]["fabricavel"]
    for file in ("modelo.stl", "modelo.step", "previa.html", "perfil_extraido.json",
                 "contornos_detectados.png", "mascara_processada.png", "perfil_sobre_fotografia.png",
                 "branca/controles_curva_verde.png", "importacao/duas_ponteiras.glb"):
        assert (tmp_path / file).stat().st_size > 100
    with zipfile.ZipFile(tmp_path / "projeto_ponteira_completo.zip") as archive:
        assert "modelo.step" in archive.namelist()
        assert "modificado/modelo.step" in archive.namelist()
        assert "branca/modelo.step" in archive.namelist()
        assert "branca/controles_curva_verde.png" in archive.namelist()
        assert "importacao/modelo.stl" in archive.namelist()
        assert json.loads(archive.read("projeto.json"))["params"]["dome_rise"] == 6
    assert report["capturas_de_tela"] is False
