# Delivery report - Contorno CAD 0.2.1

English edition prepared on 2026-11-01 for sharing with university readers.

## Delivered implementation

A new modular local Python/Streamlit application: OpenCV JPEG/PNG processing, contour selection/manual correction, two-point mm calibration, line/arc/spline profile editing, CadQuery/OpenCascade solids, interactive visualization, editable spline-dome end cap, extrusion/revolution/assisted primitives, compatible solid operations, CAD/mesh import, validated exports and project persistence. English is the initial UI language; Portuguese remains selectable. The entry point is `iniciar_cad.py`.

The application was built from scratch for this project, without reusing the prior Formlab code/architecture. Modules separate UI, images, profiles, CAD, import/export, viewer, persistence and translation. No AI/reconstruction API, commercial credits or ChatGPT integration is required.

## Demonstrated results

Actual supplied black/white JPEGs were processed. The black silhouette was calibrated using the supplied approximate 45 mm reference, then converted to an editable 12-point side profile. A 39 mm side plus assumed 6 mm spline dome produced a valid 45 mm CAD solid with volume 18,503.48289166 mm³. Changing dome rise to 9 mm produced a 48 mm solid with volume 19,144.32945587 mm³. Both passed STL/STEP export/reimport. JSON reopening preserves construction data and reference bytes. White-photo green-curve controls and intermediate GLB/OBJ import are also demonstrated.

These are assisted geometric reconstructions, not exact dimensional scans. The black contour includes some shadow; 45 mm is approximate, external radii are inferred and 30 mm socket depth is an assumption. Nominal 22.22 mm is not a manufacturing fit guarantee. The white scale is a separate test assumption. SketchUp was not executed; its intermediate-format fixtures were generated from this CAD model.

## Verification

Latest executed regression: **45 passed, 23 dependency warnings, 18.58 seconds**, macOS ARM64 / Python 3.12.14. Logs are in `docs/evidencias/pytest_english.txt` and `.xml`. Coverage includes actual JPEG/OpenCV, curves/solids/operations, stale model rejection, geometry round trips, import transforms, persistence, all pages, language isolation/switching, fresh English startup and the real JavaScript component render handler.

Historical real browser captures in `docs/evidencias/` show the original Portuguese UI. No new English browser screenshot is claimed. OpenCV overlays are calculated evidence and are not screenshots. Automated AppTest/JavaScript coverage does not replace every interactive browser gesture or physical dimensional verification.

## Files and reading order

Start with `README.md`, then `USER_MANUAL.md` or the illustrated English PDF in `docs/Contorno_CAD_User_Manual.pdf`. `README_EN.md` is an English alias; `README_PT.md` is optional Portuguese guidance. Feature limits, deployment, test evidence and licensing are documented in `docs/`. `examples/` contains both JPEGs, extracted profile, baseline/modified/white CAD, HTML previews and import fixtures. `requirements.txt` pins dependencies; `scripts/` contains runtime preparation and reproducible demonstration.

The source archive excludes virtual environments, caches, secrets and dependency binaries. The original source is MIT; photographs are not relicensed and third-party components retain their own licenses. Mandatory CasADi preparation removes excluded optional solvers. Binary redistribution needs the documented platform-specific license/source review.

## Remaining limitations

Windows/Linux/Intel native validation; full sketch constraints/handles/undo; face/edge picking and measurement; general shell/sweep and organic surfaces; full assembly editing/export; optional DAE and real SketchUp-export validation; multiuser authentication/storage/isolated jobs. No universal one-photo conversion, hidden-surface recovery or native SKP support is promised.

The source repository is `https://github.com/felipe-maia-vassalo/contorno-cad`. It is source distribution, not an online hosted Streamlit service. Installation and tests must be run on the reader's compatible machine. No university affiliation or endorsement is claimed.
