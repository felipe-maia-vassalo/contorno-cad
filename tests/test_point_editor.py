"""Optional Node regression for the component's actual JavaScript render handler."""
from pathlib import Path
import shutil
import subprocess
import pytest


def test_component_language_render_preserves_pending_points():
    node=shutil.which('node')
    if node is None:
        pytest.skip('Node.js is optional and is needed only for the JavaScript test')
    result=subprocess.run([node,str(Path(__file__).with_name('point_editor_i18n.cjs'))],capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'passed' in result.stdout
