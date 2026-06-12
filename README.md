# Ask Flow Workbench

Ask Flow Workbench is a local web workbench for post-acquisition flow cytometry analysis of exported FCS files, with CSV fallback for simple event tables. It runs separately from acquisition software and works with exported files only.

## What It Is Not

Ask Flow Workbench is not instrument-control software. It does not connect to, control, automate, maintain, calibrate, clean, shut down, or communicate with any cytometer, sampler, driver, license server, firmware, USB interface, laser, fluidics system, or proprietary instrument workflow. It does not parse, modify, depend on, or reverse engineer proprietary `.ncf` files. It does not use Agilent, ACEA, NovoCyte, or NovoExpress logos, icons, screenshots, branding, or protected UI assets.

## Boundaries

- Post-acquisition analysis only.
- FCS-first and CSV fallback only.
- No hardware control.
- No NovoExpress calls.
- No `.ncf` parsing.
- No cloud dashboard or required API integration.
- No diagnosis or unsupported biological claims.
- Ask Flow is deterministic and local by default; enhanced cloud answers require explicit environment configuration.

## Why FCS-First

FCS is the standard interchange format for event-level cytometry data. Ask Flow Workbench uses FlowIO for lightweight FCS parsing and is structured for deeper FlowKit/FlowUtils support around compensation, transforms, and future GatingML-compatible workflows.

## Install

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Windows Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

## Run

```bash
python app/main.py
```

Open http://127.0.0.1:8050.

Optional enhanced assistant mode:

```bash
export ASK_FLOW_CLOUD_ASSISTANT_ENABLED=1
export ASK_FLOW_CLOUD_MODEL=gemini-3.5-flash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=global
python app/main.py
```

This uses Google Application Default Credentials on the local machine. No API keys or credentials are stored in the repo. If enhanced mode is not configured or the call fails, Ask Flow falls back to deterministic local answers.

## Public Test Data

For a quick local demo without downloading data, click **Load Demo Dataset** in the Upload panel. It creates a deterministic synthetic event-level CSV batch with control/treated labels and example panel annotations. The generated data is for workflow testing only and is not biological reference material.

Download public FCS files from:

- https://github.com/tlnagy/fcsexamples
- https://flowrepository.org/
- Optional workflow context: https://github.com/LennonLab/sigma-spore-phage-flow

Do not commit large public datasets into this repo. Keep local test files outside source control or in a temporary project cache.

## User Workflow

1. Click **Load Demo Dataset** for a synthetic local batch, or upload one or more `.fcs` files or event-level `.csv` files as fallback.
2. Optionally upload a sample manifest CSV with `sample_id,file_name,condition,replicate,control_type,notes`.
3. Optionally upload a panel setup CSV with a channel key (`channel`, `raw_name`, `pnn`, or `detector`) plus any of `display_label,marker,antibody,fluorochrome,role`.
4. Review the sample table, metadata inspector, channel inspector, and QC cards.
5. Explore FSC/SSC scatter plots and fluorescence histograms.
6. Apply raw, safe log10, or arcsinh display transforms.
7. Add user-defined rectangle or histogram range gates and review gate statistics.
8. Compare batches or control-vs-treated groups using exploratory medians and guarded fold-changes.
9. Save gates or project JSON locally, then export gate statistics, comparison CSVs, PDF reports, or PowerPoint reports from `exports/`.
10. Use Ask Flow for summaries and safe workbench actions, such as changing plot axes, histogram channel, plot mode, transform, max plotted events, or active sample.

## What It Does

- Multi-file FCS upload with friendly bad-file handling.
- CSV fallback with explicit limitations.
- Optional manifest support.
- Optional panel setup CSV support for marker, antibody, fluorochrome, and role labels.
- Metadata and FCS keyword inspection.
- Fuzzy channel role inference from metadata and channel names.
- FSC/SSC auto-selection without hard-coded instrument channel maps.
- Plotly WebGL scatter plots with display downsampling and dataset-aware axis auto-fit.
- Fluorescence histogram overlays.
- Raw, safe log10, arcsinh, and optional logicle display transforms.
- Metadata-driven compensation view toggle for FCS files with usable `$SPILL`/`$SPILLOVER` matrices, plus a local editable compensation matrix for review/override workflows.
- Interactive on-plot rectangle/polygon drawing, including raw/log10/arcsinh/logicle coordinate conversion, child-gate drawing from the selected parent, rectangle, polygon, histogram range, quadrant, ellipse, and bi-range gates, gate JSON save/load, parent-ready gate model, and statistics.
- Gate statistics include event counts, percent of total/parent, medians, means, percentiles, SD, %CV, robust CV, and geometric mean for fluorescence channels.
- Project JSON save/load for metadata, file references, gates, QC, transform settings, comparison settings, and report selections.
- Rule-based QC dashboard with review-needed language.
- Batch tables, event count chart, median fluorescence table, batch gate-statistics grid, and exploratory control-vs-treated comparison.
- High-dimensional review using UMAP with PCA fallback plus clustering for review-needed population exploration without automatic identity claims.
- AI-assisted autogating MVP: cluster fluorescence space with UMAP/PCA review, generate disabled review-needed gate candidates on the active plot, and optionally apply enhanced marker-aware cluster labels without sending raw event matrices.
- Local CSV, PDF, and PowerPoint report export with representative plot images when static export is available.
- Ask Flow assistant panel with deterministic local answers, state-aware analysis plans, safe UI actions, optional enhanced responses, and chat-triggered autogate review.

## Limitations

- Compensation editing is a lightweight matrix review tool. It is not a full single-stain/FMO compensation wizard or spectral unmixing workflow.
- High-dimensional clustering is exploratory and does not infer cell identities unless the user supplies marker meaning.
- Static report figures are summarized; richer Kaleido image embedding is a roadmap item.
- CSV summary tables cannot support full event-level cytometry analysis.
- QC checks are heuristic review aids, not pass/fail biological conclusions.

## Roadmap

- Robust FlowKit-backed GatingML import/export.
- Single-stain/FMO guided auto-compensation and spectral unmixing review.
- Richer marker-aware cluster annotation and editable high-dimensional population review.
- Kaleido figure embedding in PDF/PPTX.
- More Ask Flow action tools for report/export workflows, while keeping execution allowlisted.

## Known Issues

- Very large FCS files depend on local memory and FlowIO parse speed.
- Logicle support depends on installed FlowUtils/FlowKit behavior.
- Project JSON intentionally does not store raw event matrices; reload exported FCS/CSV files after restart for event-level analysis.

## Citation And Inspiration Links

- FlowIO: https://github.com/whitews/FlowIO
- FlowKit: https://github.com/whitews/FlowKit
- FlowUtils: https://github.com/whitews/FlowUtils
- FlowCal: https://github.com/taborlab/FlowCal
- Cytoflow: https://github.com/cytoflow/cytoflow
- Freecyto: https://github.com/nathan2wong/freecyto
- openCyto: https://github.com/RGLab/openCyto
- FlowSOM Python: https://github.com/saeyslab/FlowSOM_Python
- PeacoQC: https://github.com/saeyslab/PeacoQC
- GateNet: https://github.com/wwu-mmll/gatenet
- Example FCS files: https://github.com/tlnagy/fcsexamples
- FlowRepository: https://flowrepository.org/

## Disclaimer

This tool is for research and post-acquisition analysis support only. It does not control any cytometer and does not replace expert review.
