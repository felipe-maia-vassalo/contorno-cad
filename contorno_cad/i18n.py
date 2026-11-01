"""Explicit PT/EN presentation translations; project values and IDs stay unchanged.

ContextVar keeps concurrent Streamlit sessions isolated. Backend functions use
Portuguese by default, including CLI/test runs without a selected language.
"""
from contextvars import ContextVar
from functools import lru_cache
import json
from pathlib import Path
import re
from string import Formatter

_LANGUAGE = ContextVar('contorno_language', default='pt')
ENGLISH = json.loads((Path(__file__).parent / 'locales' / 'en.json').read_text(encoding='utf-8'))
LANGUAGES = {'en': 'English (EN)', 'pt': 'Português (PT)'}


def set_language(language):
    if language not in LANGUAGES:
        raise ValueError('Unsupported language. Use pt or en.')
    _LANGUAGE.set(language)


def get_language():
    return _LANGUAGE.get()


def translate_in(language, message, **values):
    """Explicit locale for callbacks evaluated outside the rendering context."""
    token = _LANGUAGE.set(language)
    try:
        return t(message, **values)
    finally:
        _LANGUAGE.reset(token)


def formatter():
    language = get_language()
    return lambda value: translate_in(language, value)


@lru_cache(maxsize=1)
def _patterns():
    # Used for persisted, generated component names/notes; never changes files.
    patterns = []
    for source, target in ENGLISH.items():
        if '{' not in source:
            continue
        parts, fields = [], []
        for literal, field, spec, conversion in Formatter().parse(source):
            parts.append(re.escape(literal))
            if field is not None:
                fields.append(field)
                parts.append('(.*?)')
        patterns.append((re.compile('^' + ''.join(parts) + '$', re.DOTALL), fields, target))
    return patterns


def t(message, **values):
    """Translate a source message, then interpolate named fields safely."""
    source = str(message)
    if get_language() == 'pt':
        return source.format(**values) if values else source
    target = ENGLISH.get(source)
    if target is not None:
        return target.format(**values) if values else target
    if not values:
        for pattern, fields, template in _patterns():
            match = pattern.fullmatch(source)
            if match:
                # Captures are text, so strip numeric formatting on persisted strings.
                template = re.sub(r'\{([^}:!]+)(?:![^}:]+)?(?::[^}]+)?\}', r'{\1}', template)
                return template.format(**dict(zip(fields, match.groups())))
    return source.format(**values) if values else source


def localize_report(value):
    """Translate inspection labels for display only; JSON exports keep schema v1."""
    labels = {'representacao':'Representation', 'unidade':'Units', 'valido':'Valid',
              'solidos':'Solids', 'volume_mm3':'Volume (mm³)', 'limites_mm':'Bounds (mm)',
              'fechado':'Watertight / closed', 'fabricavel':'Mesh checks passed',
              'orientacao_consistente':'Consistent winding', 'volume_positivo':'Positive volume',
              'vertices':'Vertices', 'triangulos':'Triangles',
              'stl_reimportado':'Reimported STL', 'step_reimportado':'Reimported STEP',
              'diferenca_volume_step_mm3':'STEP volume difference (mm³)',
              'normalizacao_tesselacao_cad':'CAD tessellation normalization',
              'triangulos_antes':'Triangles before', 'triangulos_depois':'Triangles after',
              'triangulos_area_zero_removidos':'Zero-area triangles removed',
              'triangulos_duplicados_removidos':'Duplicate triangles removed',
              'fechado_antes':'Watertight before', 'fechado_depois':'Watertight after',
              'diferenca_volume_mm3':'Volume difference (mm³)', 'metodo':'Method'}
    if get_language() == 'pt':
        return value
    if isinstance(value, dict):
        return {labels.get(k,k):localize_report(v) for k,v in value.items()}
    if isinstance(value,list):
        return [localize_report(v) for v in value]
    return t(value) if isinstance(value,str) else value
