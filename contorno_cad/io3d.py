"""Importação, validação e exportação; arquivos inválidos nunca são liberados."""
from __future__ import annotations

from .i18n import t

import io
import json
from pathlib import Path
import tempfile
import zipfile

import numpy as np
import trimesh

from .viewer import (cad_bounds, cad_shape, figure_html, make_figure, mesh_from_model,
                     normalize_cad_tessellation)


def _json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")


def geometry_report(model_or_mesh, kind="cad") -> dict:
    """Inspeção geométrica, sem confundir validade CAD com malha fabricável."""
    if kind == "cad":
        from OCP.BRep import BRep_Tool

        shape = cad_shape(model_or_mesh)
        solids = shape.Solids()
        valid = bool(solids) and shape.isValid() and all(s.isValid() for s in solids)
        shells_closed = bool(solids) and all(
            BRep_Tool.IsClosed_s(shell.wrapped) for solid in solids for shell in solid.Shells())
        report = dict(representacao="sólido CAD", unidade="mm", valido=bool(valid),
                      solidos=len(solids), volume_mm3=float(sum(s.Volume() for s in solids)),
                      limites_mm=cad_bounds(shape).tolist())
        report["fechado"] = bool(valid and shells_closed and report["volume_mm3"] > 0)
        return report
    if kind != "mesh":
        raise ValueError(t('Representação desconhecida.'))
    mesh = mesh_from_model(model_or_mesh, "mesh")
    finite = not mesh.is_empty and np.isfinite(mesh.vertices).all()
    volume = float(mesh.volume) if finite else 0.0
    closed = bool(finite and mesh.is_watertight)
    oriented = bool(finite and mesh.is_winding_consistent)
    return dict(representacao="malha triangular", unidade="mm",
                valido=bool(finite), fechado=closed, orientacao_consistente=oriented,
                volume_positivo=volume > 0, volume_mm3=volume,
                fabricavel=bool(closed and oriented and volume > 0),
                vertices=len(mesh.vertices), triangulos=len(mesh.faces),
                limites_mm=mesh.bounds.tolist() if finite else None)


def _check_cad(model):
    report = geometry_report(model, "cad")
    if not report["valido"] or not report["fechado"]:
        raise ValueError(t('O arquivo não contém sólidos CAD válidos e fechados com volume positivo.'))
    return report


def _check_printable(mesh):
    report = geometry_report(mesh, "mesh")
    if not report["fabricavel"]:
        raise ValueError(t('Exportação STL bloqueada: a malha precisa ser fechada, ter orientação consistente e volume positivo. Repare a malha antes de fabricar.'))
    return report


def import_model(data: bytes, filename: str) -> dict:
    """Lê STEP como B-Rep; formatos triangulados não ganham histórico paramétrico.

    Instâncias e transformações de cenas são preservadas como componentes
    independentes. GLTF exige buffers incorporados (data URI); ZIP/assets externos
    não são resolvidos. Os números dos arquivos de malha precisam ter unidade
    confirmada pelo usuário, pois STL/OBJ não especificam milímetros.
    """
    if not data:
        raise ValueError(t('O arquivo está vazio.'))
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension in ("step", "stp"):
        import cadquery as cq

        with tempfile.TemporaryDirectory(prefix="contorno_import_") as directory:
            path = Path(directory) / "modelo.step"
            path.write_bytes(data)
            try:
                model = cq.importers.importStep(str(path))
                report = _check_cad(model)
            except Exception as exc:
                raise ValueError(t('Não foi possível importar um STEP sólido válido: {v1}', v1=exc)) from exc
        solids = cad_shape(model).Solids()
        components = [dict(name=f"Sólido {i + 1}", model=cq.Workplane("XY").newObject([s]))
                      for i, s in enumerate(solids)]
        return dict(kind="cad", components=components, report=report, units="mm",
                    warnings=["STEP preserva a geometria B-Rep, sem o histórico de operações do arquivo original."])
    if extension == "skp":
        raise ValueError(t('Leitura nativa .SKP não implementada. Exporte OBJ, STL, GLB ou DAE pelo SketchUp/um exportador compatível e importe o formato intermediário.'))
    if extension not in ("stl", "obj", "glb", "gltf", "dae"):
        raise ValueError(t('Formato não suportado. Utilize STEP, STL, OBJ, GLB, GLTF incorporado ou DAE.'))
    if extension == "gltf":
        try:
            document = json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise ValueError(t('O GLTF não é um documento JSON válido.')) from exc
        external = [item.get("uri", "") for group in ("buffers", "images")
                    for item in document.get(group, [])
                    if item.get("uri") and not item["uri"].startswith("data:")]
        if external:
            raise ValueError(t('Este GLTF depende de arquivos externos. Exporte GLB ou GLTF com buffers e imagens incorporados.'))
    try:
        scene = trimesh.load(io.BytesIO(data), file_type=extension, force="scene", process=True)
    except ImportError as exc:
        raise ValueError(t('Leitor DAE indisponível. Instale a dependência opcional pycollada ou exporte OBJ/GLB/STL.')) from exc
    except Exception as exc:
        raise ValueError(t('Falha na leitura do arquivo {v1}: {v3}', v1=extension.upper(), v3=exc)) from exc
    if isinstance(scene, trimesh.Trimesh):
        scene = trimesh.Scene(scene)
    components = []
    for node in scene.graph.nodes_geometry:
        matrix, geometry_name = scene.graph.get(node)
        geometry = scene.geometry[geometry_name]
        if not isinstance(geometry, trimesh.Trimesh) or geometry.is_empty:
            continue
        mesh = geometry.copy()
        mesh.apply_transform(matrix)
        if not np.isfinite(mesh.vertices).all():
            raise ValueError(t('O modelo contém coordenadas não finitas.'))
        components.append(dict(name=str(node), mesh=mesh))
    if not components:
        raise ValueError(t('Não foram encontradas superfícies trianguladas no arquivo.'))
    return dict(kind="mesh", components=components, units="a confirmar",
                warnings=["Malhas não têm histórico nem superfícies CAD paramétricas.",
                          "Confirme a unidade do arquivo: o aplicativo interpreta os valores "
                          "numéricos em mm; use a escala para converter, se necessário.",
                          "Materiais e texturas são referências visuais e não participam da geometria."],
                report={"componentes": len(components)})


def transform_component(component: dict, translation=(0, 0, 0), rotation=(0, 0, 0),
                        scale: float = 1.0) -> dict:
    """Transformação global em torno da origem: escala, rotações X/Y/Z e translação."""
    values = np.asarray([*translation, *rotation, scale], dtype=float)
    if not np.isfinite(values).all() or scale <= 0:
        raise ValueError(t('A escala deve ser positiva e as transformações devem ser finitas.'))
    result = dict(component)
    if "model" in component:
        import cadquery as cq

        shape = cad_shape(component["model"]).scale(float(scale))
        for vector, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), rotation):
            shape = shape.rotate((0, 0, 0), vector, float(angle))
        shape = shape.translate(tuple(float(value) for value in translation))
        result["model"] = cq.Workplane("XY").newObject([shape])
        _check_cad(result["model"])
    elif "mesh" in component:
        mesh = component["mesh"].copy()
        mesh.apply_scale(float(scale))
        matrix = trimesh.transformations.euler_matrix(*np.radians(rotation), axes="sxyz")
        matrix[:3, 3] = translation
        mesh.apply_transform(matrix)
        result["mesh"] = mesh
    else:
        raise ValueError(t('O componente não contém um sólido nem uma malha.'))
    return result


def export_bundle(model_or_mesh, project: dict, kind="cad") -> dict[str, bytes]:
    """Valida os bytes exportados e o retorno STEP antes de disponibilizar arquivos."""
    report = geometry_report(model_or_mesh, kind)
    files = {}
    if kind == "cad":
        import cadquery as cq

        report = _check_cad(model_or_mesh)
        with tempfile.TemporaryDirectory(prefix="contorno_export_") as directory:
            stl_path, step_path = Path(directory) / "modelo.stl", Path(directory) / "modelo.step"
            shape = cad_shape(model_or_mesh)
            cq.exporters.export(shape, str(stl_path), tolerance=0.05, angularTolerance=0.1)
            cq.exporters.export(shape, str(step_path))
            stl_bytes, step_bytes = stl_path.read_bytes(), step_path.read_bytes()
            mesh = trimesh.load(io.BytesIO(stl_bytes), file_type="stl", force="mesh", process=True)
            mesh, tessellation_report = normalize_cad_tessellation(mesh)
            report["normalizacao_tesselacao_cad"] = tessellation_report
            # Exporta e reabre os bytes efetivamente entregues após a normalização.
            # A operação é registrada e não faz reparos topológicos na geometria.
            stl_bytes = mesh.export(file_type="stl")
            mesh = trimesh.load(io.BytesIO(stl_bytes), file_type="stl", force="mesh", process=True)
            report["stl_reimportado"] = _check_printable(mesh)
            reimported = cq.importers.importStep(str(step_path))
            roundtrip = _check_cad(reimported)
            volume_delta = abs(roundtrip["volume_mm3"] - report["volume_mm3"])
            if not np.isclose(roundtrip["volume_mm3"], report["volume_mm3"], rtol=1e-6, atol=1e-6):
                raise ValueError(t('A verificação STEP detectou alteração do volume após reimportar.'))
            if not np.allclose(roundtrip["limites_mm"], report["limites_mm"], rtol=1e-6, atol=1e-5):
                raise ValueError(t('A verificação STEP detectou alteração das dimensões após reimportar.'))
            if roundtrip["solidos"] != report["solidos"]:
                raise ValueError(t('A verificação STEP detectou alteração no número de sólidos.'))
            report["step_reimportado"] = roundtrip
            report["diferenca_volume_step_mm3"] = volume_delta
            files.update({"modelo.stl": stl_bytes, "modelo.step": step_bytes})
    elif kind == "mesh":
        mesh = mesh_from_model(model_or_mesh, kind)
        _check_printable(mesh)
        stl_bytes = mesh.export(file_type="stl")
        restored = trimesh.load(io.BytesIO(stl_bytes), file_type="stl", force="mesh", process=True)
        report["stl_reimportado"] = _check_printable(restored)
        files["modelo.stl"] = stl_bytes
    else:
        raise ValueError(t('Representação desconhecida.'))
    files["previa.html"] = figure_html(make_figure(model_or_mesh, kind))
    files["projeto.json"] = _json_bytes(project)
    files["relatorio_geometria.json"] = _json_bytes(report)
    return files


def export_project_zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(t('Nome inseguro no pacote do projeto.'))
            archive.writestr(name, data)
    return buffer.getvalue()
