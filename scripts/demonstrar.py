#!/usr/bin/env python3
"""Demonstração reproduzível com os dois JPEGs reais fornecidos pelo usuário.

Execute da pasta do aplicativo: python scripts/demonstrar.py
As imagens PNG são sobreposições calculadas, não capturas de tela do aplicativo.
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
import trimesh

from contorno_cad.cad import build_model, validate_solid
from contorno_cad.imaging import png_bytes, process_image, read_image, right_wall
from contorno_cad.io3d import (export_bundle, export_project_zip, geometry_report,
                               import_model, transform_component)
from contorno_cad.profiles import calibration_scale, pixels_to_mm
from contorno_cad.project import clone, dumps, image_bytes, loads, new_project, set_image, signature
from contorno_cad.viewer import mesh_from_model


def _write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def _write_bundle(directory: Path, files: dict):
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (directory / name).write_bytes(data)


def _profile_overlay(rgb, pixel_points, calibration_points, origin):
    overlay = rgb.copy()
    points = np.asarray([[round(p["x"]), round(p["y"])] for p in pixel_points], np.int32)
    cv2.polylines(overlay, [points], False, (0, 125, 255), 3)
    for i, point in enumerate(points):
        cv2.circle(overlay, tuple(point), 5, (255, 125, 0), -1)
        cv2.putText(overlay, str(i + 1), tuple(point + [7, 0]), cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 80, 200), 1)
    p0, p1 = (tuple(round(v) for v in p) for p in calibration_points)
    cv2.line(overlay, p0, p1, (230, 50, 160), 2)
    cv2.putText(overlay, "45 mm aprox.", (p0[0] + 5, (p0[1] + p1[1]) // 2),
                cv2.FONT_HERSHEY_SIMPLEX, .5, (210, 20, 130), 2)
    axis = round(origin[0])
    cv2.line(overlay, (axis, 0), (axis, rgb.shape[0] - 1), (40, 180, 80), 1)
    return overlay


def _green_dome(rgb):
    """Controles relativos da anotação verde; não mede alturas físicas do topo."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, np.array([35, 90, 90]), np.array([90, 255, 255]))
    yy, xx = np.nonzero(mask)
    if len(xx) < 100:
        raise ValueError("A anotação verde não foi localizada na fotografia branca.")
    axis = (float(xx.min()) + float(xx.max())) / 2
    edge = float(xx.max()) - 5
    crown_y = float(np.median(yy[np.abs(xx - axis) < 5]))
    shoulder_y = float(np.median(yy[np.abs(xx - edge) < 3]))
    if shoulder_y <= crown_y:
        raise ValueError("Anotação verde sem elevação identificável.")
    controls, selected = [], []
    for relative_radius in (.9, .75, .5, .25):
        x = axis + (edge - axis) * relative_radius
        y = float(np.median(yy[np.abs(xx - x) < 3]))
        relative_height = float(np.clip((shoulder_y - y) / (shoulder_y - crown_y), 0, 1))
        controls.append({"r": relative_radius, "h": relative_height})
        selected.append([x, y])
    overlay = rgb.copy()
    for x, y in selected:
        cv2.circle(overlay, (round(x), round(y)), 7, (220, 20, 160), -1)
    return controls, overlay, {"pixels_verdes": int(len(xx)), "eixo_marcacao_px": axis,
                               "ombro_marcacao_px": [edge, shoulder_y],
                               "coroa_marcacao_px": [axis, crown_y], "controles_relativos": controls}


def _from_jpeg(source: Path, settings: dict, name: str, *, green=False):
    data = source.read_bytes()
    rgb = read_image(data)
    processed = process_image(rgb, settings)
    if not processed["contours"]:
        raise AssertionError("A fotografia real não produziu contornos.")
    pixel_profile, frame = right_wall(processed["contours"][0], samples=12)
    x, y, width, height = frame["bounds"]
    # Dois pontos explicitamente selecionados no eixo da silhueta. 45 mm é
    # a altura aproximada comunicada pelo usuário, não uma medição desta imagem.
    calibration_points = [[frame["axis_x"], float(y)],
                          [frame["axis_x"], float(frame["baseline_y"])]]
    scale = calibration_scale(calibration_points, 45.0)
    origin = [frame["axis_x"], frame["baseline_y"]]
    profile = pixels_to_mm(pixel_profile, scale, origin)
    project = new_project()
    project.update(name=name, mode="cap", pixel_profile=pixel_profile, profile=profile,
                   image_settings=settings,
                   calibration={"points_px": calibration_points, "distance_mm": 45.0,
                                "mm_per_pixel": scale, "origin_px": origin,
                                "points": calibration_points, "scale": scale,
                                "origin": origin, "axis_x": frame["axis_x"],
                                "approximate": True})
    project["params"].update(shoulder_height=39.0, dome_rise=6.0,
                              dome_shape=1.0, inner_diameter=22.22, socket_depth=30.0)
    project["assumptions"].extend([
        "Os pontos laterais foram extraídos da silhueta direita do primeiro contorno.",
        "Base e topo da foto são regiões em perspectiva; o recorte da lateral elimina suas extremidades.",
        "O intervalo vertical amostrado é remapeado para ombro de 39 mm; não é uma cópia dimensional exata.",
        "O topo de 6 mm é reconstrução assistida; a foto preta não contém essa superfície abaulada."])
    set_image(project, data, source.name)
    evidence = {"arquivo": source.name, "bytes_jpeg": len(data), "formato": "JPEG",
                "resolucao_px": {"largura": rgb.shape[1], "altura": rgb.shape[0]},
                "parametros_processamento": settings, "contornos_detectados": len(processed["contours"]),
                "pontos_contorno_bruto": len(processed["contours"][0]),
                "area_contorno_px2": float(cv2.contourArea(processed["contours"][0])),
                "limites_contorno_xywh_px": [x, y, width, height],
                "calibracao": project["calibration"], "pontos_perfil": len(profile),
                "raios_aproximados_mm": {"minimo": min(p["x"] for p in profile),
                                            "maximo": max(p["x"] for p in profile)}}
    images = {"contornos_detectados.png": png_bytes(processed["overlay"]),
              "mascara_processada.png": png_bytes(np.repeat(processed["mask"][:, :, None], 3, axis=2)),
              "perfil_sobre_fotografia.png": png_bytes(_profile_overlay(rgb, pixel_profile, calibration_points, origin))}
    if green:
        controls, overlay, marker_report = _green_dome(rgb)
        project["params"]["dome_controls"] = controls
        project["assumptions"].append("Formato do topo extraído da anotação verde, normalizado para elevação hipotética de 6 mm.")
        evidence["marcacao_verde"] = marker_report
        images["controles_curva_verde.png"] = png_bytes(overlay)
    return project, images, evidence


def run_demo(output_dir: Path | str | None = None) -> dict:
    output = Path(output_dir) if output_dir is not None else ROOT / "examples"
    output.mkdir(parents=True, exist_ok=True)
    settings = {"crop": [20, 25, 495, 600], "method": "Escuro", "threshold": 180,
                "blur": 3, "close": 5, "min_area": 1000}
    project, images, evidence = _from_jpeg(ROOT / "examples/ponteira_referencia.jpeg", settings,
                                          "Ponteira — fotografia real calibrada aproximadamente")
    restored = loads(dumps(project))
    assert signature(project) == signature(restored)
    assert image_bytes(restored) == (ROOT / "examples/ponteira_referencia.jpeg").read_bytes()
    baseline = build_model(restored)
    baseline_report = validate_solid(baseline)
    assert baseline_report["valid"]
    original_bundle = export_bundle(baseline, project)
    _write_bundle(output, original_bundle)
    _write_bundle(output, images)
    (output / "demo_project.json").write_bytes(dumps(project))
    _write_json(output / "perfil_extraido.json", {"unidade": "mm", "pontos": project["profile"],
                                                  "origem": "silhueta direita da fotografia JPEG; medidas aproximadas"})
    # Alteração efetiva do mesmo projeto, não troca de modelo por uma imagem.
    changed_project = clone(project)
    changed_project["params"]["dome_rise"] = 9.0
    changed = build_model(changed_project)
    changed_report = validate_solid(changed)
    assert changed_report["valid"]
    assert changed_report["volume_mm3"] > baseline_report["volume_mm3"]
    assert changed_report["dimensions_mm"]["z"] > baseline_report["dimensions_mm"]["z"] + 2.9
    changed_bundle = export_bundle(changed, changed_project)
    _write_bundle(output / "modificado", changed_bundle)

    # Importação STEP e STL pelos mesmos caminhos utilizados pela interface.
    step = import_model(original_bundle["modelo.step"], "retorno.step")
    stl = import_model(original_bundle["modelo.stl"], "retorno.stl")
    assert step["kind"] == "cad" and stl["kind"] == "mesh"
    assert geometry_report(stl["components"][0]["mesh"], "mesh")["fabricavel"]

    # Demonstração de formato intermediário aceito pelo fluxo SketchUp.
    # É um GLB/OBJ gerado a partir do sólido deste projeto, não um arquivo .SKP.
    scene = trimesh.Scene()
    mesh = mesh_from_model(baseline)
    scene.add_geometry(mesh, geom_name="corpo", node_name="ponteira_1")
    scene.add_geometry(mesh, geom_name="corpo2", node_name="ponteira_2",
                       transform=trimesh.transformations.translation_matrix([50, 0, 0]))
    glb_bytes = scene.export(file_type="glb")
    obj_text = mesh.export(file_type="obj")
    imported_glb = import_model(glb_bytes, "duas_ponteiras.glb")
    imported_obj = import_model(obj_text.encode("utf-8"), "ponteira.obj")
    assert len(imported_glb["components"]) == 2
    component = imported_glb["components"][0]
    transformed = transform_component(component, translation=(10, 5, 2), rotation=(0, 0, 30), scale=1.1)
    mesh_bundle = export_bundle(transformed["mesh"], {"schema_version": 1, "mode": "import",
                                "source": "duas_ponteiras.glb", "unidade_confirmada": "mm",
                                "transform": {"translation": [10, 5, 2], "rotation": [0, 0, 30], "scale": 1.1}}, "mesh")
    intermediate = output / "importacao"
    _write_bundle(intermediate, mesh_bundle)
    (intermediate / "duas_ponteiras.glb").write_bytes(glb_bytes)
    (intermediate / "ponteira.obj").write_text(obj_text, encoding="utf-8")

    # Segunda fotografia: segmentação distinta e spline guiada pela marca verde.
    white_project, white_images, white_evidence = _from_jpeg(
        ROOT / "examples/ponteira_curva.jpeg",
        {"crop": [170, 100, 1060, 1091], "method": "Fundo colorido", "saturation": 105,
         "blur": 3, "close": 5, "min_area": 1000}, "Ponteira branca — curva da marcação verde", green=True)
    white_model = build_model(white_project)
    white_bundle = export_bundle(white_model, white_project)
    _write_bundle(output / "branca", white_bundle)
    _write_bundle(output / "branca", white_images)

    report = {"tipo_validacao": "automatizada; fotografias JPEG reais e motor OpenCascade real",
              "capturas_de_tela": False,
              "nota_imagens": "PNG são máscaras e sobreposições computadas, não screenshots ou renderizações simuladas.",
              "fotografia_principal": evidence,
              "cad_original": baseline_report, "cad_modificado": changed_report,
              "modificacao": {"parametro": "dome_rise", "antes_mm": 6, "depois_mm": 9,
                              "diferenca_volume_mm3": changed_report["volume_mm3"] - baseline_report["volume_mm3"]},
              "persistencia": {"json_roundtrip_identico": True, "jpeg_preservado": True},
              "exportacao_original": json.loads(original_bundle["relatorio_geometria.json"]),
              "exportacao_modificada": json.loads(changed_bundle["relatorio_geometria.json"]),
              "importacao_intermediaria": {"origem": "gerado deste CAD; não houve execução do SketchUp",
                    "componentes_glb": len(imported_glb["components"]),
                    "componentes_obj": len(imported_obj["components"]),
                    "volume_antes_mm3": float(component["mesh"].volume),
                    "volume_depois_mm3": float(transformed["mesh"].volume),
                    "fator_volume_esperado": 1.1**3,
                    "malha_transformada": geometry_report(transformed["mesh"], "mesh")},
              "segunda_fotografia": white_evidence,
              "cad_curva_verde": validate_solid(white_model)}
    _write_json(output / "relatorio_demonstracao.json", report)
    complete = dict(original_bundle)
    complete.update(images)
    complete["relatorio_demonstracao.json"] = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
    complete["referencia.jpeg"] = image_bytes(project)
    complete["perfil_extraido.json"] = (output / "perfil_extraido.json").read_bytes()
    for name, data in changed_bundle.items():
        complete[f"modificado/{name}"] = data
    for name, data in white_bundle.items():
        complete[f"branca/{name}"] = data
    for name, data in white_images.items():
        complete[f"branca/{name}"] = data
    complete["branca/referencia.jpeg"] = image_bytes(white_project)
    for name, data in mesh_bundle.items():
        complete[f"importacao/{name}"] = data
    complete["importacao/duas_ponteiras.glb"] = glb_bytes
    complete["importacao/ponteira.obj"] = obj_text.encode("utf-8")
    (output / "projeto_ponteira_completo.zip").write_bytes(export_project_zip(complete))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "examples")
    args = parser.parse_args()
    result = run_demo(args.output)
    print(json.dumps({"resultado": "APROVADO", "saida": str(args.output.resolve()),
                      "volume_original_mm3": result["cad_original"]["volume_mm3"],
                      "volume_modificado_mm3": result["cad_modificado"]["volume_mm3"],
                      "altura_original_mm": result["cad_original"]["dimensions_mm"]["z"],
                      "altura_modificada_mm": result["cad_modificado"]["dimensions_mm"]["z"],
                      "step_valido": result["exportacao_original"]["step_reimportado"]["valido"],
                      "stl_fechado": result["exportacao_original"]["stl_reimportado"]["fechado"]},
                     ensure_ascii=False, indent=2))
