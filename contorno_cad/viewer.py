"""Visualização interativa da tesselação real de sólidos e malhas."""
from __future__ import annotations

from .i18n import t

import numpy as np
import plotly.graph_objects as go
import trimesh


def normalize_cad_tessellation(mesh: trimesh.Trimesh) -> tuple[trimesh.Trimesh, dict]:
    """Elimina apenas faces sem área/duplicadas produzidas pelo triangulador.

    OpenCascade pode emitir um triângulo de área zero no polo de uma revolução.
    Não preenche furos, não altera orientações e não move vértices. O relatório
    explicita as remoções; qualquer mudança de volume ou limites bloqueia a saída.
    Esta normalização destina-se à tesselação CAD, nunca a uma malha importada.
    """
    cleaned = mesh.copy()
    original_bounds = mesh.bounds.copy()
    original_volume = float(mesh.volume)
    nonzero = np.asarray(cleaned.area_faces) > 0.0
    removed_zero = int((~nonzero).sum())
    if removed_zero:
        cleaned.update_faces(nonzero)
    unique = cleaned.unique_faces()
    removed_duplicates = int((~unique).sum())
    if removed_duplicates:
        cleaned.update_faces(unique)
    if removed_zero or removed_duplicates:
        cleaned.remove_unreferenced_vertices()
    report = dict(triangulos_antes=len(mesh.faces), triangulos_depois=len(cleaned.faces),
                  triangulos_area_zero_removidos=removed_zero,
                  triangulos_duplicados_removidos=removed_duplicates,
                  fechado_antes=bool(mesh.is_watertight), fechado_depois=bool(cleaned.is_watertight),
                  diferenca_volume_mm3=float(cleaned.volume) - original_volume,
                  metodo="Remoção explícita de triângulos de área exatamente zero e duplicados; "
                         "sem preencher furos, inverter faces ou mover vértices.")
    if (not np.isclose(float(cleaned.volume), original_volume, rtol=1e-12, atol=1e-9)
            or not np.allclose(cleaned.bounds, original_bounds, rtol=0, atol=1e-9)):
        raise ValueError(t('A normalização da tesselação alteraria volume ou limites. Revise a geometria CAD antes de exportar.'))
    cleaned.metadata["normalizacao_tesselacao_cad"] = report
    return cleaned, report


def cad_shape(model):
    """Normaliza Workplane/Shape preservando todos os objetos da Workplane."""
    import cadquery as cq

    if isinstance(model, cq.Shape):
        return model
    if not isinstance(model, cq.Workplane):
        raise ValueError(t('O modelo CAD deve ser uma Workplane ou Shape do CadQuery.'))
    shapes = [value for value in model.vals() if isinstance(value, cq.Shape)]
    if not shapes:
        raise ValueError(t('O projeto ainda não contém geometria CAD.'))
    return shapes[0] if len(shapes) == 1 else cq.Compound.makeCompound(shapes)


def cad_bounds(model) -> np.ndarray:
    """Limites geométricos B-Rep, independentes da triangulação em cache.

    BoundingBox padrão pode usar a triangulação que acaba de ser exibida e
    aumentar conservadoramente a caixa de uma spline. As dimensões físicas
    exigem AddOptimal com useTriangulation=False e useShapeTolerance=False.
    """
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib

    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(cad_shape(model).wrapped, box, False, False)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return np.array([[xmin, ymin, zmin], [xmax, ymax, zmax]], dtype=float)


def mesh_from_model(model_or_mesh, kind: str = "cad") -> trimesh.Trimesh:
    """Produz uma cópia da malha, em milímetros; nunca altera o modelo fonte."""
    if kind == "mesh":
        if not isinstance(model_or_mesh, trimesh.Trimesh):
            raise ValueError(t('Selecione uma malha triangular válida.'))
        return model_or_mesh.copy()
    if kind != "cad":
        raise ValueError(t("Representação desconhecida: use 'cad' ou 'mesh'."))
    vertices, faces = cad_shape(model_or_mesh).tessellate(0.08, 0.12)
    if not vertices or not faces:
        raise ValueError(t('Não foi possível triangular a geometria CAD.'))
    mesh = trimesh.Trimesh(
        vertices=np.asarray([v.toTuple() for v in vertices], dtype=float),
        faces=np.asarray(faces, dtype=int), process=True,
    )
    return normalize_cad_tessellation(mesh)[0]


def _line_trace(lines, name, color="#253b52", width=2):
    coordinates = [[], [], []]
    for line in lines:
        for point in line:
            for axis in range(3):
                coordinates[axis].append(float(point[axis]))
        for axis in range(3):
            coordinates[axis].append(None)
    return go.Scatter3d(x=coordinates[0], y=coordinates[1], z=coordinates[2],
                        mode="lines", line=dict(color=color, width=width),
                        name=t(name), hoverinfo="skip", showlegend=True)


def make_figure(model_or_mesh, kind="cad", view="Isométrica", edges=True,
                axes=True, section_z=None) -> go.Figure:
    """Girar, ampliar e mover a câmera com o mouse; cortes são interseções reais.

    Em CAD desenha arestas B-Rep. Em malhas desenha arestas dos triângulos.
    O corte é um traçado de interseção em Z, não uma operação de corte no sólido.
    """
    mesh = mesh_from_model(model_or_mesh, kind)
    if mesh.is_empty or not np.isfinite(mesh.vertices).all():
        raise ValueError(t('A geometria está vazia ou contém coordenadas inválidas.'))
    vertices, faces = np.asarray(mesh.vertices), np.asarray(mesh.faces)
    fig = go.Figure(go.Mesh3d(
        x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2],
        i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
        color="#4ca49a" if kind == "cad" else "#749bc3", opacity=1,
        flatshading=False, name=t("Sólido CAD" if kind == "cad" else "Malha"),
        lighting=dict(ambient=0.5, diffuse=0.8, specular=0.25, roughness=0.55),
        hovertemplate="X %{x:.2f} mm<br>Y %{y:.2f} mm<br>Z %{z:.2f} mm<extra></extra>",
    ))
    if edges:
        if kind == "cad":
            lines = []
            for edge in cad_shape(model_or_mesh).Edges():
                try:
                    lines.append([edge.positionAt(float(t)).toTuple()
                                  for t in np.linspace(0, 1, 40)])
                except Exception:
                    # Uma aresta degenerada não deve impedir a inspeção do sólido.
                    lines.append([edge.startPoint().toTuple(), edge.endPoint().toTuple()])
            fig.add_trace(_line_trace(lines, "Arestas CAD"))
        else:
            unique_edges = mesh.edges_unique
            stride = max(1, int(np.ceil(len(unique_edges) / 40000)))
            lines = vertices[unique_edges[::stride]]
            fig.add_trace(_line_trace(lines, "Arestas trianguladas", width=1))

    if kind == "cad":
        # As cotas vêm do B-Rep, não dos extremos aproximados dos triângulos.
        low, high = cad_bounds(model_or_mesh)
    else:
        low, high = np.asarray(mesh.bounds)
    dimensions = high - low
    margin = max(float(dimensions.max()) * 0.08, 0.5)
    dimension_lines, annotations = [], []
    for axis, label in enumerate(("Largura X", "Profundidade Y", "Altura Z")):
        start, end = low.copy() - margin, low.copy() - margin
        start[axis], end[axis] = low[axis], high[axis]
        dimension_lines.append([start, end])
        center = (start + end) / 2
        annotations.append(dict(x=center[0], y=center[1], z=center[2],
                                text=f"{t(label)}: {dimensions[axis]:.2f} mm",
                                showarrow=False, bgcolor="rgba(255,255,255,0.85)",
                                font=dict(size=11, color="#243b53")))
    fig.add_trace(_line_trace(dimension_lines, "Dimensões", color="#6c7c8b", width=2))
    if section_z is not None:
        # Segmentos diretos evitam dependências opcionais de grafos/polígonos.
        segments = trimesh.intersections.mesh_plane(mesh, plane_origin=[0, 0, float(section_z)],
                                                    plane_normal=[0, 0, 1])
        if len(segments):
            fig.add_trace(_line_trace(segments,
                                     t("Seção Z = {v1:.2f} mm", v1=float(section_z)), "#ed8b24", 6))

    cameras = {
        "Isométrica": dict(eye=dict(x=1.6, y=-1.8, z=1.35), up=dict(x=0, y=0, z=1)),
        "Frente": dict(eye=dict(x=0, y=-2.5, z=0), up=dict(x=0, y=0, z=1)),
        "Lado": dict(eye=dict(x=2.5, y=0, z=0), up=dict(x=0, y=0, z=1)),
        "Topo": dict(eye=dict(x=0, y=0, z=2.5), up=dict(x=0, y=1, z=0)),
    }
    axis_options = dict(showgrid=axes, showticklabels=axes, visible=axes,
                        zeroline=axes, showbackground=axes)
    fig.update_layout(
        scene=dict(xaxis=dict(title="X (mm)", **axis_options),
                   yaxis=dict(title="Y (mm)", **axis_options),
                   zaxis=dict(title="Z (mm)", **axis_options),
                   aspectmode="data", camera=cameras.get(view, cameras["Isométrica"]),
                   annotations=annotations),
        height=620, margin=dict(l=0, r=0, t=16, b=0),
        paper_bgcolor="#ffffff", legend=dict(orientation="h", y=0),
        uirevision=f"{view}-{axes}",
    )
    return fig


def figure_html(figure: go.Figure) -> bytes:
    """HTML independente: inclui Plotly; não precisa de CDN nem conexão."""
    return figure.to_html(full_html=True, include_plotlyjs=True,
                          config={"responsive": True, "displaylogo": False}).encode("utf-8")
