# Third-party notices

Recorded audit: **2026-10-22**. English edition: 2026-11-01.

Independent libraries retain their own copyrights/licenses. The application's MIT license does not relicense them. This source repository/archive does not include a Python interpreter, virtual environment or dependency wheels. Preserve installed `LICENSE`, `COPYING`, `NOTICE` and equivalent texts whenever redistributing those packages.

**This application uses functionality provided by Open CASCADE Technology (OCCT), through CadQuery/OCP. OCCT is available under GNU LGPL version 2.1 with Open CASCADE exception version 1.0; users have the rights provided by those texts.**

- [OCCT LGPL-2.1](https://github.com/Open-Cascade-SAS/OCCT/blob/master/LICENSE_LGPL_21.txt)
- [OCCT exception](https://github.com/Open-Cascade-SAS/OCCT/blob/master/OCCT_LGPL_EXCEPTION.txt)
- [OCCT source](https://github.com/Open-Cascade-SAS/OCCT)
- [OCP bindings](https://github.com/CadQuery/OCP)

The Apache-2.0 wrapper does not change the kernel's LGPL license. CasADi, NLopt and native components may require matching source and replacement/relinking provisions in a binary distribution. Read the [license audit](docs/LICENCAS.md) before packaging an installer/environment.

## Mandatory runtime selection

The full original CasADi wheel includes optional plugins and a legacy METIS 4 library with restrictive terms. It is not the approved runtime selection. After installing requirements, run `python scripts/preparar_casadi.py`: it removes optional plugins/dependencies including METIS/COIN/IPOPT/MUMPS and retains the LGPL-3.0-or-later core plus necessary open-source C++ runtime. The app checks the selection before loading CAD.

The tested macOS ARM64 selection retains 9 files and removes 235 optional top-level items. Its 80 original legal texts are archived in `casadi/contorno_legal`; deleted binaries are not retained merely because their notices are archived. `contorno_core_manifest.json` records SHA-256 and composition. LLVM libc++ retains its Apache-2.0/LLVM-exception and applicable historical MIT/NCSA notices. Preparation, repeated verification and rejection of an unexpected optional file were tested. Optimization/assembly-constraint solving is unavailable. Other platforms need separate native validation.

## Recorded environment inventory

Extracted using `importlib.metadata` from Python 3.12.14 on macOS ARM64. These were installed versions for the original validation, including transitive packages and the pip environment tool. The declared-license column is wheel metadata; 'metadata' means this report did not independently audit all package source. Long metadata licenses are summarized by family. Review does not imply every incorporated native component was exhaustively inspected.

| Package | Installed version | Declared license | Review / note |
|---|---|---|---|
| `aiohappyeyeballs` | 2.7.1 | PSF-2.0 | metadata; preserve distribution notices |
| `aiohttp` | 3.14.5 | Apache-2.0 AND MIT | metadata; preserve distribution notices |
| `aiosignal` | 1.4.0 | Apache 2.0 | metadata; preserve distribution notices |
| `altair` | 6.3.0 | BSD text (metadata) | metadata; preserve distribution notices |
| `anyio` | 4.15.1 | MIT | metadata; preserve distribution notices |
| `attrs` | 26.1.0 | MIT | metadata; preserve distribution notices |
| `cadquery` | 2.6.1 | Apache Public License 2.0 | Apache-2.0 |
| `cadquery-ocp` | 7.8.1.1.post1 | not stated | Apache-2.0 in LICENSE; native OCCT LGPL-2.1 + exception |
| `casadi` | 3.8.1 | GNU Lesser General Public License v3 or later (LGPLv3+) | LGPL-3.0-or-later core; optional plugins/dependencies removed by mandatory preparation |
| `certifi` | 2026.10.19 | MPL-2.0 | metadata; preserve distribution notices |
| `charset-normalizer` | 3.5.2 | MIT | metadata; preserve distribution notices |
| `click` | 8.5.0 | BSD-3-Clause | metadata; preserve distribution notices |
| `contourpy` | 1.4.0 | BSD-3-Clause | metadata; preserve distribution notices |
| `cycler` | 0.12.1 | BSD text (metadata) | metadata; preserve distribution notices |
| `ezdxf` | 1.4.5 | not stated; classifier MIT | metadata; preserve distribution notices |
| `fonttools` | 4.67.0 | MIT | metadata; preserve distribution notices |
| `frozenlist` | 1.8.0 | Apache-2.0 | metadata; preserve distribution notices |
| `h11` | 0.16.0 | MIT | metadata; preserve distribution notices |
| `idna` | 3.20 | BSD-3-Clause | metadata; preserve distribution notices |
| `iniconfig` | 2.3.1 | MIT | metadata; preserve distribution notices |
| `itsdangerous` | 2.2.0 | not stated; classifier BSD | metadata; preserve distribution notices |
| `Jinja2` | 3.1.6 | not stated; classifier BSD | metadata; preserve distribution notices |
| `jsonschema` | 4.26.0 | MIT | metadata; preserve distribution notices |
| `jsonschema-specifications` | 2025.9.1 | MIT | metadata; preserve distribution notices |
| `kiwisolver` | 1.5.1 | BSD text (metadata) | metadata; preserve distribution notices |
| `MarkupSafe` | 3.0.4 | BSD-3-Clause | metadata; preserve distribution notices |
| `matplotlib` | 3.11.2 | Matplotlib license (PSF-derived) | metadata; preserve distribution notices |
| `more-itertools` | 11.2.1 | MIT | metadata; preserve distribution notices |
| `msgpack` | 1.2.3 | Apache-2.0 | metadata; preserve distribution notices |
| `multidict` | 7.1.0 | Apache-2.0 | metadata; preserve distribution notices |
| `multimethod` | 1.12 | Apache-2.0 (full text) | metadata; preserve distribution notices |
| `narwhals` | 2.27.1 | MIT | metadata; preserve distribution notices |
| `nlopt` | 2.11.0 | MIT | wheel LICENSE: LGPL-2.1-or-later compiled library + MIT |
| `numpy` | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | BSD-3-Clause core; additional wheel licenses |
| `opencv-python-headless` | 5.0.0.93 | Apache 2.0 | wheel packaging MIT + native OpenCV Apache-2.0 + third parties |
| `packaging` | 26.3 | Apache-2.0 OR BSD-2-Clause | metadata; preserve distribution notices |
| `pandas` | 3.1.0 | BSD-3-Clause | BSD-3-Clause + wheel components |
| `path` | 17.1.1 | MIT | metadata; preserve distribution notices |
| `pillow` | 13.0.0 | MIT-CMU | MIT-CMU + bundled codecs |
| `pip` | 25.0.1 | MIT | metadata; preserve distribution notices |
| `plotly` | 7.1.0 | MIT | MIT; includes Plotly.js/notices |
| `pluggy` | 1.7.0 | MIT | metadata; preserve distribution notices |
| `propcache` | 0.5.4 | Apache-2.0 | metadata; preserve distribution notices |
| `protobuf` | 7.36.2 | 3-Clause BSD License | metadata; preserve distribution notices |
| `pyarrow` | 26.0.0 | Apache-2.0 | metadata; preserve distribution notices |
| `pydeck` | 0.9.3 | Apache License 2.0 | metadata; preserve distribution notices |
| `Pygments` | 2.21.0 | BSD-2-Clause | metadata; preserve distribution notices |
| `pyparsing` | 3.3.3 | MIT | metadata; preserve distribution notices |
| `pytest` | 9.1.1 | MIT | MIT |
| `python-dateutil` | 3.0.0 | Dual License | metadata; preserve distribution notices |
| `python-multipart` | 0.0.32 | Apache-2.0 | metadata; preserve distribution notices |
| `PyYAML` | 6.0.3 | MIT | metadata; preserve distribution notices |
| `referencing` | 0.37.0 | MIT | metadata; preserve distribution notices |
| `requests` | 2.34.2 | Apache-2.0 | metadata; preserve distribution notices |
| `rpds-py` | 2026.9.1 | MIT | metadata; preserve distribution notices |
| `scipy` | 1.18.1 | BSD-3-Clause (full text) | BSD-3-Clause core; additional wheel licenses |
| `six` | 1.17.0 | MIT | metadata; preserve distribution notices |
| `starlette` | 1.9.0 | BSD-3-Clause | metadata; preserve distribution notices |
| `streamlit` | 1.66.1 | Apache-2.0 | Apache-2.0 (official project; wheel does not list a license file) |
| `trame` | 4.0.0 | Apache License 2.0 | metadata; preserve distribution notices |
| `trame-client` | 4.1.4 | MIT | metadata; preserve distribution notices |
| `trame-common` | 1.2.9 | not stated; classifier Apache | metadata; preserve distribution notices |
| `trame-server` | 4.1.0 | Apache License 2.0 | metadata; preserve distribution notices |
| `trame-vtk` | 2.11.17 | BSD License | metadata; preserve distribution notices |
| `trimesh` | 5.1.1 | MIT (full text) | MIT |
| `typing_extensions` | 4.16.0 | PSF-2.0 | metadata; preserve distribution notices |
| `typish` | 1.9.3 | MIT | metadata; preserve distribution notices |
| `tzdata` | 2026.5 | Apache-2.0 | metadata; preserve distribution notices |
| `urllib3` | 2.8.0 | MIT | metadata; preserve distribution notices |
| `uvicorn` | 0.54.0 | BSD-3-Clause | metadata; preserve distribution notices |
| `vtk` | 9.3.1 | BSD | BSD-3-Clause + third parties |
| `websockets` | 17.3 | BSD-3-Clause | metadata; preserve distribution notices |
| `wslink` | 2.6.0 | not stated; classifier BSD | metadata; preserve distribution notices |
| `yarl` | 1.25.1 | Apache-2.0 | metadata; preserve distribution notices |


## Findings in installed files

- `cadquery_ocp/LICENSE` is the wrapper's Apache-2.0 license. Missing OCCT LGPL/exception files in a wheel listing do not change the kernel license; supply official texts and matching source for your own binary redistribution.
- OpenCV packaging's `LICENSE.txt` is MIT; its approximately 180 kB `LICENSE-3RD-PARTY.txt` covers incorporated components and must be retained in full.
- NLopt's installed `licenses/LICENSE` declares LGPL-2.1-or-later for the compiled library; MIT metadata does not make the whole wheel MIT.
- The original inventory found 20 license/notice-named files in NumPy, 19 in pandas, 5 in SciPy and 3 in Plotly. Counts do not establish a complete native-code audit.
- The original CasADi wheel had multiple plugins and 80 license/notice files. Core LGPL terms do not automatically cover every plugin. Mandatory preparation removes plugins and archives their notices for traceability.

## Reproduce the inventory

```bash
python -m pip list --format=json
python -m pip check
python -m pip freeze
```

Use `importlib.metadata.distribution("package").files` to locate LICENSE/COPYING/NOTICE/COPYRIGHT files. If metadata is incomplete, inspect the exact wheel and source version. This report identifies components and obligations; it is not a complete corresponding-source/notices bundle for a binary distribution. Prepare those materials before distributing a ready-made environment.
