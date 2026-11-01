"""Motor CAD em milímetros. Nenhuma medida física é inferida de fotografias.

Perfis usam ``x/y``; na revolução, x é o raio e y é a altura.
``kind`` descreve o segmento que chega ao ponto: line, spline ou arc.
Arcos exigem ``mid_x/mid_y`` (um ponto intermediário do arco).

Na ponteira, o perfil descreve a parede externa da base ao ombro. O intervalo
vertical é ajustado a shoulder_height e os raios calibrados são preservados.
A altura total é shoulder_height + dome_rise. O encaixe cilíndrico abre na base.
"""
from __future__ import annotations

from .i18n import t

import math
from typing import Any

import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib


class GeometryError(ValueError):
    """Parâmetro ou operação CAD incompatível com a geometria solicitada."""


_EPS = 1e-7
_SELECTORS = {"all": None, "top": ">Z", "bottom": "<Z", "vertical": "|Z",
              ">Z": ">Z", "<Z": "<Z", "|Z": "|Z", "|X": "|X", "|Y": "|Y"}


def _bounds(shape: cq.Shape) -> cq.BoundBox:
    # AddOptimal sem triangulação: uma tesselação já armazenada não pode mudar
    # as cotas do CAD, especialmente nos polos de superfícies spline.
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped, box, False, False)
    return cq.BoundBox(box)


def _number(value: Any, name: str, *, positive: bool = False,
            nonnegative: bool = False) -> float:
    name = t(name)
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise GeometryError(t('{v0}: informe um número válido.', v0=name)) from None
    if not math.isfinite(number):
        raise GeometryError(t('{v0}: o número deve ser finito.', v0=name))
    if positive and number <= _EPS:
        raise GeometryError(t('{v0}: o valor deve ser maior que zero.', v0=name))
    if nonnegative and number < 0:
        raise GeometryError(t('{v0}: o valor não pode ser negativo.', v0=name))
    return number


def _points(profile: list[dict]) -> list[dict]:
    if not isinstance(profile, list) or len(profile) < 2:
        raise GeometryError(t('Defina pelo menos dois pontos para o perfil.'))
    out = []
    for i, point in enumerate(profile):
        if not isinstance(point, dict):
            raise GeometryError(t('Ponto {v1}: use coordenadas x e y.', v1=i + 1))
        p = dict(point)
        p["x"] = _number(p.get("x"), f"x do ponto {i + 1}")
        p["y"] = _number(p.get("y"), f"y do ponto {i + 1}")
        p["kind"] = p.get("kind", "line")
        if p["kind"] not in ("line", "spline", "arc"):
            raise GeometryError(t('Ponto {v1}: segmento desconhecido: {v3}.', v1=i + 1, v3=p['kind']))
        if out and math.hypot(p["x"] - out[-1]["x"], p["y"] - out[-1]["y"]) < _EPS:
            continue
        out.append(p)
    if len(out) > 2 and math.hypot(out[0]["x"] - out[-1]["x"], out[0]["y"] - out[-1]["y"]) < _EPS:
        out.pop()
    if len(out) < 2:
        raise GeometryError(t('O perfil precisa de pontos distintos.'))
    return out


def _segments(workplane: cq.Workplane, points: list[dict]) -> cq.Workplane:
    """Acrescenta segmentos, já posicionado no ponto imediatamente anterior."""
    index = 0
    while index < len(points):
        p = points[index]
        if p["kind"] == "spline":
            group = []
            while index < len(points) and points[index]["kind"] == "spline":
                group.append(points[index])
                index += 1
            tangents = None
            first_tangent = group[0].get("tangent_start")
            last_tangent = group[-1].get("tangent_end")
            if first_tangent is not None or last_tangent is not None:
                if first_tangent is None or last_tangent is None:
                    raise GeometryError(t('Tangência: informe as duas direções, inicial e final.'))
                try:
                    tangents = [tuple(_number(v, "Tangente") for v in t) for t in (first_tangent, last_tangent)]
                    if any(len(t) != 2 or math.hypot(*t) < _EPS for t in tangents):
                        raise ValueError()
                except (TypeError, ValueError):
                    raise GeometryError(t('Tangentes devem ser vetores [x, y] diferentes de zero.')) from None
            workplane = workplane.spline([(p["x"], p["y"]) for p in group],
                                        includeCurrent=True, tangents=tangents)
            continue
        if p["kind"] == "arc":
            mid_x, mid_y = p.get("mid_x", p.get("mx")), p.get("mid_y", p.get("my"))
            if mid_x is None or mid_y is None:
                raise GeometryError(t('Arco: informe mid_x e mid_y para o ponto intermediário.'))
            workplane = workplane.threePointArc(
                (_number(mid_x, "mid_x do arco"), _number(mid_y, "mid_y do arco")),
                (p["x"], p["y"]))
        else:
            workplane = workplane.lineTo(p["x"], p["y"])
        index += 1
    return workplane


def _checked(model: cq.Workplane, context: str) -> cq.Workplane:
    context = t(context)
    report = validate_solid(model)
    if not report["valid"]:
        raise GeometryError(t('{v0}: o resultado não é um sólido CAD válido e fechado. Revise o perfil, as interseções e as medidas.', v0=context))
    return model


def sample_profile(profile: list[dict], samples_per_edge: int = 24,
                   *, closed: bool = False) -> list[dict]:
    """Amostra as mesmas curvas OCCT usadas no sólido, para sobrepor à foto.

    A sequência percorre o fio em ordem por comprimento de arco. Não substitui
    splines/arcos por linhas entre os pontos de controle. ``closed=True`` inclui
    a aresta de fechamento de um perfil de extrusão/seção fechada.
    """
    points = _points(profile)
    count = int(samples_per_edge)
    if not 2 <= count <= 500:
        raise GeometryError(t('Amostragem: use entre 2 e 500 amostras por aresta.'))
    try:
        wp = cq.Workplane("XY").moveTo(points[0]["x"], points[0]["y"])
        wp = _segments(wp, points[1:])
        wire = wp.close().wire().val() if closed else wp.wire().val()
        number = max(2, len(wire.Edges()) * count + 1)
        output = []
        for i in range(number):
            point = wire.positionAt(i / (number - 1), mode="length")
            output.append({"x": float(point.x), "y": float(point.y)})
        return output
    except GeometryError:
        raise
    except Exception as exc:
        raise GeometryError(t('Não foi possível amostrar o perfil CAD: {v1}', v1=exc)) from exc


def build_extrusion(profile: list[dict], depth: float) -> cq.Workplane:
    points = _points(profile)
    if len(points) < 3:
        raise GeometryError(t('Extrusão: desenhe um contorno fechado com pelo menos três pontos.'))
    depth = _number(depth, "Profundidade da extrusão", positive=True)
    try:
        wire = cq.Workplane("XY").moveTo(points[0]["x"], points[0]["y"])
        wire = _segments(wire, points[1:]).close()
        return _checked(wire.extrude(depth), "Extrusão")
    except GeometryError:
        raise
    except Exception as exc:
        raise GeometryError(t('Não foi possível extrudar. Verifique se o perfil fecha sem se cruzar. Detalhe CAD: {v1}', v1=exc)) from exc


def build_revolution(profile: list[dict], close_to_axis: bool = True) -> cq.Workplane:
    points = _points(profile)
    if any(p["x"] < 0 for p in points):
        raise GeometryError(t('Revolução: o raio x não pode ser negativo; mantenha o perfil de um lado do eixo.'))
    if max(p["x"] for p in points) <= _EPS:
        raise GeometryError(t('Revolução: o perfil não possui raio.'))
    try:
        wire = cq.Workplane("XZ").moveTo(points[0]["x"], points[0]["y"])
        wire = _segments(wire, points[1:])
        # Um perfil lateral aberto é fechado ao eixo, sem inventar raios.
        # close_to_axis=False permite um contorno fechado de seção anular.
        if close_to_axis:
            if points[-1]["x"] > _EPS:
                wire = wire.lineTo(0, points[-1]["y"])
            if points[0]["x"] > _EPS:
                wire = wire.lineTo(0, points[0]["y"])
        wire = wire.close()
        return _checked(wire.revolve(360, (0, 0), (0, 1)), "Revolução")
    except GeometryError:
        raise
    except Exception as exc:
        raise GeometryError(t('Não foi possível revolucionar. Revise cruzamentos, curvas e a posição do eixo. Detalhe CAD: {v1}', v1=exc)) from exc


def build_cap(profile: list[dict], params: dict) -> cq.Workplane:
    """Ponteira com parede extraída do perfil, topo spline e encaixe na base.

    dome_shape (0.5..2) modifica a spline: h=(1-r²)^dome_shape.
    dome_controls opcionais usam r/h normalizados e substituem essa curva.
    A calibração da imagem fornece os raios; nenhum diâmetro externo é presumido.
    """
    wall = _points(profile)
    if wall[0]["y"] > wall[-1]["y"]:
        wall.reverse()
    if any(p["x"] <= _EPS for p in wall):
        raise GeometryError(t('Ponteira: o perfil da parede externa precisa ter raios x positivos.'))
    if any(b["y"] < a["y"] - _EPS for a, b in zip(wall, wall[1:])):
        raise GeometryError(t('Ponteira: ordene a parede da base ao ombro, sem voltar na altura y.'))
    span = wall[-1]["y"] - wall[0]["y"]
    if span <= _EPS:
        raise GeometryError(t('Ponteira: o perfil deve ter altura maior que zero.'))
    rise = _number(params.get("dome_rise", 3), "Elevação do topo", nonnegative=True)
    if "shoulder_height" in params:
        shoulder = _number(params["shoulder_height"], "Altura até o ombro", positive=True)
    elif "cap_height" in params:
        shoulder = _number(params["cap_height"], "Altura total", positive=True) - rise
        shoulder = _number(shoulder, "Altura total menos elevação", positive=True)
    else:
        shoulder = span
    shape = _number(params.get("dome_shape", 1), "Formato da curva", positive=True)
    if not 0.5 <= shape <= 2:
        raise GeometryError(t('O formato do topo deve estar entre 0,5 e 2.'))
    y0 = wall[0]["y"]
    for p in wall:
        p["y"] = (p["y"] - y0) * shoulder / span
        if p.get("kind") == "arc":
            p["mid_y"] = (_number(p.get("mid_y", p.get("my")), "mid_y do arco") - y0) * shoulder / span
        for key in ("tangent_start", "tangent_end"):
            if p.get(key) is not None:
                try:
                    tx, ty = p[key]
                    p[key] = [_number(tx, "Tangente x"), _number(ty, "Tangente y") * shoulder / span]
                except (TypeError, ValueError):
                    raise GeometryError(t('Tangente da parede: use um vetor [x, y].')) from None
    bore_diameter = _number(params.get("inner_diameter", 0), "Diâmetro interno", nonnegative=True)
    socket_depth = _number(params.get("socket_depth", 0), "Profundidade do encaixe", nonnegative=True)
    minimum_wall = _number(params.get("minimum_wall", 0.1), "Parede mínima de segurança", positive=True)
    if (bore_diameter > 0) != (socket_depth > 0):
        raise GeometryError(t('Encaixe: informe diâmetro interno e profundidade juntos, ou ambos zero.'))
    if socket_depth > 0 and socket_depth + minimum_wall >= shoulder + rise:
        raise GeometryError(t('O encaixe atravessaria o topo ou deixaria a coroa abaixo da espessura mínima.'))
    # Teste conservador: o encaixe não pode alcançar a parede ao longo do corpo.
    if bore_diameter > 0 and bore_diameter / 2 + minimum_wall >= min(p["x"] for p in wall):
        raise GeometryError(t('O diâmetro interno deixa uma parede muito fina ou atravessa o perfil externo.'))
    try:
        wire = cq.Workplane("XZ").moveTo(0, 0).lineTo(wall[0]["x"], 0)
        wire = _segments(wire, wall[1:])
        shoulder_radius = wall[-1]["x"]
        if rise > _EPS:
            controls = params.get("dome_controls")
            if controls:
                normalized = [(1.0, 0.0)]
                for control in controls:
                    r = _number(control.get("r"), "Raio relativo do topo")
                    h = _number(control.get("h"), "Elevação relativa do topo")
                    if not 0 <= r <= 1 or not 0 <= h <= 1:
                        raise GeometryError(t('Controles do topo: r e h precisam estar entre 0 e 1.'))
                    if abs(r - 1) < _EPS and abs(h) < _EPS:
                        continue
                    normalized.append((r, h))
                if normalized[-1] != (0.0, 1.0):
                    normalized.append((0.0, 1.0))
                if any(b[0] >= a[0] for a, b in zip(normalized, normalized[1:])):
                    raise GeometryError(t('Controles do topo: ordene r do ombro (1) até o eixo (0), sem repetir raios.'))
                dome = [(r * shoulder_radius, shoulder + h * rise) for r, h in normalized[1:]]
            else:
                dome = [(shoulder_radius * (1 - i / 12),
                         shoulder + rise * (1 - (1 - i / 12) ** 2) ** shape)
                        for i in range(1, 13)]
            # A coroa de uma revolução deve chegar ao eixo horizontalmente.
            # Isso também evita uma spline livre ultrapassar a altura informada.
            tangents = [(dome[0][0] - shoulder_radius, dome[0][1] - shoulder), (-1, 0)]
            wire = wire.spline(dome, includeCurrent=True, tangents=tangents)
        else:
            wire = wire.lineTo(0, shoulder)
        outer = wire.lineTo(0, 0).close().revolve(360, (0, 0), (0, 1))
        _checked(outer, "Corpo da ponteira")
        if _bounds(outer.val()).zmax > shoulder + rise + 0.01:
            raise GeometryError(t('A spline ultrapassa a altura total. Reduza a elevação dos controles intermediários do topo.'))
        if socket_depth > 0:
            bore = cq.Workplane("XY").circle(bore_diameter / 2).extrude(socket_depth)
            # Checagem volumétrica evita oferecer um encaixe que perfura o topo
            # de uma spline personalizada, mesmo que o resultado ainda seja válido.
            desired_volume = math.pi * (bore_diameter / 2) ** 2 * socket_depth
            covered_volume = outer.intersect(bore).val().Volume()
            if covered_volume < desired_volume * (1 - 1e-6):
                raise GeometryError(t('O encaixe alcança a superfície externa. Reduza diâmetro/profundidade ou aumente o corpo.'))
            outer = outer.cut(bore)
        return _checked(outer, "Ponteira")
    except GeometryError:
        raise
    except Exception as exc:
        raise GeometryError(t('Não foi possível gerar a ponteira. Revise as curvas e as espessuras. Detalhe CAD: {v1}', v1=exc)) from exc


def _primitive(spec: dict) -> cq.Workplane:
    shape = spec.get("shape", "box")
    x, y, z = (_number(spec.get(axis, 0), axis) for axis in ("x", "y", "z"))
    base = cq.Workplane("XY", origin=(x, y, z))
    if shape == "box":
        return base.box(_number(spec.get("width", 10), "Largura", positive=True),
                        _number(spec.get("depth", 10), "Profundidade", positive=True),
                        _number(spec.get("height", 10), "Altura", positive=True),
                        centered=(True, True, False))
    if shape in ("cylinder", "tube"):
        radius = _number(spec.get("radius", 10), "Raio", positive=True)
        height = _number(spec.get("height", 10), "Altura", positive=True)
        base = base.circle(radius)
        if shape == "tube":
            inner = _number(spec.get("inner_radius", 8), "Raio interno", positive=True)
            if inner >= radius:
                raise GeometryError(t('Tubo: o raio interno deve ser menor que o externo.'))
            base = base.circle(inner)
        return base.extrude(height)
    if shape == "loft":
        sections = spec.get("sections", [])
        if len(sections) < 2:
            raise GeometryError(t('Loft: defina pelo menos duas seções em alturas diferentes.'))
        wires = []
        last_z = None
        for section in sections:
            section_z = _number(section.get("z"), "Altura da seção")
            if last_z is not None and section_z <= last_z:
                raise GeometryError(t('Loft: as alturas das seções devem aumentar.'))
            section_plane = cq.Workplane("XY", origin=(x, y, z + section_z))
            if section.get("shape", "circle") == "circle":
                section_plane = section_plane.circle(_number(section.get("radius"), "Raio da seção", positive=True))
            elif section.get("shape") == "rectangle":
                section_plane = section_plane.rect(_number(section.get("width"), "Largura da seção", positive=True),
                                                   _number(section.get("depth"), "Profundidade da seção", positive=True))
            else:
                raise GeometryError(t('Loft: use seções circle ou rectangle.'))
            wires.append(section_plane.val())
            last_z = section_z
        return cq.Workplane(obj=cq.Solid.makeLoft(wires, ruled=bool(spec.get("ruled", False))))
    raise GeometryError(t('Forma não implementada: {v1}. Use box, cylinder, tube ou loft.', v1=shape))


def build_assisted(primitives: list[dict]) -> cq.Workplane:
    if not primitives:
        raise GeometryError(t('Adicione pelo menos uma forma à reconstrução assistida.'))
    result = None
    for index, primitive in enumerate(primitives):
        operation = primitive.get("operation", "union")
        if operation not in ("union", "cut"):
            raise GeometryError(t('Combinação: escolha union (união) ou cut (subtração).'))
        if result is None and operation == "cut":
            raise GeometryError(t('A primeira forma precisa ser uma união; ainda não existe corpo para subtrair.'))
        body = _primitive(primitive)
        result = body if result is None else (result.union(body) if operation == "union" else result.cut(body))
        _checked(result, f"Forma {index + 1}")
    return result


def apply_operations(model: cq.Workplane, operations: list[dict]) -> cq.Workplane:
    """Aplica operações reais. Falhas interrompem a reconstrução, sem ignorar edições."""
    for index, operation in enumerate(operations):
        kind = operation.get("type")
        try:
            if kind in ("fillet", "chamfer"):
                selected = operation.get("selector", "top")
                if selected not in _SELECTORS:
                    raise GeometryError(t('Seleção de arestas não suportada. Use top, bottom, vertical ou all.'))
                selector = _SELECTORS[selected]
                edges = model.edges(selector) if selector else model.edges()
                amount = _number(operation.get("radius" if kind == "fillet" else "distance",
                                               operation.get("size", 1)),
                                 "Raio" if kind == "fillet" else "Chanfro", positive=True)
                model = edges.fillet(amount) if kind == "fillet" else edges.chamfer(amount)
            elif kind == "hole":
                diameter = _number(operation.get("diameter"), "Diâmetro do furo", positive=True)
                bounds = _bounds(model.val())
                depth = _number(operation.get("depth", bounds.zlen), "Profundidade do furo", positive=True)
                entry = operation.get("entry", "bottom")
                if entry not in ("top", "bottom"):
                    raise GeometryError(t('Furo: entry precisa ser top ou bottom.'))
                z = bounds.zmin if entry == "bottom" else bounds.zmax - depth
                x, y = (_number(operation.get(axis, 0), axis) for axis in ("x", "y"))
                tool = cq.Workplane("XY", origin=(x, y, z)).circle(diameter / 2).extrude(depth)
                previous_volume = model.val().Volume()
                model = model.cut(tool)
                if abs(model.val().Volume() - previous_volume) < _EPS:
                    raise GeometryError(t('O furo não intersecta o corpo; ajuste sua posição.'))
            elif kind == "cavity":
                previous_volume = model.val().Volume()
                model = model.cut(_primitive(operation))
                if abs(model.val().Volume() - previous_volume) < _EPS:
                    raise GeometryError(t('A cavidade não intersecta o corpo; ajuste posição e medidas.'))
            elif kind in ("union", "cut"):
                tool = _primitive(operation)
                old_volume = model.val().Volume()
                model = model.union(tool) if kind == "union" else model.cut(tool)
                if kind == "cut" and abs(model.val().Volume() - old_volume) < _EPS:
                    raise GeometryError(t('A ferramenta de subtração não intersecta o corpo.'))
            elif kind == "scale":
                factor = _number(operation.get("factor"), "Fator de escala", positive=True)
                model = cq.Workplane(obj=model.val().scale(factor))
            else:
                raise GeometryError(t('Operação não implementada: {v1}.', v1=kind))
            _checked(model, f"Operação {index + 1} ({kind})")
        except GeometryError:
            raise
        except Exception as exc:
            raise GeometryError(t('A operação {v1} ({v3}) falhou. Reduza a medida ou escolha outras arestas/geometria. Detalhe CAD: {v5}', v1=index + 1, v3=kind, v5=exc)) from exc
    return model


def build_model(project: dict) -> cq.Workplane:
    mode = project.get("mode", "revolution")
    params = project.get("params", {})
    try:
        if mode == "cap":
            model = build_cap(project.get("profile", []), params)
        elif mode == "revolution":
            model = build_revolution(project.get("profile", []), bool(params.get("close_to_axis", True)))
        elif mode == "extrusion":
            model = build_extrusion(project.get("profile", []), params.get("depth", project.get("depth", 10)))
        elif mode == "assisted":
            model = build_assisted(project.get("primitives", []))
        else:
            raise GeometryError(t('Modo de reconstrução não reconhecido: {v1}.', v1=mode))
        return apply_operations(model, project.get("operations", []))
    except GeometryError:
        raise
    except Exception as exc:
        raise GeometryError(t('O motor CAD não conseguiu gerar o modelo: {v1}', v1=exc)) from exc


def validate_solid(model: cq.Workplane | cq.Shape) -> dict:
    """Validade OCCT e sólidos fechados; não certifica tolerâncias de fabricação."""
    try:
        shape = model.val() if isinstance(model, cq.Workplane) else model
        solids = shape.Solids()
        volume = float(shape.Volume())
        valid = bool(shape.isValid() and solids and volume > _EPS and
                     all(s.isValid() and s.Volume() > _EPS and all(shell.Closed() for shell in s.Shells())
                         for s in solids))
        bounds = _bounds(shape)
        return {"valid": valid, "solids": len(solids), "volume_mm3": volume,
                "area_mm2": float(shape.Area()),
                "dimensions_mm": {"x": float(bounds.xlen), "y": float(bounds.ylen), "z": float(bounds.zlen)}}
    except Exception as exc:
        return {"valid": False, "solids": 0, "volume_mm3": 0.0,
                "area_mm2": 0.0, "dimensions_mm": {}, "error": str(exc)}
