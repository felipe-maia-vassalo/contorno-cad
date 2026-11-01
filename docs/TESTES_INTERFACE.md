# Streamlit interface evidence

The application entry point is `iniciar_cad.py`. AppTest runs the actual Streamlit code, OpenCV, CadQuery and OpenCascade. It does not itself perform visual inspection, mouse gestures or native file selection.

```bash
python scripts/preparar_casadi.py --verificar
python -m pytest tests/test_ui.py tests/test_i18n.py -q
```

The original five UI tests passed on 2026-10-22 (`5 passed, 15 warnings in 8.57s`). They explicitly select Portuguese to retain coverage of the optional language. Later bilingual and fresh-English tests have their own logs; see `evidencias/pytest_english.txt` for the latest executed suite rather than treating the historical count as current.

| Test path | What is verified |
|---|---|
| Seven pages with photo fixture | No unexpected exceptions/errors; image and profile remain in session. |
| Real example JPEG button -> crop -> threshold -> side -> calibration -> profile -> CAD | Actual original bytes, nonempty OpenCV mask, emitted images, mm profile and valid solid. |
| Generate -> export -> change dome -> regenerate -> save/reopen | Height 45 -> 48 mm, larger volume, stale-export blocking, valid reimported STL/STEP, ZIP integrity and reconstructible JSON. |
| Two-component GLB fixture -> active component -> transform -> export | Component count, expected 1.1³ volume factor/center and valid STL, with no fictitious mesh STEP. |
| Invalid 1,000 mm socket diameter | Clear failure; old geometry is not offered as current export. |
| Fresh English session and language changes | English initial controls/project name, optional Portuguese and preserved edits/project/geometry. |

Fixtures inserted into `session_state` are documented as fixtures, not uploads through a file chooser. The example button reads an actual included JPEG. JSON tests use the real parser/new session. Download tests inspect produced bytes and emitted links, not an OS-completed download.

## Browser captures

`evidencias/00_painel_real.jpg` through `10_calibracao_pontos_real.jpg` are historical real browser captures of the original Portuguese interface: home, contour processing, profile editing/overlay, 45 mm model, rotated view, modified 48 mm model, export checks, manual point edit and calibration. They are retained in their original language/date. Generated OpenCV overlays are separately identified and are not presented as screenshots.

The English update has automated AppTest and real JavaScript render-handler verification. No new English browser capture is claimed unless separately recorded. The JavaScript harness covers translated labels and pending-point preservation; it does not replace all browser drag/rotate interactions.

## Geometry regressions linked to viewing

Zero-area/duplicate CAD triangles can be removed only with logged counts and preserved volume/bounds. The final STL bytes are reimported and checked. B-rep bounds are computed without relying on cached triangulation, which can otherwise inflate a spline's bounding box after viewing. A test displays a custom spline before STEP export and requires stable bounds before/after viewing and reimport.

The reproducible demo supplements these tests. Physical measurement and engineering fit/manufacturing evaluation remain necessary.
