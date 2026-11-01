"""PT/EN presentation, language switching, and real CAD workflow regressions."""
import ast
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from string import Formatter
import pytest
from streamlit.testing.v1 import AppTest
from contorno_cad.i18n import ENGLISH, get_language, set_language, t
from contorno_cad import project as storage
from contorno_cad.cad import build_model, GeometryError, validate_solid
from contorno_cad.viewer import make_figure, figure_html

ROOT = Path(__file__).resolve().parents[1]
PAGES = ['Painel inicial','Imagem para CAD','Editor de perfil 2D','Editor CAD',
         'Importar Modelo 3D','Visualizador 3D','Exportar projeto']

@pytest.fixture(autouse=True)
def language_context():
    set_language('pt')
    yield
    set_language('pt')


def widget(items, label):
    return next(x for x in items if x.label == label)


def clean(at):
    assert not at.exception, [e.message for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    return at


def app(demo=True):
    at=AppTest.from_file(str(ROOT/'iniciar_cad.py'),default_timeout=60)
    at.session_state['language']='pt'
    if demo:at.session_state['project']=storage.loads((ROOT/'examples/demo_project.json').read_bytes())
    return clean(at.run())


def switch(at, language):
    widget(at.selectbox,'Language / Idioma').set_value(language).run()
    return clean(at)


def page(at, canonical, label='Workflow'):
    widget(at.radio,label).set_value(canonical).run()
    return clean(at)


def click(at, label):
    widget(at.button,label).click().run()
    return clean(at)


def test_catalog_has_all_explicit_messages_and_matching_placeholders():
    def fields(text):return {(name,spec,conv) for _,name,spec,conv in Formatter().parse(text) if name is not None}
    for source,target in ENGLISH.items():assert fields(source)==fields(target),(source,target)
    for path in (ROOT/'contorno_cad').glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='t' and node.args and isinstance(node.args[0],ast.Constant):
                assert node.args[0].value in ENGLISH,(path.name,node.args[0].value)


def test_context_is_isolated_between_threads_and_formats_values():
    def translate(language):
        set_language(language)
        return t('Editor CAD'),t('Escala confirmada: {v1:.6f} mm/pixel. Origem: {v3}.',v1=.125,v3=[1,2])
    with ThreadPoolExecutor(2) as pool:
        result=list(pool.map(translate,['pt','en']))
    assert result[0][0]=='Editor CAD' and result[1][0]=='CAD Editor'
    assert '0.125000' in result[1][1] and 'Origin:' in result[1][1]
    assert get_language()=='pt'
    with pytest.raises(ValueError):set_language('fr')


def test_all_seven_pages_and_photo_guide_in_english():
    at=switch(app(),'en')
    for name in PAGES:
        page(at,name)
        set_language('en')
        assert any(x.value==('Contorno CAD' if name==PAGES[0] else t(name)) for x in at.title)
    page(at,PAGES[1])
    assert any('**Known measurement:**' in x.value for x in at.markdown)
    assert at.get('image')[0].proto.imgs[0].caption=='Original image'
    assert any('Image received:' in x.value for x in at.success)
    # Canonical method codes remain compatible with saved Portuguese projects.
    assert widget(at.selectbox,'Method').value=='Escuro'


def test_switch_preserves_geometry_and_edits_and_exports_english_html():
    at=app()
    page(at,'Editor CAD','Fluxo de trabalho')
    widget(at.number_input,'Elevação do topo (mm)').set_value(9).run()
    click(at,'Gerar / atualizar modelo')
    before=storage.dumps(at.session_state['project'])
    signature=at.session_state['model_signature']
    volume=validate_solid(at.session_state['model'])['volume_mm3']
    switch(at,'en')
    assert widget(at.number_input,'Dome rise (mm)').value==9
    assert storage.dumps(at.session_state['project'])==before
    assert at.session_state['model_signature']==signature
    assert validate_solid(at.session_state['model'])['volume_mm3']==volume
    assert not any('project has changed' in x.value for x in at.warning)
    page(at,'Exportar projeto')
    click(at,'Validate geometry and prepare files')
    files=at.session_state['exports']
    assert {'modelo.stl','modelo.step','projeto.json','previa.html'} <= files.keys()
    assert b'CAD edges' in files['previa.html']
    assert storage.loads(files['projeto.json'])==at.session_state['project']
    switch(at,'pt')
    assert not at.get('download_button')[1:] or not any(x.label=='Baixar modelo.step' for x in at.get('download_button'))
    page(at,'Editor CAD','Fluxo de trabalho')
    assert widget(at.number_input,'Elevação do topo (mm)').value==9
    assert storage.dumps(at.session_state['project'])==before


def test_english_error_and_viewer_labels_and_portuguese_roundtrip():
    p=storage.loads((ROOT/'examples/demo_project.json').read_bytes())
    set_language('en')
    fig=make_figure(build_model(p),section_z=20)
    names={trace.name for trace in fig.data}
    assert {'CAD solid','CAD edges','Dimensions','Section Z = 20.00 mm'} <= names
    assert any('Height Z:' in a.text for a in fig.layout.scene.annotations)
    p['params']['inner_diameter']=1000
    with pytest.raises(GeometryError,match='inner diameter leaves the wall'):
        build_model(p)
    set_language('pt')
    with pytest.raises(GeometryError,match='parede muito fina'):
        build_model(p)


def test_language_preserves_unapplied_calibration_coordinates():
    at=app();page(at,'Imagem para CAD','Fluxo de trabalho')
    widget(at.number_input,'Distância conhecida (mm)').set_value(52).run()
    widget(at.number_input,'Eixo / origem X (px)').set_value(260).run()
    before=storage.dumps(at.session_state['project'])
    switch(at,'en')
    assert widget(at.number_input,'Known distance (mm)').value==52
    assert widget(at.number_input,'Axis / origin X (px)').value==260
    assert storage.dumps(at.session_state['project'])==before


def test_english_image_to_cad_calibration_and_invalid_geometry_message():
    at=switch(app(False),'en');page(at,'Imagem para CAD')
    click(at,'Load black end cap photo')
    widget(at.slider,'Horizontal crop (pixels)').set_value((20,495))
    widget(at.slider,'Vertical crop (pixels)').set_value((25,600))
    widget(at.selectbox,'Method').set_value('Escuro')
    widget(at.slider,'Light/dark threshold (0 = Otsu)').set_value(180)
    clean(at.run())
    click(at,'Use right side (revolution / end cap)')
    click(at,'Mark contour height endpoints for calibration')
    click(at,'Confirm calibration and convert profile to mm')
    assert all(v['x']>0 for v in at.session_state['project']['profile'])
    assert any('Confirmed scale:' in v.value for v in at.success)
    click(at,'Continue to 2D Profile');click(at,'Continue to CAD Editor')
    click(at,'Generate / update model')
    assert validate_solid(at.session_state['model'])['valid']
    widget(at.number_input,'Socket inner diameter (mm)').set_value(1000).run()
    widget(at.button,'Generate / update model').click().run()
    assert not at.exception
    assert any('inner diameter leaves the wall' in e.value for e in at.error)


def test_fresh_session_starts_in_english_and_portuguese_remains_selectable():
    at=AppTest.from_file(str(ROOT/'iniciar_cad.py'),default_timeout=60).run()
    clean(at)
    assert widget(at.selectbox,'Language / Idioma').value=='en'
    assert widget(at.text_input,'Project name').value=='New project'
    assert any(x.label=='Workflow' for x in at.radio)
    assert any(x.label=='Open Image to CAD' for x in at.button)
    switch(at,'pt')
    assert any(x.label=='Fluxo de trabalho' for x in at.radio)
    switch(at,'en')
    assert any(x.label=='Workflow' for x in at.radio)
