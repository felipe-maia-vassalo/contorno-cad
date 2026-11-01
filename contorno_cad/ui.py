"""Streamlit interface with session-local Portuguese and English presentation."""
from pathlib import Path
import base64
import hashlib
import json
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go

from .i18n import t, set_language, get_language, LANGUAGES, localize_report, formatter, translate_in
from . import imaging, profiles, project as storage
from .cad import build_model, apply_operations, validate_solid, sample_profile
from .io3d import import_model, transform_component, export_bundle, export_project_zip, geometry_report
from .viewer import make_figure, figure_html, mesh_from_model

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["Painel inicial", "Imagem para CAD", "Editor de perfil 2D", "Editor CAD", "Importar Modelo 3D", "Visualizador 3D", "Exportar projeto"]
MODES = {"Ponteira • revolução com topo spline": "cap", "Revolução de perfil lateral": "revolution", "Extrusão de contorno fechado": "extrusion", "Reconstrução paramétrica assistida": "assisted"}
point_editor = components.declare_component("editor_pontos_contorno", path=str(Path(__file__).parent / "components" / "point_editor"))


def go_page(page):
    st.session_state.route = page


def reset_project(p):
    st.session_state.project = p
    for key in ["model", "model_signature", "exports", "export_signature", "imported"]:
        st.session_state.pop(key, None)
    st.session_state.revision = st.session_state.get("revision", 0) + 1
    st.session_state.project_serial = st.session_state.get("project_serial", 0) + 1
    # Widget identity is renewed when a project is reopened.
    for key in list(st.session_state):
        if key.startswith(("edit_", "click_", "ui_")):
            del st.session_state[key]


def localized_number_input(container, label, *args, **kwargs):
    # Keep language changes independent from edits, while synchronizing values
    # changed externally by contour selection, calibration, or derived geometry.
    key = kwargs.get("key")
    default = kwargs.get("value", 0.0)
    defaults = st.session_state.setdefault("_number_defaults", {})
    if key and key in st.session_state and defaults.get(key) != default:
        st.session_state[key] = default
    if key:
        defaults[key] = default
    return container.number_input(label, *args, **kwargs)


def number(label, value, min_value=None, max_value=None, step=.1, key=None):
    return localized_number_input(st, t(label), min_value=min_value, max_value=max_value, value=float(value), step=float(step), format='%.3f', key=key)


def photo(p):
    data = storage.image_bytes(p)
    return imaging.read_image(data) if data else None


def profile_overlay(p, rgb):
    fig = go.Figure(go.Image(z=rgb))
    cal = p.get("calibration", {})
    if p.get("profile") and cal.get("scale"):
        pp = profiles.mm_to_pixels(p["profile"], cal["scale"], cal["origin"])
    else:
        pp = p.get("pixel_profile", [])
    if pp:
        fig.add_trace(go.Scatter(x=[v["x"] for v in pp], y=[v["y"] for v in pp], mode="markers+text", text=[str(i+1) for i in range(len(pp))], textposition="top right", marker=dict(size=6,color="#00d9a3"), name=t("Pontos editáveis")))
        if p.get("profile") and cal.get("scale"):
            try:
                curve = sample_profile(p["profile"],closed=p["mode"]=="extrusion")
                curve = profiles.mm_to_pixels(curve,cal["scale"],cal["origin"])
                fig.add_trace(go.Scatter(x=[v["x"] for v in curve],y=[v["y"] for v in curve],mode="lines",line=dict(color="#00d9a3"),name=t("Curva calculada pelo CAD")))
            except ValueError as exc:
                st.warning(t('Prévia da curva: {v1}', v1=exc))
    if cal.get("axis_x") is not None:
        fig.add_vline(x=cal["axis_x"], line_dash="dash", line_color="#259bff")
    fig.update_layout(height=600, margin=dict(l=0,r=0,t=15,b=0), dragmode="pan", uirevision="photo")
    return fig


def current_model(p, warn=True):
    if "model" not in st.session_state:
        if warn:
            st.info(t('Gere um sólido no Editor CAD ou importe um arquivo para abrir a visualização.'))
        return None, "cad"
    if st.session_state.get("model_signature") != storage.signature(p):
        if warn:
            st.warning(t('Há alterações no projeto. Clique em Gerar / atualizar modelo para atualizar a geometria antes de exportar.'))
        return None, st.session_state.get("kind", "cad")
    return st.session_state.model, st.session_state.get("kind", "cad")


def generate(p):
    try:
        with st.spinner(t('Calculando geometria e verificando o resultado…')):
            if p["mode"] == "import":
                source = p["import_source"]
                loaded = import_model(base64.b64decode(source["base64"]), source["filename"])
                st.session_state.imported = loaded
                item = loaded["components"][int(p.get("component_index", 0))]
                item = transform_component(item, **p.get("transform", {}))
                kind = loaded["kind"]
                model = item["model" if kind == "cad" else "mesh"]
                if kind == "cad":
                    model = apply_operations(model, p.get("operations", []))
            else:
                model, kind = build_model(p), "cad"
            st.session_state.model = model
            st.session_state.kind = kind
            st.session_state.model_signature = storage.signature(p)
            st.session_state.pop("exports", None)
        st.success(t('Modelo atualizado a partir dos parâmetros atuais.'))
    except Exception as exc:
        st.error(t(str(exc)))


def show_model(model, kind="cad", controls=True):
    view, edges, axes, section = "Isométrica", True, True, None
    if controls:
        a,b,c = st.columns([2,1,1])
        view = a.selectbox(t('Vista'), ["Isométrica", "Frente", "Lado", "Topo"], format_func=formatter(), key='ui_show_model_110')
        edges = b.checkbox(t('Arestas'), True, key='ui_show_model_111')
        axes = c.checkbox(t('Eixos / medidas'), True, key='ui_show_model_112')
        if st.checkbox(t('Seção transversal em Z'), key='ui_show_model_113'):
            bounds = mesh_from_model(model, kind).bounds
            section = st.slider(t('Plano da seção (mm)'), float(bounds[0,2]), float(bounds[1,2]), float(bounds[:,2].mean()), key='ui_show_model_115')
    st.plotly_chart(make_figure(model, kind, view=view, edges=edges, axes=axes, section_z=section), width="stretch", config={"displaylogo":False,"scrollZoom":True})
    st.caption(t('Arraste para girar; use a roda para aproximar e Shift + arrastar para mover a câmera. A seção mostra a interseção real com o plano.'))
    report = geometry_report(model, kind)
    a,b,c = st.columns(3)
    a.metric(t('Representação'), t("Sólido CAD" if kind == "cad" else "Malha"))
    b.metric(t('Volume (mm³)'), f'{report["volume_mm3"]:,.2f}')
    bounds = np.asarray(report["limites_mm"])
    c.metric(t('Dimensões X × Y × Z (mm)'), " × ".join(f"{v:.2f}" for v in bounds[1]-bounds[0]))
    with st.expander(t('Inspeção geométrica')):
        st.json(localize_report(report))


def home(p):
    st.title(t('Contorno CAD'))
    st.write(t('Da referência visual a um sólido com medidas controladas.'))
    st.info(t('Uma fotografia fornece uma silhueta, não todas as dimensões. Confirme medidas, perspectiva, simetria e folgas antes de fabricar.'))
    st.write(t('**1. Enviar JPEG → 2. Detectar e corrigir perfil → 3. Calibrar → 4. Gerar e editar → 5. Validar e exportar**'))
    a,b = st.columns(2)
    with a:
        st.subheader(t('Começar com sua fotografia'))
        st.button(t('Abrir Imagem para CAD'), on_click=go_page, args=(PAGES[1],), type="primary", key='ui_home_136')
    with b:
        st.subheader(t('Exemplo real da ponteira'))
        demo = ROOT / "examples" / "demo_project.json"
        if demo.exists() and st.button(t('Abrir exemplo calibrado da ponteira'), key='ui_home_140'):
            reset_project(storage.loads(demo.read_bytes()))
            st.rerun()
        st.caption(t('A foto original, o contorno detectado e as hipóteses ficam disponíveis no projeto. Veja a página Imagem para CAD.'))
    st.write(t('**Projeto atual:** {v1} · {v3} pontos · unidades: mm', v1=p['name'], v3=len(p.get('profile', []))))
    if p.get("profile"):
        a,b=st.columns(2)
        a.button(t('Revisar perfil atual'),on_click=go_page,args=(PAGES[2],), key='ui_home_147')
        b.button(t('Abrir Editor CAD'),on_click=go_page,args=(PAGES[3],),type="primary", key='ui_home_148')
    with st.expander(t('Medidas e hipóteses deste projeto'), expanded=True):
        for note in p.get("assumptions", []):
            st.write('• ' + t(note))


def image_page(p):
    st.title(t('Imagem para CAD'))
    st.write(t('Envie uma foto, recorte a área do objeto e ajuste a detecção. Os pontos permanecem no projeto entre as etapas.'))
    with st.expander(t('Como deve ser a imagem para funcionar bem'), expanded=True):
        st.markdown(t('\n- **Formato:** JPG, JPEG ou PNG, até 30 MB e 24 megapixels. Prefira o arquivo original, sem compressão excessiva.\n- **Objeto inteiro e nítido:** deixe uma margem em volta da peça e evite cortar a base ou o topo. Como orientação, tente ocupar pelo menos 500 pixels na maior dimensão; isso não garante precisão.\n- **Fundo simples e contrastante:** peça escura sobre fundo claro ou peça clara sobre fundo escuro. Evite sombras fortes, reflexos, transparências e outros objetos encostados no contorno.\n- **Câmera alinhada:** fotografe de frente para o perfil desejado, com a câmera na altura do centro da peça, sem inclinar. Afaste a câmera e use zoom óptico se disponível para reduzir a perspectiva.\n- **Medida conhecida:** tenha uma dimensão medida da peça ou uma régua no mesmo plano. Marque dois pontos e informe a distância real em milímetros; sem isso, pixels não fornecem medidas físicas.\n- **Revolução / ponteira:** use a vista lateral de uma peça com simetria circular em torno de um eixo. Desenhe ou selecione apenas uma lateral do eixo até a borda. O encaixe interno precisa de medidas próprias.\n- **Extrusão:** fotografe perpendicularmente uma face plana cujo contorno possa manter a mesma seção ao longo da profundidade. Informe essa profundidade separadamente.\n- **Formas complexas:** fotografias oblíquas, peças orgânicas e superfícies ocultas exigem mais vistas, medidas e reconstrução assistida. Uma única foto não recupera automaticamente toda a peça.\n\nSe a detecção falhar, ajuste o recorte, contraste e limiares ou desenhe/corrija os pontos sobre a imagem. Marcações coloridas são referências de desenho, não medidas. Sempre confira o perfil e as dimensões antes de gerar o sólido.\n'))
    uploaded = st.file_uploader(t('Fotografia JPEG ou PNG'), type=["jpg","jpeg","png"],key="photo_upload_"+str(st.session_state.get("project_serial",0)))
    if uploaded:
        data = uploaded.getvalue()
        digest = hashlib.sha256(data).hexdigest()
        if p.get("image_digest") != digest:
            imaging.read_image(data)
            storage.set_image(p, data, uploaded.name)
            p.update(image_digest=digest, pixel_profile=[], profile=[], calibration={}, image_settings={})
            st.session_state.revision += 1
    a,b = st.columns(2)
    for col, name, label in [(a,"ponteira_referencia.jpeg","Carregar fotografia preta"),(b,"ponteira_curva.jpeg","Carregar fotografia com curva verde")]:
        if col.button(t(label), key='ui_image_page_181_'+name):
            data = (ROOT/"examples"/name).read_bytes()
            storage.set_image(p, data, name)
            p.update(image_digest=hashlib.sha256(data).hexdigest(), pixel_profile=[], profile=[], calibration={}, image_settings={})
            st.session_state.revision += 1
            st.rerun()
    rgb = photo(p)
    if rgb is None:
        return
    h,w = rgb.shape[:2]
    st.success(t('Imagem recebida: {v1} — {v3} × {v5} pixels. Dimensões físicas ainda dependem da calibração.', v1=p['image']['filename'], v3=w, v5=h))
    settings = p.setdefault("image_settings", {})
    with st.expander(t('Recorte, contraste e detecção'), expanded=True):
        x0,y0,x1,y1 = settings.get("crop", [0,0,w,h])
        xs = st.slider(t('Recorte horizontal (pixels)'), 0,w,(int(x0),int(x1)), key='ui_image_page_195')
        ys = st.slider(t('Recorte vertical (pixels)'), 0,h,(int(y0),int(y1)), key='ui_image_page_196')
        a,b,c = st.columns(3)
        methods = ["Canny","Escuro","Claro","Fundo colorido"]
        method = a.selectbox(t('Método'), methods,index=methods.index(settings.get("method","Canny")), format_func=formatter(), key='ui_image_page_199')
        contrast = b.slider(t('Contraste'),.2,3.,float(settings.get("contrast",1.)),.1, key='ui_image_page_200')
        blur = c.select_slider(t('Filtro gaussiano'), options=[1,3,5,7,9],value=int(settings.get("blur",3)), key='ui_image_page_201')
        a,b,c = st.columns(3)
        low = a.slider(t('Canny: limiar inferior'),0,255,int(settings.get("low",50)), key='ui_image_page_203')
        high = b.slider(t('Canny: limiar superior'),0,255,int(settings.get("high",150)), key='ui_image_page_204')
        threshold = c.slider(t('Limiar claro/escuro (0 = Otsu)'),0,255,int(settings.get("threshold",0)), key='ui_image_page_205')
        a,b,c = st.columns(3)
        close = a.slider(t('Fechar pequenas lacunas (px)'),0,15,int(settings.get("close",3)), key='ui_image_page_207')
        min_area = localized_number_input(b, t('Área mínima do contorno (px²)'), min_value=1, value=int(settings.get('min_area', 100)), key='ui_image_page_208')
        saturation = c.slider(t('Saturação máxima do objeto'),0,255,int(settings.get("saturation",105)), key='ui_image_page_209')
        settings.update(crop=[*xs[:1],*ys[:1],xs[1],ys[1]],method=method,contrast=contrast,blur=blur,low=low,high=high,threshold=threshold,close=close,min_area=min_area,saturation=saturation)
    result = imaging.process_image(rgb, settings)
    a,b = st.columns(2)
    a.image(rgb, caption=t('Original recebida'), width="stretch")
    b.image(result["overlay"], caption=t('Contornos detectados: {v1}', v1=len(result['contours'])), width="stretch")
    with st.expander(t('Máscara / bordas realmente calculadas pelo OpenCV')):
        st.image(result["mask"], width="stretch", clamp=True)
    if result["contours"]:
        selected = st.selectbox(t('Contorno desejado'), range(len(result["contours"])),format_func=lambda i, _language=get_language(): translate_in(_language, 'Contorno {v1}', v1=i + 1), key='ui_image_page_218')
        contour = result["contours"][selected]
        epsilon = st.slider(t('Simplificação do contorno (px)'),.1,20.,2.,.1, key='ui_image_page_220')
        a,b = st.columns(2)
        if a.button(t('Usar contorno fechado (extrusão)'), key='ui_image_page_222'):
            p["pixel_profile"] = imaging.contour_points(contour, epsilon)
            p["profile"] = []
            p["mode"] = "extrusion"
            st.session_state.revision += 1
        if b.button(t('Usar lateral direita (revolução / ponteira)'), key='ui_image_page_227'):
            pp,meta = imaging.right_wall(contour)
            p["pixel_profile"] = pp
            p["profile"] = []
            cal = p.setdefault("calibration",{})
            cal.update(axis_x=meta["axis_x"],origin=[meta["axis_x"],meta["baseline_y"]])
            p["mode"] = "cap"
            st.session_state.revision += 1
        if st.button(t('Marcar extremos verticais do contorno para calibrar'), key='ui_image_page_235'):
            pts = contour.reshape(-1,2)
            center = float((pts[:,0].min()+pts[:,0].max())/2)
            p.setdefault("calibration",{})["points"] = [[center,float(pts[:,1].min())],[center,float(pts[:,1].max())]]
            st.session_state.revision += 1
    else:
        st.warning(t('Nenhum contorno encontrado. Ajuste o recorte/método ou desenhe o perfil abaixo.'))
    calibrate_editor(p,rgb)
    st.button(t('Continuar para o perfil 2D'),on_click=go_page,args=(PAGES[2],),type="primary", key='ui_image_page_243')


def calibrate_editor(p,rgb):
    st.subheader(t('Pontos e escala na fotografia'))
    cal = p.setdefault("calibration",{})
    pp = p.get("pixel_profile",[])
    if p.get("profile") and cal.get("scale"):
        pp = profiles.mm_to_pixels(p["profile"],cal["scale"],cal["origin"])
    value = point_editor(image="data:image/png;base64,"+base64.b64encode(imaging.png_bytes(rgb)).decode(),points=pp,calibration=cal.get("points",[]),axis_x=cal.get("axis_x"),revision=st.session_state.revision,closed=p["mode"]=="extrusion",language=get_language(),key="click_"+str(st.session_state.revision),default=None)
    if value and value.get("event_id") != st.session_state.get("last_point_event"):
        st.session_state.last_point_event = value["event_id"]
        p["pixel_profile"] = value["points"]
        cal["points"] = value["calibration"]
        if cal.get("scale"):
            p["profile"] = profiles.pixels_to_mm(p["pixel_profile"],cal["scale"],cal["origin"])
        st.session_state.revision += 1
        st.rerun()
    h,w = rgb.shape[:2]
    with st.expander(t('Coordenadas da calibração e origem'),expanded=True):
        pts = cal.get("points",[[w/2,0],[w/2,h-1]])
        if len(pts)!=2:
            pts = [[w/2,0],[w/2,h-1]]
        a,b,c,d = st.columns(4)
        px1=localized_number_input(a, t('Ponto 1 · X (px)'), value=float(pts[0][0]), step=1.0, key='ui_calibrate_editor_267')
        py1=localized_number_input(b, t('Ponto 1 · Y (px)'), value=float(pts[0][1]), step=1.0, key='ui_calibrate_editor_268')
        px2=localized_number_input(c, t('Ponto 2 · X (px)'), value=float(pts[1][0]), step=1.0, key='ui_calibrate_editor_269')
        py2=localized_number_input(d, t('Ponto 2 · Y (px)'), value=float(pts[1][1]), step=1.0, key='ui_calibrate_editor_270')
        origin=cal.get("origin",[w/2,h-1])
        a,b,c = st.columns(3)
        distance=localized_number_input(a, t('Distância conhecida (mm)'), min_value=0.001, value=float(cal.get('distance_mm', 45.0)), step=0.1, key='ui_calibrate_editor_273')
        ox=localized_number_input(b, t('Eixo / origem X (px)'), value=float(origin[0]), step=1.0, key='ui_calibrate_editor_274')
        oy=localized_number_input(c, t('Base / origem Y (px)'), value=float(origin[1]), step=1.0, key='ui_calibrate_editor_275')
        if st.button(t('Confirmar calibração e converter perfil para mm'), key='ui_calibrate_editor_276'):
            scale=profiles.calibration_scale([[px1,py1],[px2,py2]],distance)
            cal.update(points=[[px1,py1],[px2,py2]],distance_mm=distance,scale=scale,origin=[ox,oy],axis_x=ox)
            p["profile"]=profiles.pixels_to_mm(p.get("pixel_profile",[]),scale,[ox,oy])
            st.session_state.revision+=1
            st.rerun()
        if cal.get("scale"):
            st.success(t('Escala confirmada: {v1:.6f} mm/pixel. Origem: {v3}.', v1=cal['scale'], v3=cal['origin']))
    st.warning(t('A calibração vale no plano escolhido e não corrige perspectiva. A altura de 45 mm é uma referência aproximada que precisa ser confirmada.'))


def profile_page(p):
    st.title(t('Editor de perfil 2D'))
    st.write(t('Na revolução, X é o raio em relação ao eixo e Y é a altura. Na extrusão, X e Y definem o contorno fechado. Todas as medidas abaixo estão em mm.'))
    frame=pd.DataFrame(p.get("profile",[]),columns=["x","y","kind","mid_x","mid_y"])
    frame["kind"]=frame["kind"].fillna("line")
    edited=st.data_editor(frame,num_rows="dynamic",width="stretch",key="edit_profile_"+str(st.session_state.revision),column_config={"kind":st.column_config.SelectboxColumn(t('Segmento de chegada'),options=["line","spline","arc"],required=True),"x":st.column_config.NumberColumn(t('X / raio (mm)'),required=True),"y":st.column_config.NumberColumn(t('Y / altura (mm)'),required=True),"mid_x":st.column_config.NumberColumn(t('Arco: X intermediário')),"mid_y":st.column_config.NumberColumn(t('Arco: Y intermediário'))})
    st.caption(t('Adicione/remova linhas na tabela. Para spline, marque uma sequência de pontos como spline; para arco, informe o ponto intermediário do segmento. A primeira linha é o ponto inicial.'))
    a,b=st.columns(2)
    if a.button(t('Aplicar coordenadas do perfil'),type="primary", key='ui_profile_page_295'):
        rows=[]
        records=edited.to_dict("records")
        for index,row in enumerate(records):
            if pd.isna(row["x"]) or pd.isna(row["y"]):
                raise ValueError(t('Preencha X e Y de todos os pontos.'))
            cleaned={k:v for k,v in row.items() if not pd.isna(v)}
            previous=p.get("profile",[])
            if len(records)==len(previous) and cleaned.get("kind")==previous[index].get("kind"):
                for key in ("tangent_start","tangent_end"):
                    if key in previous[index]:cleaned[key]=previous[index][key]
            rows.append(cleaned)
        p["profile"]=rows
        if p.get("calibration",{}).get("scale"):
            p["pixel_profile"]=profiles.mm_to_pixels(rows,p["calibration"]["scale"],p["calibration"]["origin"])
        st.session_state.revision+=1
        st.rerun()
    if b.button(t('Suavizar lateral com spline'), key='ui_profile_page_312'):
        p["profile"]=profiles.smooth_wall(p["profile"])
        st.session_state.revision+=1
        st.rerun()
    with st.expander(t('Tangência da spline (quando houver uma sequência spline)')):
        st.caption(t('Direções em X/Y no início e fim da primeira sequência. Não impõe tangência entre todas as curvas; alterações incompatíveis são rejeitadas pelo motor CAD.'))
        a,b,c,d=st.columns(4)
        tx0=localized_number_input(a, t('Tangente inicial X'), value=0.0, key='ui_profile_page_319')
        ty0=localized_number_input(b, t('Tangente inicial Y'), value=1.0, key='ui_profile_page_320')
        tx1=localized_number_input(c, t('Tangente final X'), value=0.0, key='ui_profile_page_321')
        ty1=localized_number_input(d, t('Tangente final Y'), value=1.0, key='ui_profile_page_322')
        if st.button(t('Aplicar direções à primeira spline'), key='ui_profile_page_323'):
            ids=[i for i,v in enumerate(p["profile"]) if i>0 and v.get("kind")=="spline"]
            if not ids: raise ValueError(t('Marque pelo menos um segmento spline na tabela.'))
            first=ids[0];last=first
            while last+1<len(p["profile"]) and p["profile"][last+1].get("kind")=="spline":last+=1
            p["profile"][first]["tangent_start"]=[tx0,ty0]
            p["profile"][last]["tangent_end"]=[tx1,ty1]
            st.success(t('Tangentes aplicadas. Gere o modelo para verificar a curva.'))
    rgb=photo(p)
    if rgb is not None:
        st.plotly_chart(profile_overlay(p,rgb),width="stretch")
        if st.checkbox(t('Corrigir pontos diretamente sobre a foto'), key='ui_profile_page_334'):
            calibrate_editor(p,rgb)
    elif p.get("profile"):
        st.plotly_chart(go.Figure(go.Scatter(x=[v["x"] for v in p["profile"]],y=[v["y"] for v in p["profile"]],mode="lines+markers")).update_layout(xaxis_title="X (mm)",yaxis_title="Y (mm)",yaxis_scaleanchor="x"),width="stretch")
    st.button(t('Continuar para o Editor CAD'),on_click=go_page,args=(PAGES[3],), key='ui_profile_page_338')


def param_controls(p):
    modes=list(MODES)
    idx=list(MODES.values()).index(p["mode"]) if p["mode"] in MODES.values() else 0
    label=st.selectbox(t('Método de reconstrução'),modes,index=idx, format_func=formatter(), key='ui_param_controls_344')
    p["mode"]=MODES[label]
    params=p.setdefault("params",{})
    if p["mode"]=="cap":
        st.caption(t('O perfil fornece os raios externos. Sua faixa de altura é ajustada à altura lateral abaixo. O topo é uma spline de revolução, não precisa ser um arco circular.'))
        a,b,c=st.columns(3)
        params["shoulder_height"]=localized_number_input(a, t('Altura lateral até o ombro (mm)'), min_value=0.1, value=float(params.get('shoulder_height', 39.0)), step=0.5, key='ui_param_controls_350')
        params["dome_rise"]=localized_number_input(b, t('Elevação do topo (mm)'), min_value=0.1, value=float(params.get('dome_rise', 6.0)), step=0.5, key='ui_param_controls_351')
        params["dome_shape"]=c.slider(t('Formato da spline superior'),.5,2.,float(params.get("dome_shape",1.)),.05, key='ui_param_controls_352')
        a,b,c=st.columns(3)
        params["inner_diameter"]=localized_number_input(a, t('Diâmetro interno do encaixe (mm)'), min_value=0.0, value=float(params.get('inner_diameter', 22.22)), step=0.05, key='ui_param_controls_354')
        params["socket_depth"]=localized_number_input(b, t('Profundidade do encaixe (mm)'), min_value=0.0, value=float(params.get('socket_depth', 30.0)), step=0.5, key='ui_param_controls_355')
        c.metric(t('Altura total (mm)'),f'{params["shoulder_height"]+params["dome_rise"]:.2f}')
        with st.expander(t('Definir espessura lateral na base')):
            wall=number(t('Espessura desejada (mm)'),3.,.1,step=.1, key='ui_param_controls_358')
            if st.button(t('Calcular diâmetro interno pela espessura'), key='ui_param_controls_359'):
                if not p.get("profile"):raise ValueError(t('Defina o perfil primeiro.'))
                base=min(p["profile"],key=lambda v:v["y"])
                diameter=2*(base["x"]-wall)
                if diameter<=0:raise ValueError(t('Espessura maior que o raio externo da base.'))
                params["inner_diameter"]=diameter
                st.rerun()
            st.caption(t('Espessura referida à base; paredes inclinadas têm espessura variável. O motor verifica se o encaixe atravessa a superfície externa.'))
        with st.expander(t('Spline superior personalizada (raio e elevação normalizados)')):
            st.caption(t('r=1 é o ombro e r=0 é o eixo; h=0 é o ombro e h=1 é o ápice. Informe controles internos; os extremos e a tangente horizontal do ápice são definidos pelo motor.'))
            custom=st.checkbox(t('Usar controles personalizados'),value=bool(params.get("dome_controls")), key='ui_param_controls_369')
            text=st.text_area(t('Controles JSON'),value=json.dumps(params.get("dome_controls",[{"r":.75,"h":.5},{"r":.4,"h":.86}]),indent=2), key='ui_param_controls_370')
            if custom:
                if st.button(t('Aplicar controles da curva'), key='ui_param_controls_372'):
                    params["dome_controls"]=json.loads(text)
            else:params.pop("dome_controls",None)
    elif p["mode"]=="extrusion":
        params["depth"]=number(t('Profundidade de extrusão (mm)'),params.get("depth",10.),.1, key='ui_param_controls_376')
    elif p["mode"]=="revolution":
        params["close_to_axis"]=st.checkbox(t('Fechar perfil lateral até o eixo'),value=params.get("close_to_axis",True), key='ui_param_controls_378')
    else:
        primitive_controls(p)


def primitive_controls(p):
    st.write(t('Combine formas em milímetros. União adiciona material; subtração cria vazios.'))
    with st.form("primitive_form"):
        a,b,c=st.columns(3)
        shape=a.selectbox(t('Forma'),["box","cylinder","tube","loft"],format_func=lambda s, _language=get_language(): translate_in(_language, {'box': 'Caixa / placa', 'cylinder': 'Cilindro', 'tube': 'Tubo', 'loft': 'Loft entre círculos'}[s]), key='ui_primitive_controls_387')
        op=b.selectbox(t('Combinação'),["union","cut"],format_func=lambda s, _language=get_language(): translate_in(_language, 'União' if s == 'union' else 'Subtração'), key='ui_primitive_controls_388')
        height=localized_number_input(c, t('Altura (mm)'), value=20.0, min_value=0.1, key='ui_primitive_controls_389')
        a,b,c,d=st.columns(4)
        width=localized_number_input(a, t('Largura (mm)'), value=30.0, min_value=0.1, key='ui_primitive_controls_391')
        depth=localized_number_input(b, t('Profundidade (mm)'), value=20.0, min_value=0.1, key='ui_primitive_controls_392')
        radius=localized_number_input(c, t('Raio (mm)'), value=15.0, min_value=0.1, key='ui_primitive_controls_393')
        inner=localized_number_input(d, t('Raio interno / raio superior loft (mm)'), value=10.0, min_value=0.1, key='ui_primitive_controls_394')
        a,b,c=st.columns(3)
        x=localized_number_input(a, t('Posição X (mm)'), value=0.0, key='ui_primitive_controls_396')
        y=localized_number_input(b, t('Posição Y (mm)'), value=0.0, key='ui_primitive_controls_397')
        z=localized_number_input(c, t('Posição Z (mm)'), value=0.0, key='ui_primitive_controls_398')
        if st.form_submit_button(t('Adicionar forma'), key='ui_primitive_controls_399'):
            item=dict(shape=shape,operation=op,width=width,depth=depth,height=height,radius=radius,inner_radius=inner,x=x,y=y,z=z)
            if shape=="loft":item["sections"]=[{"z":0,"radius":radius},{"z":height,"radius":inner}]
            p.setdefault("primitives",[]).append(item)
    if p.get("primitives"):
        st.dataframe(p["primitives"],width="stretch")
        if st.button(t('Remover última forma'), key='ui_primitive_controls_405'):p["primitives"].pop();st.rerun()


def operation_controls(p):
    with st.expander(t('Operações de edição do sólido')):
        with st.form("operations_form"):
            labels={"fillet":"Arredondamento (fillet)","chamfer":"Chanfro","hole":"Furo cilíndrico","cavity":"Cavidade retangular","union":"União com caixa","cut":"Subtração de caixa","scale":"Escala uniforme"}
            kind=st.selectbox(t('Operação'),list(labels),format_func=lambda value, _language=get_language(): translate_in(_language, labels.get(value)), key='ui_operation_controls_412')
            a,b,c=st.columns(3)
            size=localized_number_input(a, t('Raio / chanfro / diâmetro (mm)'), value=1.0, min_value=0.001, key='ui_operation_controls_414')
            selector=b.selectbox(t('Arestas para fillet / chanfro'),["top","bottom","vertical","all"],format_func=lambda s, _language=get_language(): translate_in(_language, {'top': 'Mais altas', 'bottom': 'Mais baixas', 'vertical': 'Verticais', 'all': 'Todas'}[s]), key='ui_operation_controls_415')
            factor=localized_number_input(c, t('Fator de escala'), value=1.1, min_value=0.001, key='ui_operation_controls_416')
            a,b,c=st.columns(3)
            x=localized_number_input(a, t('Ferramenta X (mm)'), value=0.0, key='ui_operation_controls_418')
            y=localized_number_input(b, t('Ferramenta Y (mm)'), value=0.0, key='ui_operation_controls_419')
            z=localized_number_input(c, t('Ferramenta Z (mm)'), value=0.0, key='ui_operation_controls_420')
            a,b,c=st.columns(3)
            width=localized_number_input(a, t('Ferramenta largura (mm)'), value=5.0, min_value=0.001, key='ui_operation_controls_422')
            depth=localized_number_input(b, t('Ferramenta profundidade (mm)'), value=5.0, min_value=0.001, key='ui_operation_controls_423')
            height=localized_number_input(c, t('Ferramenta altura / profundidade do furo (mm)'), value=5.0, min_value=0.001, key='ui_operation_controls_424')
            entry=st.selectbox(t('Entrada do furo'),["top","bottom"],format_func=lambda s, _language=get_language(): translate_in(_language, 'Topo' if s == 'top' else 'Base'), key='ui_operation_controls_425')
            if st.form_submit_button(t('Adicionar operação e reconstruir'), key='ui_operation_controls_426'):
                item=dict(type=kind,radius=size,distance=size,diameter=size,selector=selector,factor=factor,shape="box",x=x,y=y,z=z,width=width,depth=height if kind=="hole" else depth,height=height,entry=entry)
                p.setdefault("operations",[]).append(item)
                generate(p)
        st.caption(t('A seleção de arestas usa posição/orientação. Seleção por clique em face/aresta e histórico do SketchUp não estão implementados. Uma operação incompatível bloqueia a atualização e a exportação.'))
        if p.get("operations"):
            st.json(localize_report(p['operations']))
            if st.button(t('Desfazer última operação'), key='ui_operation_controls_433'):
                p["operations"].pop();generate(p);st.rerun()
            with st.expander(t('Alterar operações numericamente (JSON)')):
                text=st.text_area(t('Lista de operações'),json.dumps(p["operations"],ensure_ascii=False,indent=2), key='ui_operation_controls_436')
                if st.button(t('Aplicar lista de operações'), key='ui_operation_controls_437'):
                    value=json.loads(text)
                    if not isinstance(value,list):raise ValueError(t('Informe uma lista JSON.'))
                    p["operations"]=value;generate(p)


def cad_page(p):
    st.title(t('Editor CAD'))
    if p["mode"]=="import":
        st.info(t('Modelo importado. Transformações e escolha de componente ficam em Importar Modelo 3D. As operações abaixo se aplicam ao componente CAD selecionado.'))
    else:param_controls(p)
    if st.button(t('Gerar / atualizar modelo'),type="primary", key='ui_cad_page_448'):
        generate(p)
    if p["mode"]!="import" or st.session_state.get("kind")=="cad":
        operation_controls(p)
    model,kind=current_model(p)
    if model is not None:show_model(model,kind)
    st.warning(t('Formas arbitrárias em uma só fotografia exigem reconstrução manual/assistida. Esta versão não recupera automaticamente superfícies ocultas ou geometrias orgânicas gerais.'))
    st.button(t('Continuar para exportação'),on_click=go_page,args=(PAGES[6],), key='ui_cad_page_455')


def import_page(p):
    st.title(t('Importar Modelo 3D'))
    st.write(t('STEP mantém sólidos CAD. STL, OBJ, GLB/GLTF são malhas sem histórico paramétrico. A importação nativa de SKP não está disponível.'))
    with st.expander(t('Como trazer um modelo do SketchUp')):
        st.write(t('No SketchUp, utilize Arquivo → Exportar → Modelo 3D e escolha um formato disponível em sua edição. Os formatos dependem da versão/licença. Use STL, OBJ ou GLB; DAE é opcional. Esta aplicação não precisa de assinatura ou serviço de conversão. STEP deve vir de um programa/exportador que realmente crie B-Rep sólido.'))
        st.write(t('STL/OBJ não têm unidade confiável: confirme a escala. GLTF aceita apenas buffers incorporados; arquivos externos de textura/material não são resolvidos. Em STEP, componentes são separados por sólido; nomes e hierarquia de montagem podem se perder.'))
    upload=st.file_uploader(t('Modelo intermediário'),type=["step","stp","stl","obj","glb","gltf","dae","skp"], key='ui_import_page_464')
    if upload and st.button(t('Ler modelo enviado'), key='ui_import_page_465'):
        loaded=import_model(upload.getvalue(),upload.name)
        p.update(mode="import",import_source={"filename":upload.name,"base64":base64.b64encode(upload.getvalue()).decode()},component_index=0,transform={"translation":[0,0,0],"rotation":[0,0,0],"scale":1.},operations=[])
        st.session_state.imported=loaded
        generate(p)
    if p["mode"]!="import":return
    if "imported" not in st.session_state:
        source=p["import_source"]
        st.session_state.imported=import_model(base64.b64decode(source["base64"]),source["filename"])
    loaded=st.session_state.imported
    for warning in loaded.get("warnings",[]):st.info(t(warning))
    p["component_index"]=st.selectbox(t('Componente ativo'),range(len(loaded["components"])),index=int(p.get("component_index",0)),format_func=lambda i, _language=get_language(): translate_in(_language, loaded['components'][i]['name']), key='ui_import_page_476')
    st.caption(t('A visualização e a exportação se referem ao componente ativo. Os demais componentes permanecem no arquivo original salvo no JSON.'))
    transform=p.setdefault("transform",{"translation":[0,0,0],"rotation":[0,0,0],"scale":1.})
    a,b,c=st.columns(3)
    translation=[localized_number_input(col, t('Translação {v1} (mm)', v1=axis), value=float(v), key='ui_import_page_480_' + axis) for col,axis,v in zip((a,b,c),"XYZ",transform["translation"])]
    a,b,c=st.columns(3)
    rotation=[localized_number_input(col, t('Rotação {v1} (graus)', v1=axis), value=float(v), key='ui_import_page_482_' + axis) for col,axis,v in zip((a,b,c),"XYZ",transform["rotation"])]
    scale=number(t('Escala uniforme / conversão de unidade'),transform["scale"],.00001,step=.1, key='ui_import_page_483')
    transform.update(translation=translation,rotation=rotation,scale=scale)
    if st.button(t('Aplicar transformação ao componente'),type="primary", key='ui_import_page_485'):generate(p)
    if loaded["kind"]=="mesh":
        st.warning(t('Esta é uma malha: pode mover, girar e escalar; fillets, raios e paredes paramétricas exigem reconstruir um sólido. Use Imagem para CAD ou formas assistidas como novo projeto de referência.'))
    model,kind=current_model(p)
    if model is not None:show_model(model,kind)


def export_page(p):
    st.title(t('Exportar projeto'))
    st.download_button(t('Salvar projeto paramétrico JSON'),storage.dumps(p),file_name="projeto_contorno.json",mime="application/json", key='ui_export_page_494')
    st.caption(t('O JSON preserva a fotografia, calibração, perfil, parâmetros, operações e arquivo importado quando houver. Reabra-o pela barra lateral e gere o modelo novamente.'))
    model,kind=current_model(p)
    if model is None:return
    if st.button(t('Validar geometria e preparar arquivos'),type="primary", key='ui_export_page_498'):
        with st.spinner(t('Exportando e reimportando os arquivos para verificar a geometria…')):
            st.session_state.exports=export_bundle(model,p,kind)
            st.session_state.export_signature=storage.signature(p)
            st.session_state.export_language=get_language()
    files=st.session_state.get("exports")
    if files and st.session_state.get("export_signature")==storage.signature(p) and st.session_state.get("export_language")==get_language():
        st.success(t('Verificação concluída: STL reimportado fechado/orientado; STEP reimportado válido quando existe sólido CAD.'))
        for filename,data in files.items():
            st.download_button(t('Baixar {filename}', filename=filename),data,file_name=filename,key="dl_"+filename)
        st.download_button(t('Baixar ZIP completo deste projeto'),export_project_zip(files),file_name="projeto_contorno.zip",mime="application/zip", key='ui_export_page_507')
        st.json(localize_report(json.loads(files['relatorio_geometria.json'])))
    if kind=="mesh":st.info(t('STEP indisponível: o componente é uma malha. Nenhuma conversão automática para sólido foi presumida.'))


def run():
    st.set_page_config(page_title="Contorno CAD",page_icon="◈",layout="wide")
    language_column, _ = st.columns([2, 5])
    language = language_column.selectbox("Language / Idioma", list(LANGUAGES),
                                         format_func=LANGUAGES.get, key="language")
    set_language(language)
    if "project" not in st.session_state:st.session_state.project=storage.new_project()
    if "revision" not in st.session_state:st.session_state.revision=0
    p=st.session_state.project
    with st.sidebar:
        st.title(t('◈ Contorno CAD'))
        st.caption(t('Reconstrução assistida · local · mm'))
        route=st.radio(t('Fluxo de trabalho'),PAGES,key="route", format_func=formatter())
        st.divider()
        p["name"]=st.text_input(t('Nome do projeto'),p.get("name","Novo projeto"), key='ui_run_522')
        restore=st.file_uploader(t('Reabrir projeto JSON'),type=["json"],key="restore")
        if restore and st.button(t('Reabrir projeto salvo'), key='ui_run_524'):
            reset_project(storage.loads(restore.getvalue()));st.rerun()
        st.download_button(t('Salvar projeto agora'),storage.dumps(p),file_name="projeto_contorno.json",mime="application/json", key='ui_run_526')
        if st.button(t('Novo projeto vazio'), key='ui_run_527'):
            reset_project(storage.new_project());st.rerun()
        st.caption(t('Dados permanecem nesta sessão. Salve o JSON antes de fechar o navegador ou reiniciar o servidor.'))
    try:
        if route==PAGES[0]:home(p)
        elif route==PAGES[1]:image_page(p)
        elif route==PAGES[2]:profile_page(p)
        elif route==PAGES[3]:cad_page(p)
        elif route==PAGES[4]:import_page(p)
        elif route==PAGES[5]:
            st.title(t('Visualizador 3D'))
            model,kind=current_model(p)
            if model is not None:show_model(model,kind)
        else:export_page(p)
    except Exception as exc:
        st.error(t('Não foi possível concluir esta etapa: {v1}', v1=exc))
        st.caption(t('Revise os parâmetros. O projeto atual continua disponível para salvar e corrigir.'))
