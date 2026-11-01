# Implemented features and limitations

Release 0.2.1. This is a local tool for **assisted CAD reconstruction**: the photograph supplies a projected outline, while the user supplies scale, construction method and missing dimensions. CadQuery/OpenCascade creates actual B-rep solids; the viewer displays their tessellation. A single photograph does not determine hidden surfaces or exact dimensions.

## Workflow and pages

| Page | Implemented behavior |
|---|---|
| Home | Open a blank project or the calibrated real-photo example; review assumptions. |
| Image to CAD | Decode JPEG/PNG, crop, detect/select contours, edit photo points and calibrate. |
| 2D Profile Editor | Edit coordinates in mm, line/arc/spline segments, smoothing and spline end directions. |
| CAD Editor | Generate an end cap, general revolution, extrusion or primitive-based solid; apply CAD operations. |
| Import 3D Model | Import supported solids/meshes, select a component and transform it. |
| 3D Viewer | Rotate/pan/zoom, choose views, display edges/axes/bounds and a horizontal section. |
| Export Project | Save JSON; validate and prepare STL, eligible STEP, HTML, geometry report and ZIP. |

Pages share the Streamlit session project. Detector controls rerun processing. Geometry changes require **Generate / update model**. The app detects stale geometry and blocks its export until rebuilt. Operation failures are reported rather than silently skipped. Save JSON before closing the browser or restarting the server.

## Images and calibration

- Actual JPG/JPEG/PNG decoding, EXIF orientation and RGB conversion; limit 30 MB and 24 megapixels.
- Original image, numbered contours and processed mask/edges. Grayscale and Gaussian filtering run through OpenCV.
- Horizontal/vertical crop controls retain coordinates in the original photograph's frame.
- Dark/light threshold segmentation, optional Otsu threshold, Canny and a saturation-based colored-background method. Contrast, blur, gap closing and minimum area are adjustable.
- Up to 50 external contours sorted by area; pixel-tolerance simplification. This is contour detection, not object recognition.
- Closed outer outline for extrusion; internal holes are not automatically reconstructed as inner loops.
- Right-side sampler produces 12 points and suggests an axis/base, trimming small extreme regions. This assumes approximate axial symmetry and needs review for shadows and perspective.
- Canvas selection, dragging, adding/removing/clearing points and applying edits. Point order determines the profile; there is no snapping or sketch constraint solver.
- Two calibration points, clicked or entered numerically, plus a known distance in mm. Scale = real distance / pixel distance. Axis/origin are editable; vertical contour endpoints provide a shortcut.

All physical dimensions use **millimeters**. There is no global mm/cm/inch selector. Convert measurements to mm; use the import scale factor when necessary. Calibration does not correct perspective, lens distortion or differences in depth. A silhouette-derived diameter is approximate, not a caliper measurement. Prefer a sharp complete object, contrasting background, even lighting, a perpendicular camera and a measured reference in the same plane.

## Profiles and curves

The table edits X/Y and adds/removes rows. In revolution, X is **radius**, Y is height. Each incoming segment can be `line`, `arc` or `spline`. An arc needs an intermediate point and is built as a three-point arc. Consecutive spline points are interpolated by OpenCascade. PCHIP smoothing makes a 16-point side spline from at least three distinct heights; it is not a universal closed-outline smoother.

The first spline sequence can receive start/end tangent directions. This does not impose tangency across every segment. A CAD-sampled curve is shown over the photograph; the draggable canvas displays the control polygon. Pixel/mm conversion includes arc control points and tangent direction signs. There are no Bezier handles, full sketch constraints or general undo/redo. Crossed profiles, negative radii and incompatible curves are rejected.

## Reconstruction methods

**End cap with spline dome:** the side wall runs from base to shoulder. Calibrated radii are retained and its vertical span is remapped to the supplied side height. Total height = side height + dome rise. The dome is a real spline revolved through 360 degrees, with rise, shape and normalized internal controls. The apex has a horizontal tangent. This permits a variable-radius curve; controls outside the permitted order/height are rejected.

The socket is a blind cylindrical hole opening at the **base**, with editable diameter/depth. The kernel checks containment and remaining material. The base-wall helper derives the inner diameter for a requested thickness **at the base**; a tapered body does not thereby receive a constant-thickness wall. There is no general `shell` or organic surface offset.

**General revolution:** 360-degree rotation in the XZ plane; close a side to the axis or use a closed annular section. Radii must be nonnegative. Partial-angle rotation is not exposed.

**Extrusion:** a closed line/arc/spline outline with positive user-supplied depth. The section is constant through that depth; depth is not inferred from the image.

**Assisted reconstruction:** boxes/plates, cylinders, tubes and lofts combined by union/subtraction. The first primitive must add material. The UI creates a loft between two circles; the engine can accept multiple circular/rectangular sections through project data. Detailed changes to existing primitives may require recreating them or editing JSON. This is not a complete industrial CAD feature tree.

## Solid editing

| Operation | Scope |
|---|---|
| Fillet / chamfer | Actual B-rep operations; select top, bottom, vertical or all edges and enter a size. Topology or excessive radius can make an operation fail. |
| Holes | Cylindrical X/Y-positioned holes from top/base along global Z; diameter and depth are editable. |
| Cavity | Positioned rectangular box subtraction. |
| Union / subtraction | Box tool in the operation UI; supported primitives are also accepted through project data. |
| Dimensions / curves | Edit profile, end-cap parameters, extrusion depth and primitive dimensions, then regenerate. |
| Scale | Uniform scale, including holes and wall dimensions. |
| Operation list | Remove the last operation or edit the numerical JSON list. |

No interactive face/edge picking, 3D gizmos, natural-language commands, general shell/sweep, arbitrary NURBS surface editing or constrained assembly solver is implemented. An instruction such as 'set radius to 8 mm' must be applied through the appropriate numeric field.

## Import and transformation

| Format | Representation and limit |
|---|---|
| STEP/STP | Valid closed B-rep solids; one numbered component per solid. Compatible CAD operations are possible, without the original feature history. |
| STL | Triangulated mesh: inspect, translate, rotate and scale. No recovered parametric CAD features. |
| OBJ | Available mesh components; external materials are not reconstruction data. |
| GLB | Meshes and scene instances, with scene transforms applied. No assembly constraints. |
| GLTF | Embedded buffers/images only; external resources are rejected. Prefer GLB. |
| DAE | Optional `pycollada` path; not installed, audited or validated in the standard environment. |
| SKP | No native reader. The app explains the supported intermediate-format route. |

The source file is embedded in JSON. **Only the active component is displayed, transformed and exported.** Other components remain in the original stored source; edited full-scene export and independent persistent transforms for all components are not available. Transform order is scale, global-axis rotations, then translation, about the global origin. STL/OBJ units are not trustworthy; numbers are treated as mm. STEP names/hierarchy may be lost. Materials/textures do not become CAD geometry.

The demonstration imports a two-instance GLB and an OBJ generated from this project's CAD. SketchUp was not run and no native SKP file was converted. Export options in SketchUp depend on its edition/version.

## Viewer, exports and checks

Plotly shows the current solid/mesh, with front, side, top and isometric views, zoom/pan/rotate, CAD or triangle edges, axes and overall dimensions. The inspection report includes representation, bounds and volume. The Z section consists of intersections of the display mesh with a horizontal plane; it is not an analytical CAD section or destructive cut. There is no arbitrary section orientation or point-to-point measuring tool.

| Output | Behavior |
|---|---|
| STL | Reimported bytes must be watertight, consistently wound and positive-volume. |
| STEP | Only valid closed CAD solids; round trip checks validity, solid count, volume and bounds. Meshes are not disguised as STEP solids. |
| HTML | Interactive standalone Plotly.js viewer, without CDN dependency. Contains visualization geometry, not a feature history. |
| JSON | Image/source bytes, calibration, points, parameters and operations. Reopen and generate to reconstruct the solid. |
| ZIP | Validated exports, JSON, HTML and report. To reopen, extract and load JSON; direct ZIP import is not implemented. |

CAD tessellation normalization removes only exactly zero-area and duplicate triangles, logs counts and requires preserved volume/bounds. It does not fill holes, reverse faces or move vertices, and is not automatically applied to imported meshes. Geometric validity does not certify strength, tolerances, plastic shrinkage, fit, tooling or manufacturing suitability.

## Measured demonstration results

The black JPEG is 936 x 619 px. Its main contour has 663 raw points; 12 side points were sampled. Calibration uses the supplied **approximate** 45 mm / 542 px = 0.0830258303 mm/px. Side height 39 mm, dome rise 6 mm and socket depth 30 mm are assisted choices. The nominal bore is 22.22 mm. The silhouette-derived maximum diameter is about 35.618 mm, with no independent physical measurement.

| Model | Height | CAD volume |
|---|---:|---:|
| Baseline | 45 mm | 18,503.48289166 mm³ |
| Dome rise changed to 9 mm | 48 mm | 19,144.32945587 mm³ |

The volume changes by about 640.84656421 mm³. Both models pass STL/STEP export/reimport checks. The white JPEG is 1280 x 1091 px; the demo detects 8,098 green-mark pixels and samples four normalized dome controls. Its assumed 45 mm height is independent of the black reference. The green-mark extraction is implemented in the demo script; UI controls remain numerically editable. The example does not establish that the two photos depict identical geometry or that a nominal bore already has manufacturing clearance.

## Remaining work

Windows/Linux/Intel native validation; sketch constraints/handles/undo; interactive face/edge measurements; general shell and surface transitions; persistent multi-component assembly editing/export; DAE and real SketchUp-export validation; optional authenticated multiuser storage and isolated CAD jobs. Universal single-photo organic reconstruction and hidden-surface recovery remain outside the implemented scope.
