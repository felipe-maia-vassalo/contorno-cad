"""Round trips reais; não substituem a inspeção visual e dimensional da peça."""
import io
import json
import zipfile

import cadquery as cq
import numpy as np
import pytest
import trimesh

from contorno_cad.io3d import (export_bundle, export_project_zip, geometry_report,
                               import_model, transform_component)
from contorno_cad.viewer import make_figure, mesh_from_model, normalize_cad_tessellation


def test_step_roundtrip_and_transformed_component(tmp_path):
    original = cq.Workplane("XY").box(12, 18, 25).faces(">Z").workplane().hole(4)
    path = tmp_path / "peca.step"
    cq.exporters.export(original, str(path))
    imported = import_model(path.read_bytes(), "peca.STEP")
    assert imported["kind"] == "cad"
    assert len(imported["components"]) == 1
    component = imported["components"][0]
    volume = geometry_report(component["model"])["volume_mm3"]
    moved = transform_component(component, translation=(30, 0, 10), rotation=(0, 0, 90), scale=2)
    assert geometry_report(moved["model"])["volume_mm3"] == pytest.approx(volume * 8)
    assert geometry_report(component["model"])["volume_mm3"] == pytest.approx(volume)
    bounds = np.asarray(geometry_report(moved["model"])["limites_mm"])
    assert bounds.mean(axis=0) == pytest.approx([30, 0, 10])
    files = export_bundle(moved["model"], {"versao": 1, "nome": "Peça de teste"})
    assert {"modelo.stl", "modelo.step", "previa.html", "projeto.json", "relatorio_geometria.json"} <= files.keys()
    report = json.loads(files["relatorio_geometria.json"])
    assert report["stl_reimportado"]["fabricavel"]
    assert report["step_reimportado"]["valido"]
    assert report["diferenca_volume_step_mm3"] < 1e-5
    assert import_model(files["modelo.step"], "retorno.stp")["kind"] == "cad"
    assert import_model(files["modelo.stl"], "retorno.stl")["kind"] == "mesh"
    assert b"plotly.js" in files["previa.html"]
    with zipfile.ZipFile(io.BytesIO(export_project_zip(files))) as archive:
        assert set(archive.namelist()) == set(files)
        assert json.loads(archive.read("projeto.json"))["nome"] == "Peça de teste"


def test_stl_mesh_import_transform_export():
    original = trimesh.creation.cylinder(radius=5, height=15, sections=32)
    result = import_model(original.export(file_type="stl"), "cilindro.stl")
    component = result["components"][0]
    assert result["kind"] == "mesh"
    moved = transform_component(component, translation=(12, 3, 4), rotation=(90, 0, 0), scale=1.5)
    assert moved["mesh"].volume == pytest.approx(component["mesh"].volume * 1.5**3)
    assert moved["mesh"].bounds.mean(axis=0) == pytest.approx([12, 3, 4])
    assert component["mesh"].bounds.mean(axis=0) == pytest.approx([0, 0, 0])
    files = export_bundle(moved["mesh"], {}, kind="mesh")
    assert "modelo.stl" in files and "modelo.step" not in files
    restored = import_model(files["modelo.stl"], "restaurado.stl")["components"][0]["mesh"]
    assert restored.is_watertight and restored.is_winding_consistent


def test_glb_preserves_instances_and_transforms():
    scene = trimesh.Scene()
    box = trimesh.creation.box([2, 3, 4])
    scene.add_geometry(box, geom_name="caixa", node_name="primeira")
    scene.graph.update(frame_to="segunda", frame_from=scene.graph.base_frame,
                       geometry="caixa", matrix=trimesh.transformations.translation_matrix([20, 0, 0]))
    result = import_model(scene.export(file_type="glb"), "cena.glb")
    assert len(result["components"]) == 2
    centers = sorted(round(c["mesh"].bounds.mean(axis=0)[0]) for c in result["components"])
    assert centers == [0, 20]


def test_reject_external_gltf_and_unsupported_skp():
    with pytest.raises(ValueError, match="externos"):
        import_model(json.dumps({"buffers": [{"uri": "modelo.bin"}]}).encode(), "modelo.gltf")
    with pytest.raises(ValueError, match="SKP"):
        import_model(b"sketchup", "modelo.skp")
    with pytest.raises(ValueError, match="vazio"):
        import_model(b"", "modelo.stl")


def test_blocks_open_and_reversed_stl():
    box = trimesh.creation.box()
    opened = trimesh.Trimesh(vertices=box.vertices, faces=box.faces[:-1], process=True)
    assert not geometry_report(opened, "mesh")["fabricavel"]
    with pytest.raises(ValueError, match="bloqueada"):
        export_bundle(opened, {}, "mesh")
    reversed_box = box.copy()
    reversed_box.invert()
    with pytest.raises(ValueError, match="volume positivo"):
        export_bundle(reversed_box, {}, "mesh")
    with pytest.raises(ValueError, match="positiva"):
        transform_component({"name": "caixa", "mesh": box}, scale=-1)


def test_viewer_real_mesh_section_and_cad_edges():
    solid = cq.Workplane("XY").circle(5).extrude(20)
    mesh = mesh_from_model(solid)
    assert mesh.is_watertight
    figure = make_figure(solid, view="Frente", section_z=10)
    assert figure.data[0].type == "mesh3d"
    assert len(figure.data[0].i) == len(mesh.faces)
    assert any(trace.name.startswith("Seção") for trace in figure.data)
    assert any(trace.name == "Arestas CAD" for trace in figure.data)
    assert figure.layout.scene.camera.eye.y == -2.5
    assert len(figure.layout.scene.annotations) == 3


def test_zip_does_not_allow_parent_paths():
    with pytest.raises(ValueError, match="inseguro"):
        export_project_zip({"../fora.txt": b"x"})


def test_cad_tessellation_zero_area_removal_is_explicit_and_preserves_geometry():
    box = trimesh.creation.box([12, 14, 16])
    # O triângulo degenerado usa somente vértices da geometria original.
    dirty = trimesh.Trimesh(vertices=box.vertices,
                            faces=np.vstack([box.faces, [0, 0, 1]]), process=False)
    assert not dirty.is_watertight
    cleaned, report = normalize_cad_tessellation(dirty)
    assert report["triangulos_area_zero_removidos"] == 1
    assert report["triangulos_duplicados_removidos"] == 0
    assert report["diferenca_volume_mm3"] == 0
    assert not report["fechado_antes"] and report["fechado_depois"]
    assert cleaned.volume == dirty.volume
    assert np.array_equal(cleaned.bounds, dirty.bounds)
    assert len(dirty.faces) == len(box.faces) + 1  # origem nunca é mutada


def test_photo_derived_spline_pole_exports_watertight():
    # Regressão da singularidade que só apareceu com o perfil da fotografia real.
    from contorno_cad.cad import build_cap

    wall = [{"x": 15.2893129771, "y": 0, "kind": "line"},
            {"x": 17.8090405870, "y": 7.9838710, "kind": "line"},
            {"x": 12.7158671590, "y": 37.298387, "kind": "line"}]
    model = build_cap(wall, dict(shoulder_height=39, dome_rise=6, dome_shape=1,
                                 inner_diameter=22.22, socket_depth=30))
    files = export_bundle(model, {})
    report = json.loads(files["relatorio_geometria.json"])
    assert report["stl_reimportado"]["fabricavel"]
    assert report["step_reimportado"]["valido"]
    assert abs(report["normalizacao_tesselacao_cad"]["diferenca_volume_mm3"]) < 1e-9


def test_viewing_custom_spline_before_export_does_not_change_cad_dimensions():
    from contorno_cad.cad import build_cap

    wall = [{"x": 13.0743243, "y": 0, "kind": "line"},
            {"x": 19.2957380, "y": 35, "kind": "line"},
            {"x": 17.5181913, "y": 39, "kind": "line"}]
    model = build_cap(wall, dict(shoulder_height=39, dome_rise=6, inner_diameter=22.22,
                                 socket_depth=30, dome_controls=[
                                     {"r": .9, "h": .30833333333333335},
                                     {"r": .75, "h": .5416666666666666},
                                     {"r": .5, "h": .825}, {"r": .25, "h": .9375}]))
    before = np.asarray(geometry_report(model)["limites_mm"])
    make_figure(model)  # OpenCascade agora tem triangulação conservadora em cache.
    after = np.asarray(geometry_report(model)["limites_mm"])
    assert after == pytest.approx(before, abs=1e-9)
    assert after[1, 2] - after[0, 2] == pytest.approx(45.0, abs=1e-6)
    files = export_bundle(model, {})
    report = json.loads(files["relatorio_geometria.json"])
    assert np.asarray(report["step_reimportado"]["limites_mm"]) == pytest.approx(before, abs=1e-6)
