# Installation and operation

The Streamlit server runs OpenCV and the CAD kernel on the host computer. No photograph is sent to an AI/reconstruction API. Internet access is required to install packages; routine local use does not require a paid service. English is the initial interface language.

## Tested macOS installation

Use native 64-bit **Python 3.12** and macOS 14 or later. The executed environment was macOS 27.0.1, Apple Silicon ARM64, Python 3.12.14. Do not mix Intel/Rosetta Python with ARM wheels. Install Python from [python.org](https://www.python.org/downloads/) or a managed distribution, without replacing system Python.

```bash
git clone https://github.com/felipe-maia-vassalo/contorno-cad.git
cd contorno-cad
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/preparar_casadi.py
python scripts/preparar_casadi.py --verificar
python -m pip check
python -m streamlit run iniciar_cad.py --server.address 127.0.0.1
```

Open the printed URL, normally http://127.0.0.1:8501. Leave the terminal running; Ctrl+C stops it. Later, activate the same environment and run the final command again. `bash executar_macos.sh` is an alternative launcher. Use `--server.port 8502` if 8501 is occupied.

A compiler/Xcode is unnecessary when compatible wheels exist. If pip cannot find OCP/CadQuery wheels, check Python, platform and architecture first. Do not copy virtual environments between computers or change pinned versions without revalidation. See [CadQuery installation](https://cadquery.readthedocs.io/en/stable/installation.html).

## Mandatory CAD runtime preparation

Run `python scripts/preparar_casadi.py` after installing or reinstalling dependencies. The original CasADi wheel contains optional solvers including a legacy METIS library with restrictive terms. Preparation removes optional plugins/dependencies, archives legal texts and retains the audited core plus required C++ runtime. It refuses global Python or a different CasADi version. The app verifies the manifest, retained-file hashes and absence of optional items before importing CadQuery.

The tested macOS selection retains 9 core/type/runtime files, including LLVM `libc++.1.0.dylib`, and removes 235 optional top-level items. Optimization/constraint solving and CadQuery `Assembly.solve()` are unavailable; this application's geometry does not use them. Pip metadata still describes the original wheel; `casadi/contorno_core_manifest.json` describes the actual selection. Windows/Linux selections require separate native validation and may fail closed if the core cannot load.

## Windows (not validated)

The following is a starting procedure for Python 3.12 x64, not an executed Windows test. Create a fresh environment on the target:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/preparar_casadi.py
.\.venv\Scripts\python.exe scripts/preparar_casadi.py --verificar
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m streamlit run iniciar_cad.py --server.address 127.0.0.1
```

These commands do not need PowerShell activation-policy changes. Verify native dependencies, preparation and the full test suite before claiming support. Linux and Intel Macs also remain unvalidated.

## Data and local use

Follow the [user manual](../USER_MANUAL.md). JPEG -> contour -> calibration -> profile -> CAD -> validated export is the main workflow. Missing depths, clearances and dome dimensions remain explicit assumptions. Save JSON before closing/restarting; session state is not disk persistence. STL/STEP preserve geometry, not the complete application project.

## Future internal deployment

The current version has no built-in authentication, permission management, shared project database or isolated CAD job queue. The supplied configuration binds to **127.0.0.1**, enables CORS/XSRF protection, limits uploads to 30 MB and disables usage telemetry.

For an internal server, use a dedicated machine/service user and isolated environment. Keep Streamlit on loopback behind a reverse proxy with corporate authentication, TLS and WebSocket support. Restrict access to the intended network/VPN; apply CPU/memory/session limits, backups and retention rules for images/projects/logs. Introduce isolated processes/a queue before heavy concurrent CAD use. Test upgrades in staging and keep rollback artifacts. Do not substitute an unauthenticated public `0.0.0.0` listener for deployment controls. Public hosting has not been performed.

## Troubleshooting

| Symptom | Action |
|---|---|
| `streamlit: command not found` | Activate `.venv` or use its Python with `-m streamlit`. |
| `No matching distribution` | Check Python 3.12, architecture and compatible wheels. |
| Native import failure | Reinstall on the target, prepare CasADi and run `pip check`. |
| Missing/changed core manifest | Repeat preparation in the dedicated environment. |
| No useful contour | Crop, adjust segmentation or draw/correct the profile manually. |
| Revolution/fillet fails | Check crossing points, negative radii, axis, remaining material and feature size. |
| Open mesh blocked from export | Repair it in an appropriate tool or reconstruct a closed CAD solid. |
| STEP has no parameters | Save/reopen project JSON for this application's parameters. |
| Work lost after restart | Reopen the saved JSON; session state is temporary. |

Report the operation, Python/platform/architecture, error and a minimal reproducible project. Remove confidential images/data before sharing. Source distribution contains no interpreter/venv/wheels. A future installer or container needs a new binary license/source/relinking review; see [licenses](LICENCAS.md).
