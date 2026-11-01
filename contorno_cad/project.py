"""Formato local versionado. JSON é dado; nunca executamos conteúdo importado."""
from .i18n import t
import base64
import copy
import json
import math
import hashlib


def new_project():
    return {"schema_version": 1, "name": t("Novo projeto"), "mode": "cap", "profile": [], "pixel_profile": [], "calibration": {}, "image": None,
            "params": {"shoulder_height": 39.0, "dome_rise": 6.0, "dome_shape": 1.0, "inner_diameter": 22.22, "socket_depth": 30.0, "depth": 10.0},
            "operations": [], "primitives": [], "assumptions": ["Altura de referência: aproximadamente 45 mm, a confirmar.", "22,22 mm é diâmetro nominal do tubo; a folga do encaixe deve ser ajustada após medição.", "Diâmetros externos inferidos da silhueta são aproximações sujeitas à perspectiva.", "Elevação de 6 mm e encaixe de 30 mm são hipóteses editáveis."]}


def set_image(project, data, filename):
    project["image"] = {"filename": filename, "base64": base64.b64encode(data).decode("ascii")}


def image_bytes(project):
    if not project.get("image"):
        return None
    return base64.b64decode(project["image"]["base64"], validate=True)


def dumps(project):
    return json.dumps(project, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")


def loads(data):
    if len(data) > 60 * 1024 * 1024:
        raise ValueError(t('Projeto acima de 60 MB.'))
    project = json.loads(data)
    if not isinstance(project, dict) or project.get("schema_version") != 1:
        raise ValueError(t('Versão de projeto não suportada. Use um JSON Contorno CAD versão 1.'))
    if project.get("mode") not in {"cap", "revolution", "extrusion", "assisted", "import"}:
        raise ValueError(t('Modo de construção inválido.'))
    if len(project.get("profile", [])) > 2000 or len(project.get("operations", [])) > 100:
        raise ValueError(t('Projeto com pontos ou operações demais.'))
    for p in project.get("profile", []):
        if not all(math.isfinite(float(p[k])) for k in ("x", "y")):
            raise ValueError(t('O perfil contém coordenadas inválidas.'))
    return project


def signature(project):
    return hashlib.sha256(dumps(project)).hexdigest()


def clone(project):
    return copy.deepcopy(project)
