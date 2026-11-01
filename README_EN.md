# Contorno CAD

[English](README.md) | [Português brasileiro](README_PT.md)

A local Python and Streamlit application for **assisted reconstruction of editable CAD solids from photographs**, with real OpenCV image processing and CadQuery/OpenCascade geometry. It also imports supported CAD and mesh formats.

Choose **Português (PT)** or **English (EN)** using the **Language / Idioma** selector at the top of the app. You can switch at any time without changing project dimensions, profiles, or the generated solid. English is the default. Translation is bundled with the source; it requires no API or internet service.

This is an executable first version, not a universal single-photo 3D reconstruction system. A photo supplies a silhouette; you supply a known measurement, choose a construction method, and define missing dimensions. Measurements inferred from perspective images remain approximate.

## Browser-only evaluation

Cloud deployment support is prepared using `online_cad.py`. The app owner must complete Streamlit Community Cloud sign-in and verify the Linux build before publishing a live demo URL. See [online deployment notes](docs/ONLINE_DEMO.md). The GitHub repository URL itself is the source, not the running app.

## Requirements

- Python **3.12**, in a dedicated virtual environment.
- The tested platform is **macOS Apple Silicon (arm64)**. The pinned NumPy/SciPy arm64 wheels require macOS 14 or newer.
- Internet access is needed to install dependencies. Normal app use is local, with no paid APIs, reconstruction services, or AI credits.
- Windows, Linux, and Intel Macs have not been validated. Platform-specific wheels and the native runtime preparation require verification before claiming support.

The entry point is **`iniciar_cad.py`**. There is no need to replace an existing `app.py` from another project.

## Installation

Clone the public source repository, or choose **Code → Download ZIP** on GitHub:

```bash
git clone https://github.com/felipe-maia-vassalo/contorno-cad.git
cd contorno-cad
```


From the repository root (the folder containing `iniciar_cad.py`):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/preparar_casadi.py
python scripts/preparar_casadi.py --verificar
streamlit run iniciar_cad.py
```

Open the URL printed in the terminal, normally **http://127.0.0.1:8501**. Keep the terminal open while using the app. Press **Ctrl+C** to stop it. If port 8501 is occupied:

```bash
streamlit run iniciar_cad.py --server.port 8502
```

On later runs:

```bash
source .venv/bin/activate
streamlit run iniciar_cad.py
```

On macOS, `bash executar_macos.sh` is also available. It reuses an existing prepared environment or creates `.venv` when Python 3.12 is available. Its development-workspace fallback is optional; the standard installation above is independent of that workspace.

### Mandatory dependency preparation

**Do not skip `scripts/preparar_casadi.py`.** The audited CasADi 3.8.1 wheel contains optional solver libraries, including a legacy METIS binary with restrictive terms. The preparation script removes optional plugins and dependencies, retains the audited core and required open-source C++ runtime, archives legal notices, and writes an integrity manifest. The app checks that manifest before loading CadQuery.

The geometric operations used here do not use the removed optimization plugins. Assembly constraint solving through CasADi is unsupported. Run preparation again after reinstalling dependencies. The script operates only inside a virtual environment; do not use a shared environment belonging to another application.

See the [license audit](docs/LICENCAS.md) and [third-party notices](THIRD_PARTY_NOTICES.md). Do not redistribute unreviewed dependency wheels or virtual environments as if they were covered by the application's MIT license.

## First model: the included end cap

1. The app opens in **English (EN)**. Portuguese remains available in **Language / Idioma**.
2. On **Home**, click **Open calibrated end cap example**.
3. Open **Image to CAD** to review the original JPEG, crop, detected outline, and calibration.
4. Open **2D Profile Editor** to inspect or change the profile. For revolution, **X is the radius**, not the diameter; Y is height. Click **Apply profile coordinates** after table edits.
5. In **CAD Editor**, select **End cap • revolution with spline dome**, then click **Generate / update model**.
6. Rotate the actual tessellated solid in the viewer. Use the wheel to zoom and **Shift + drag** to pan.
7. Change **Dome rise (mm)** from **6** to **9**, then generate again. Total height changes from **45 to 48 mm**, and the solid's volume changes.
8. Set **Socket inner diameter (mm)** and **Socket depth (mm)** using actual measurements and the required clearance. Inspect the cross-section.
9. On **Export Project**, click **Validate geometry and prepare files**. Download STL, STEP, standalone HTML, JSON, the geometry report, or a project ZIP.
10. Save the JSON before closing. Reopen it with **Reopen project JSON → Reopen saved project**, then generate again.

The sample uses approximately 45 mm as a calibration reference, a 39 mm side height, and an assumed 6 mm dome rise. The side profile's height range is rescaled to the side height; its outer radii come from the calibrated silhouette and remain approximate. The detected outline includes some shadow near the base and needs manual review before dimensional manufacturing work.

The 22.22 mm socket reference is the nominal tube diameter, not a guarantee of fit. Its 30 mm depth is an editable assumption. The socket opens at the **bottom** of this reconstructed model. The black photo does not directly show the proposed dome in that orientation; it is explicitly added through assisted reconstruction.

## Using your own photograph

### 1. Prepare the image

Upload JPG, JPEG, or PNG, up to **30 MB / 24 megapixels**. Prefer:

- A sharp, complete object with a margin around it.
- A simple background contrasting with the object.
- Even lighting without strong shadows, reflections, or transparency.
- A camera perpendicular to the intended profile, centered on the part.
- A measured dimension or ruler in the same plane as the profile.

A side view suits axially symmetric parts reconstructed by revolution. A perpendicular view of a flat face suits a constant-depth extrusion. Hidden surfaces, perspective distortion, and arbitrary organic forms need additional measurements and manual reconstruction. The app includes this guidance directly above the image uploader.

### 2. Detect a contour

1. On **Image to CAD**, upload the file and confirm its filename and pixel resolution.
2. Adjust horizontal and vertical crop, contrast, and Gaussian filtering.
3. Choose **Dark object**, **Light object**, **Colored background**, or **Canny**. A threshold of zero enables Otsu for the light/dark methods.
4. Adjust thresholds, gap closing, and minimum contour area. Compare the original, numbered contours, and mask.
5. Select the intended contour. Use **Use closed outline (extrusion)** or **Use right side (revolution / end cap)** as appropriate.

The automatic side sampler assumes an axis near the contour center and samples one side. It is not an object recognizer. Review shadows, perspective, the suggested axis, and every extracted point.

### 3. Calibrate and edit

1. In the photo point editor, choose **Mark two calibration points**.
2. Click two points whose real distance you know, then **Apply points to step**. Alternatively, enter their pixel coordinates numerically.
3. Enter **Known distance (mm)**, **Axis / origin X (px)**, and **Base / origin Y (px)**.
4. Click **Confirm calibration and convert profile to mm**.
5. Select and drag points, add or remove them, or adjust the numerical table. Apply the edits.

Calibration converts pixels to millimeters; it does not correct perspective. There is no general unit selector: enter measurements in mm.

### 4. Build and modify

Choose the method matching the part, enter the missing dimensions, and click **Generate / update model**. After a change, regenerate before exporting. The app blocks stale geometry from being exported as the current model.

## Pages and features

| Page | Features |
|---|---|
| Home | New project, calibrated example, workflow shortcuts, dimensional assumptions. |
| Image to CAD | JPEG/PNG loading, crop, contrast/filtering, edge/threshold detection, contour selection, point editing, two-point calibration. |
| 2D Profile Editor | Numerical coordinates; lines, three-point arcs, spline sequences; side smoothing; first-sequence start/end tangents; real CAD curve preview over the photo. |
| CAD Editor | End cap, 360° revolution, extrusion, assisted primitive reconstruction, solid editing, regeneration. |
| Import 3D Model | STEP solids or supported meshes, available components, active-component selection, translation, rotation, uniform scale. |
| 3D Viewer | Rotate, zoom, pan, isometric/front/side/top views, edges, axes, overall dimensions, geometry inspection, Z cross-section. |
| Export Project | Validated STL/STEP, standalone HTML, project JSON, geometry report, ZIP. |

### Curves and reconstruction

- `line`: straight segment arriving at a point.
- `arc`: three-point circular arc; provide `mid_x` and `mid_y` for its intermediate point.
- `spline`: consecutive points interpolated by the CAD kernel. Start/end tangent directions can be assigned to the first sequence.
- **Smooth side profile with spline** requires at least three points with distinct heights. It is not a universal closed-outline smoothing tool.
- **Revolution** uses a nonnegative-radius profile on one side of the axis, optionally closed to the axis. It revolves through 360°.
- **Extrusion** uses a closed outline and user-entered depth. Internal image contours are not automatically imported as hole loops.
- **Assisted reconstruction** combines boxes/plates, cylinders, tubes, and lofts by union or subtraction. The first shape must add material. The UI creates a loft between two circles; more general supported sections can be defined in project data.
- **End cap dome** uses a real spline, with rise, shape, and optional normalized interior `r/h` controls. It need not have constant circular radius. The side profile's radii remain linked to the calibrated data.

The point-dragging canvas displays a control polyline. The overlaid CAD plot displays sampled actual lines, arcs, and splines. There are no Bézier handles or general sketch constraint solver.

### Solid editing

The app supports fillets, chamfers, cylindrical holes, rectangular cavities, union/subtraction with a box tool, uniform scale, and numerical operation-list editing. Edge groups are selected by position or orientation: highest, lowest, vertical, or all. Holes follow the global Z direction and enter from the top or bottom.

An incompatible operation raises a message instead of silently skipping the edit. Use **Undo last operation**, reduce the dimension, or choose another group. General face/edge clicking, arbitrary-face hole direction, organic surface modeling, and constant-wall shelling are not implemented.

The end cap wall-thickness tool calculates socket diameter from the outer radius **at the base**. Tapered walls do not gain constant thickness. Geometry checks do not certify material strength, mold shrinkage, tolerances, or manufacturing fit.

## Importing SketchUp / other 3D models

Export an intermediate format supported by your SketchUp edition/version, then import it here. Available SketchUp exporters depend on its licensing and version; this app requires no paid conversion service.

| Format | Representation and support |
|---|---|
| STEP / STP | Valid closed B-Rep solids; split into solid components; no original feature history. |
| STL / OBJ | Triangle meshes; inspect, translate, rotate, scale, export compatible results. Confirm units. |
| GLB | Mesh scenes with available components/instances and their transforms. |
| GLTF | Embedded buffers/images only; external assets are rejected. Prefer GLB. |
| DAE | Optional reader, not installed or validated in the standard dependency set. |
| SKP | No native support. Export an intermediate format. |

Visualization, transformations, and export apply to the **active component**. Other components stay in the original source file embedded in the JSON; the app does not persist edited transforms for a complete assembly. Transform order is scale → rotations → translation, around the global origin.

Meshes do not acquire a parametric solid history. Fillets, radii, and controlled walls may require rebuilding a solid from measurements and reference geometry.

## Saving and exporting

- **Project JSON:** embeds the photograph or imported source, calibration, profile, parameters, and operations. Reopen it and regenerate. Data stays compatible across PT/EN. User names, filenames, annotations embedded in photographs, and technical schema keys are preserved.
- **STL:** exported bytes are reimported and checked for watertightness, consistent winding, and positive volume. Invalid manufacturing meshes are blocked.
- **STEP:** offered only for valid closed CAD solids. Reimport checks validity, volume, bounds, and solid count.
- **HTML:** an interactive Plotly viewer with JavaScript embedded; no CDN is required. Prepare exports again after switching language to get viewer labels in that language.
- **ZIP:** packages the validated exports, project JSON, HTML, and geometry report. Extract its JSON to reopen the project; the UI does not import the ZIP directly.

Zero-area or duplicate faces emitted by CAD tessellation can be removed only with the operation recorded and unchanged volume/bounds. Imported mesh holes are not automatically filled. The visual mesh/STL approximates the CAD surfaces.

UI text, application validation messages, the photo point editor, and plot labels switch language. Raw JSON file schemas, user data, original photographs, and third-party diagnostic text are not rewritten. Technical exported report keys remain compatible with the existing schema; the on-screen inspection uses localized labels.

## Examples and tests

```bash
python -m pytest -q
python scripts/demonstrar.py
```

Tests cover real JPEG processing, calibration, profile curves, CAD operations, effective geometry changes, persistence, valid STL/STEP round trips, mesh scenes/transforms, invalid geometry, Streamlit workflows, and PT/EN switching. The JavaScript point editor also has a render/state regression test when Node.js is available; Node is not required to run the app.

The demonstration uses both supplied photographs. It also creates/imports GLB and OBJ intermediate examples; these were generated from this application's CAD, not exported from an actual SketchUp session.

Useful example files:

- `examples/demo_project.json`: reopenable calibrated project with embedded real JPEG.
- `examples/modelo.step`, `modelo.stl`, `previa.html`: baseline end cap.
- `examples/modificado/`: modified dome.
- `examples/branca/`: white reference part and green-annotation spline demonstration. Its dimensions are explicitly assumed.
- `examples/importacao/`: intermediate import and transformation examples.
- `examples/relatorio_demonstracao.json`: machine-readable evidence.

The English test reports and manual describe the implementation; historical browser captures retain their original Portuguese labels. [Language support notes](docs/I18N.md) describe the bilingual update. Runtime session state is not a backup: save the JSON before closing or restarting.

## Troubleshooting

- **Preparation missing / unexpected optional dependency:** activate `.venv`, rerun `python scripts/preparar_casadi.py`, then restart.
- **No matching distribution:** confirm Python 3.12, supported OS, and native architecture. Do not mix arm64 and Rosetta packages.
- **No contour:** adjust crop, contrast, detection method, or draw the profile manually.
- **Negative radius:** correct the axis and keep the revolution profile on one side.
- **Socket breaks through:** reduce socket diameter/depth or deliberately increase body dimensions.
- **Fillet/chamfer fails:** use a smaller size or another edge group, or undo the operation.
- **Open/inverted mesh:** repair it in the source program; manufacturing STL export stays blocked.
- **Outdated model:** regenerate after the last geometry change.

## Project structure

```text
iniciar_cad.py                  Streamlit entry point
contorno_cad/ui.py              Pages and UI state
contorno_cad/i18n.py            Session-local PT/EN translation
contorno_cad/locales/en.json    English message catalog
contorno_cad/imaging.py         Photo decoding and OpenCV processing
contorno_cad/profiles.py        Calibration and profile coordinates
contorno_cad/cad.py             CadQuery/OpenCascade solid operations
contorno_cad/io3d.py            Import, validation, and export
contorno_cad/viewer.py          Actual CAD/mesh visualization
contorno_cad/project.py         Versioned JSON persistence
scripts/                       Dependency preparation and demonstration
tests/                         Unit, integration, UI, and language tests
```

The server binds to `127.0.0.1` by default. Internal deployment needs explicit authentication, HTTPS, access control, resource limits, and platform validation. See [deployment notes](docs/IMPLANTACAO.md). No multi-user database or public hosting is included.

## License

Original application code: [MIT](LICENSE). Third-party dependencies retain their own licenses, including applicable OCCT, CasADi-core, and NLopt obligations. Review [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [docs/LICENCAS.md](docs/LICENCAS.md) before redistribution. User-provided reference photographs are **not** relicensed under the application's MIT license.

## Documentation for reviewers

- [Illustrated user manual](USER_MANUAL.md) and [PDF manual](docs/Contorno_CAD_User_Manual.pdf).
- [Implemented features and limitations](docs/FUNCIONALIDADES_E_LIMITACOES.md).
- [Automated verification](docs/TESTES_AUTOMATIZADOS.md) and [interface evidence](docs/TESTES_INTERFACE.md).
- [Installation and internal deployment](docs/IMPLANTACAO.md).
- [License audit](docs/LICENCAS.md) and [third-party notices](THIRD_PARTY_NOTICES.md).
- [Delivery report](RELATORIO_DA_ENTREGA.md) and [language implementation](docs/I18N.md).

The main documentation is in English. Some historical screenshots, original photographs, schema keys and legacy filenames retain their original Portuguese text. They have not been altered to look like new English-language evidence. No affiliation with or endorsement by a university is claimed.
