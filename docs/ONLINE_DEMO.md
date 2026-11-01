# Online evaluation deployment

**Live app: https://contorno-cad.streamlit.app/**

Deployed and verified on 1 November 2026, Streamlit Community Cloud, Debian Linux amd64, Python 3.12.16. Public sharing is enabled in the provider UI. Reviewers need only a browser.

## Owner deployment settings

- Repository: `felipe-maia-vassalo/contorno-cad`
- Branch: `main`
- Main file path: `online_cad.py`
- Advanced settings: Python **3.12**
- No application secrets or paid API keys are required.

Sign in at https://share.streamlit.io/, connect the intended GitHub account and create an app from this repository. Use a public reviewer-facing app. Select an available URL label in the deployment form; do not advertise an unverified guessed URL.

Community Cloud installs `requirements.txt` and Debian libraries listed in `packages.txt`. `online_cad.py` automatically creates an app-owned selected CasADi core in temporary storage before importing the CAD engine; the managed host environment remains unchanged. Only allowlisted core/runtime files and legal notices are copied. A fresh subprocess verifies the selected native core before it is exposed on the import path. Existing invalid/changed manifests are rejected rather than silently repaired. A process/thread lock serializes preparation; the prepared runtime is cached across sessions. The normal local entry point `iniciar_cad.py` retains its explicit preparation behavior.

## Verification before sharing

Check build/runtime logs, confirm English startup, open the included calibrated example, generate the real solid, change dome rise, regenerate, prepare STL/STEP, and download/reimport when supported by the validation environment. Distinguish the actual cloud/Linux test from the local macOS tests.

Prepared-entry verification on macOS: **50 tests passed**, including hosted-entry AppTest with real CAD generation/exports. `docs/evidencias/pytest_cloud_copy.txt` record the executed tests. Tests check read-only source preservation, exclusion of optional solvers, concurrent first-run copying, changed-copy rejection, and actual native-core import from the selected copy in a fresh process. These automated results are separate from the completed live Linux browser verification below.

## Reviewer use

Open the live URL above; no installation is required. Start with **Open calibrated end cap example**, then **CAD Editor -> Generate / update model**. Modify **Dome rise (mm)** and regenerate; use **Export Project -> Validate geometry and prepare files** for downloads. See the English user manual for the full workflow.

Uploaded files are processed by the hosting server, unlike the local installation. The app's project data remains in each session's server memory and is not intentionally saved to a shared project database. Hosting/platform logs and browser behavior remain governed by the provider. Use non-confidential test images. Download JSON before closing; sessions and ephemeral hosting storage are not backups.

## Hosting limits

Free Community Cloud resources are limited and can change. A sleeping app may need to wake; heavy CAD models or concurrent sessions can exceed available memory/CPU. This is a public evaluation demo, not a guaranteed-availability manufacturing service. If the native kernel or resource footprint cannot run reliably on this tier, use a separately authorized Linux/container host; no paid service is provisioned automatically.

This application needs a Python process and native OpenCascade libraries. GitHub Pages and static hosting do not execute it. The available Sites runtime is Cloudflare Workers and is not an appropriate native Streamlit/CAD host.

## Official references

- [Deploy your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Resources and app management](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)


## Completed live verification

The first deployment exposed a read-only managed-environment restriction. The corrected bootstrap copies only the allowlisted CasADi core/runtime files and legal texts to app-owned temporary storage, verifies a fresh native import and hashes, and leaves managed packages unchanged. The live app then started successfully.

In the actual hosted browser, the included 936 x 619 JPEG was processed with one detected contour; calibration was confirmed at 0.083026 mm/pixel. A real 45 mm solid displayed volume 18,503.48 mm³. Mouse rotation worked. Changing dome rise from 6 to 9 mm triggered stale-model protection; regeneration produced a 48 mm solid with volume 19,144.33 mm³. Cloud export reimport checks passed. The project ZIP was downloaded through the browser, and its STL/STEP were reimported successfully on the local Mac as an additional check.

Evidence: `evidencias/11_online_jpeg_contour_en.jpg`, `12_online_cad_45mm_en.jpg`, `13_online_cad_48mm_en.jpg`, `14_online_validated_exports_en.jpg`, and `online_verification.json`. These are new real English cloud screenshots, separate from historical Portuguese captures. The JPEG was loaded through the included example, not a new cloud file-chooser upload. Concurrent-user load, every CAD operation and an independent anonymous-browser session were not tested; public sharing was confirmed in the provider UI.

The provider installed Python 3.12.16 and applied its own dependency maintenance, including replacing pyarrow 26.0.0 with 24.0.0 and updating certifi/pip. The original macOS lockfile inventory is not claimed to be identical to this managed Linux environment. No binary installer/container is distributed by this deployment.
