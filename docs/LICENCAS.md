# Open-source licenses and business use

Audit date: **2026-10-22**. English documentation updated 2026-11-01. Scope: this application's source, the installed test environment and native components identified through package notices. This is the recorded audit of pinned versions, not a certification of all future installations. Installed version-specific license texts take precedence over a repository's current branch.

The source package contains no Python interpreter, virtual environment or dependency wheels. Dependencies are installed separately. The application's MIT license covers original application code, not dependency code, user photographs, trademarks, product designs or third-party industrial rights. Reference photographs retain their original rights; their inclusion does not grant a broader image license.

## Main components

| Component | Recorded license | Redistribution obligations |
|---|---|---|
| [Python](https://docs.python.org/3.12/license.html) | PSF-2.0 and incorporated notices | Retain licenses/copyrights if redistributing the interpreter; record relevant modifications. |
| [Streamlit](https://github.com/streamlit/streamlit/blob/develop/LICENSE) | Apache-2.0 | Include license/notices and identify modified library files. |
| [CadQuery](https://github.com/CadQuery/cadquery/blob/master/LICENSE) | Apache-2.0 | Retain license/notices and applicable modification notices. |
| [OCP wrapper](https://github.com/CadQuery/OCP/blob/master/LICENSE) | Apache-2.0 | Does not change the native OCCT kernel's LGPL license. |
| [OCCT](https://github.com/Open-Cascade-SAS/OCCT/blob/master/LICENSE_LGPL_21.txt) | LGPL-2.1 with [OCCT exception 1.0](https://github.com/Open-Cascade-SAS/OCCT/blob/master/OCCT_LGPL_EXCEPTION.txt) | Visible attribution, license/exception, corresponding-source and replacement/relinking conditions for binary distribution. |
| [opencv-python packaging](https://github.com/opencv/opencv-python/blob/4.x/LICENSE.txt) | MIT | Preserve copyright/permission and the wheel's third-party notices. |
| [OpenCV native library](https://github.com/opencv/opencv/blob/4.x/LICENSE) | Apache-2.0 in recent versions | Preserve license/notices; incorporated codecs/components have separate terms. |
| [NumPy](https://github.com/numpy/numpy/blob/main/LICENSE.txt), [SciPy](https://github.com/scipy/scipy/blob/main/LICENSE.txt), [pandas](https://github.com/pandas-dev/pandas/blob/main/LICENSE) | BSD-3-Clause cores | Preserve conditions/disclaimers; no endorsement; preserve bundled native notices. |
| [Trimesh](https://github.com/mikedh/trimesh/blob/main/LICENSE.md), [Plotly](https://github.com/plotly/plotly.py/blob/main/LICENSE.txt) | MIT | Preserve copyright/permission; exported HTML embeds Plotly.js and its notices. |
| [Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE) | MIT-CMU / historical PIL terms | Preserve notices and bundled codec terms; observe advertising/name restrictions. |
| [pytest](https://github.com/pytest-dev/pytest/blob/main/LICENSE) | MIT | Testing dependency; preserve notices if redistributed. |

Software licenses do not require publishing the user's generated CAD projects merely because these libraries were used. They also do not grant rights over a reconstructed third-party product.

## Mandatory CasADi selection

The original **CasADi 3.8.1 wheel is not approved here as a whole**. The recorded audit found a legacy METIS 4 component (`libcoinmetis`) with terms restricting business use beyond evaluation. Run `python scripts/preparar_casadi.py` after installation. It removes all optional solvers/plugins, headers and their dependencies, including METIS/COIN/IPOPT/MUMPS, archives legal texts and verifies the retained core. The application checks version, manifest, hashes and absence of optional items before loading CadQuery.

The validated macOS ARM64 selection retains nine files: `__init__.py`, `__init__.pyi`, `casadi.py`, `casadi.pyi`, `py.typed`, `_casadi.so`, `libcasadi.dylib`, `libcasadi.3.7.dylib`, and `libc++.1.0.dylib`. The retained [CasADi core](https://github.com/casadi/casadi/blob/main/LICENSE.txt) is LGPL-3.0-or-later. Required [LLVM libc++](https://github.com/llvm/llvm-project/blob/main/libcxx/LICENSE.TXT) uses Apache-2.0 with LLVM exceptions and historical MIT/NCSA terms as applicable. `otool -L` inspection of the binding/core showed this runtime and system-library dependencies, without the removed solvers.

Preparation removes 235 top-level optional items; 80 original legal files are archived under `casadi/contorno_legal`. `contorno_core_manifest.json` records retained-file SHA-256 hashes, removed items and the import check. Archived notices do not imply their deleted binaries remain installed. Pip metadata continues to describe the original wheel, so it is not the selected-composition manifest.

The app does not call CasADi optimization or CadQuery `Assembly.solve()`. Those operations are unsupported with this reduced environment. Only macOS ARM64 native composition was validated; a Windows/Linux runtime change needs identification and review before expanding the allowlist. Do not restore the full wheel simply to work around a native error.

## Other transitive/native dependencies

- [NLopt](https://github.com/stevengj/nlopt/blob/master/COPYING): the installed compiled library's license text includes LGPL-2.1-or-later with Luksan code, despite MIT package metadata. Do not assume a wheel is the MIT-only build.
- [VTK](https://github.com/Kitware/VTK/blob/master/Copyright.txt): BSD-3-Clause core with incorporated notices. It arrives transitively with OCP; this app's viewer uses Plotly.
- NumPy/SciPy wheels may include BLAS/LAPACK/OpenBLAS and Fortran runtimes. Pillow/OpenCV may include JPEG/PNG/zlib/TIFF/OpenEXR/FFmpeg components depending on platform/version. Preserve the wheel-specific notices. Headless OpenCV avoids the graphical Qt variant, not all native obligations.
- Certifi declares MPL-2.0. Distribution of covered files requires their notices and corresponding covered source/modifications under MPL; this file-level copyleft does not automatically relicense unrelated application files.
- Streamlit/web dependencies and browser-delivered JavaScript retain their own notices. Review them for a container, frozen executable or bundled installer.

## OCCT notice and binary distribution

**This application uses functionality provided by Open CASCADE Technology (OCCT), through CadQuery/OCP. OCCT is available under GNU LGPL version 2.1 with Open CASCADE exception version 1.0. Users have the rights provided by those licenses.**

The exception permits certain header-derived object-code uses; it does not relicense the whole kernel as Apache/MIT or remove the remaining LGPL conditions. For a binary distribution including OCCT:

1. Include LGPL-2.1, the exception and original copyright/notices.
2. Provide the corresponding source for the actual redistributed library version, including modifications, with the license-required materials/information. A generic link to the newest source is not a substitute for matching source.
3. Allow library modification and reverse engineering to debug such modifications; do not impose an incompatible EULA.
4. Use replaceable ABI-compatible libraries or provide necessary relinking materials where applicable. Frozen packaging needs its own assessment.
5. Record binary/source versions and hashes. Changes to OCCT itself remain subject to its license.

Similar source/notices/replacement/relinking considerations apply to CasADi, NLopt and other actually incorporated LGPL components. This source-only repository is not a corresponding-source bundle for a future binary installer.

## Use and distribution checklist

| Scenario | Required review |
|---|---|
| Local source install with pip | Keep notices and this audit; document the prepared environment. The selected components do not require a paid commercial CAD license. |
| Internal server | Preserve notices and control access/data. The listed LGPL libraries are not AGPL; remote use alone does not impose release of the entire app source. |
| Source-only sharing | Include `LICENSE`, this report and `THIRD_PARTY_NOTICES.md`; provide dependency installation instructions. |
| Installer/venv/wheels/container/device bundle | Audit platform-specific binaries and include full notices plus applicable corresponding-source/relinking materials, including native/plugin components. |

Before adding/updating a dependency, record its exact version, origin, license, native components and distribution method; run `pip check` and retain an inventory. This app does not depend on FreeCAD, proprietary SketchUp SDKs or AI/reconstruction services. Native SKP is unsupported; intermediate exports depend on the source software's own availability/license.
