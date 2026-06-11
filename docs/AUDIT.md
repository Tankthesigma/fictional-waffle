# Ask Flow Workbench Audit Notes

Last audit pass: 2026-06-11

## Public Feature Check

Public Agilent/NovoExpress materials describe a combined acquisition and analysis package with plots, gates, compensation, batch statistics, reports, export, and additional instrument/worklist functions. Ask Flow Workbench intentionally implements only the external post-acquisition analysis side.

Sources checked:

- Agilent NovoExpress product page: https://www.agilent.com/en/product/research-flow-cytometry/flow-cytometry-software/novocyte-novoexpress-software-1320805
- Agilent flow cytometry software overview: https://www.agilent.com/en/product/research-flow-cytometry/flow-cytometry-software
- Public NovoExpress Software Guide mirror: https://www.scripps.edu/_files/pdfs/science-medicine/cores-and-services/flow-cytometry-ca/NovoExpress-Software-Guide.pdf

## Covered In This App

- Exported `.fcs` and event-level `.csv` upload.
- Metadata and channel inspection.
- Fuzzy channel role inference without hard-coded NovoCyte channel maps.
- Dot, density, contour, and histogram plotting.
- Raw, safe log10, arcsinh, and optional logicle display transforms.
- Metadata-driven spillover awareness and compensated event view when FCS metadata is usable.
- Rectangle gates, histogram range gates, gate JSON save/load, gate overlays, and descriptive gate statistics.
- Rule-based QC flags with review-needed language.
- Batch tables, fluorescence medians, and exploratory control-vs-treated comparison.
- Gate statistics CSV export, comparison CSV export, and PDF/PowerPoint export with representative plot images when static export is available.
- Deterministic local Ask Flow summaries.

## Explicitly Out Of Scope

- Instrument connection, acquisition, maintenance, fluidics, cleaning, shutdown, lasers, drivers, firmware, licensing, USB communication, autosampler control, or XP compatibility.
- NovoExpress calls, `.ncf` parsing, proprietary workflow replication, protected assets, vendor logos, screenshots, or branding.
- Full compensation wizard, spectral unmixing, compliance audit trail, cell-cycle fitting, proliferation fitting, LIS export, plate heat maps, or one-click biological autogating.

## Validation Commands

```bash
python app/main.py
python -m pytest tests
ruff check app tests
python -m compileall -q app tests
```

Current audit coverage includes upload error paths, channel inference, transforms, downsampling, compensation parsing/application, QC heuristics, rectangle and histogram range gate membership, gate serialization, table CSV export, project save/load, report export, Dash callback smoke paths, project-rooted runtime paths, and graph stress tests for WebGL dot plots, density plots, contour plots, gate overlays, and histogram overlays.

## Remaining Gaps To Treat Honestly

- Polygon gate drawing exists in the core model but is not exposed as an interactive Dash drawing workflow yet.
- Compensation is metadata-driven only; no single-stain compensation wizard or matrix editor.
- Report plot export depends on Kaleido availability.
- QC is heuristic and descriptive, not a biological pass/fail system.
- Ask Flow is deterministic and local; it does not infer cell identity or diagnosis.
