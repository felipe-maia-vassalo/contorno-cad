"""Calibração explícita, edição numérica e coordenadas do perfil."""
from .i18n import t
import numpy as np
from scipy.interpolate import PchipInterpolator


def calibration_scale(points, distance_mm):
    if len(points) != 2:
        raise ValueError(t('Selecione exatamente dois pontos para calibrar.'))
    distance = float(np.linalg.norm(np.asarray(points[1], float) - np.asarray(points[0], float)))
    if distance < 1 or not np.isfinite(distance_mm) or distance_mm <= 0:
        raise ValueError(t('A distância real deve ser positiva e os pontos devem ser diferentes.'))
    return float(distance_mm) / distance


def pixels_to_mm(points, scale, origin):
    if not scale or scale <= 0:
        raise ValueError(t('Calibre a fotografia antes de criar o perfil em milímetros.'))
    result = []
    for p in points:
        q = dict(p)
        q.update(x=(float(p["x"]) - origin[0]) * scale, y=(origin[1] - float(p["y"])) * scale)
        if p.get("kind") == "arc":
            q.update(mid_x=(p["mid_x"] - origin[0]) * scale, mid_y=(origin[1] - p["mid_y"]) * scale)
        for key in ("tangent_start", "tangent_end"):
            if p.get(key) is not None:
                q[key] = [p[key][0] * scale, -p[key][1] * scale]
        result.append(q)
    return result


def mm_to_pixels(points, scale, origin):
    result = []
    for p in points:
        q = dict(p)
        q.update(x=origin[0] + p["x"] / scale, y=origin[1] - p["y"] / scale)
        if p.get("kind") == "arc":
            q.update(mid_x=origin[0] + p["mid_x"] / scale, mid_y=origin[1] - p["mid_y"] / scale)
        for key in ("tangent_start", "tangent_end"):
            if p.get(key) is not None:
                q[key] = [p[key][0] / scale, -p[key][1] / scale]
        result.append(q)
    return result


def smooth_wall(points, samples=16):
    if len(points) < 3:
        raise ValueError(t('Suavização exige pelo menos três pontos.'))
    arr = np.asarray([[p["x"], p["y"]] for p in points], float)
    arr = arr[np.argsort(arr[:, 1])]
    if np.any(np.diff(arr[:, 1]) < 1e-8):
        raise ValueError(t('Para suavizar uma lateral, cada ponto deve ter uma altura distinta.'))
    yy = np.linspace(arr[0, 1], arr[-1, 1], samples)
    xx = PchipInterpolator(arr[:, 1], arr[:, 0])(yy)
    return [{"x": float(x), "y": float(y), "kind": "spline"} for x, y in zip(xx, yy)]
