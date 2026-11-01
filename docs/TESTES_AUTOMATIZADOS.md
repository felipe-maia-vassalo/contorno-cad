# Automated evidence with real photographs

The original demonstration ran on 2026-10-22 using macOS ARM64 / Python 3.12.14. The language/default-English regression runs are recorded separately in `evidencias/pytest_i18n.txt` and `evidencias/pytest_english.txt`. Consult those actual logs for counts and durations. Historical counts describe their recorded stage, not necessarily the current test inventory.

```bash
python scripts/demonstrar.py
python -m pytest -q
node tests/point_editor_i18n.cjs
```

Node is optional for app use, but executes the JavaScript component regression; without it, that test is skipped. OpenCV overlays/masks are calculated images, **not interface screenshots**. AppTest executes application logic and session state, not a full browser.

## Executed photo-to-CAD pipeline

1. Decode the actual 936 x 619 black-reference JPEG and verify its signature.
2. Crop `[20, 25, 495, 600]`; run grayscale, Gaussian blur, dark threshold 180 and 5-pixel morphological closing.
3. Select the external contour with pixel bounds `[42, 39, 431, 543]`; sample 12 right-side points.
4. Calibrate points `(257.5, 39)` and `(257.5, 581)` using the supplied approximate 45 mm: 45/542 = 0.0830258303 mm/pixel.
5. Convert to mm; approximate sampled radii range from 11.665 to 17.809 mm, subject to segmentation/perspective.
6. Revolve the assisted side profile, remapped to 39 mm, with a 6 mm spline dome. Cut a nominal 22.22 mm diameter, assumed 30 mm deep socket from the base.
7. Change dome rise to 9 mm and rebuild the same project.
8. Export/reimport both STL and STEP; check mesh closure/winding/positive volume and CAD validity/solid count/bounds/volume.
9. Save/reopen JSON and reconstruct, preserving photograph bytes, parameters, calibration and profile.

| Check | Baseline | Modified |
|---|---:|---:|
| Height | approximately 45 mm | approximately 48 mm |
| CAD volume | 18,503.48289166 mm³ | 19,144.32945587 mm³ |
| Valid closed solids | 1 | 1 |
| STL round trip | Passed | Passed |
| STEP round trip | Passed | Passed |

Volume increased by approximately 640.84656421 mm³. Initial STEP round-trip volume difference was approximately 1.26e-9 mm³. STL is a tessellated approximation: its baseline volume is about 18,462.4013 mm³, approximately 0.22% lower than CAD.

The CAD tessellator emitted one zero-area triangle at the revolution pole. Explicit normalization removed it (5,821 -> 5,820 triangles), preserving bounds/volume; no hole was filled and no vertex moved. The report logs the operation. Imported meshes are not silently repaired.

## White photograph and green curve

The actual 1280 x 1091 JPEG is segmented against its colored background. HSV detection identifies 8,098 green annotation pixels and extracts four relative dome controls:

| Relative radius | Relative rise |
|---:|---:|
| 0.90 | 0.308333 |
| 0.75 | 0.541667 |
| 0.50 | 0.825000 |
| 0.25 | 0.937500 |

The spline reaches the axis with a horizontal tangent. Its 6 mm rise and 45 mm total height are editable test assumptions, not measurements from the green mark. The valid solid volume is about 25,053.5572 mm³. Results are in `examples/branca/`.

## Intermediate import demonstration

The demo creates a two-instance GLB and an OBJ from the CAD tessellation. The importer preserves two GLB components; a selected component is scaled by 1.1, rotated 30 degrees and translated `(10, 5, 2)` mm, then exported/reimported as valid STL. Volume scales by 1.1³ = 1.331. These are generated fixtures: SketchUp was not run, no real SketchUp-export session is claimed and native SKP is unsupported.

## Coverage and evidence limits

Tests cover JPEG decoding/detection adjustments, calibration errors, coordinate round trips, smoothing, persistence, analytic extrusion/revolution volume, lines/arcs/splines, holes/booleans/loft/fillet/chamfer/scale, invalid material/socket configurations, STEP/STL round trips, GLB instances/transforms, open/inverted meshes, viewer sections, external-GLTF rejection, SKP rejection and ZIP name validation. Language tests cover all pages, fresh English startup, PT/EN switching, pending edits, unchanged geometry and English HTML exports.

The outline can include shadows near the black base. Neither topology tests nor valid exports certify measured accuracy, manufacturing clearance, strength, shrinkage or tolerance. See `../examples/relatorio_demonstracao.json` for raw results and [interface evidence](TESTES_INTERFACE.md) for the distinction between fixtures and actual browser interaction.
