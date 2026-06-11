# Sample Data

Large cytometry datasets are intentionally not bundled.

Recommended public demo sources:

- https://github.com/tlnagy/fcsexamples
- https://flowrepository.org/
- NovoExpress-exported workflow examples for context: https://github.com/LennonLab/sigma-spore-phage-flow

Download one or more `.fcs` files locally, then upload them through Ask Flow Workbench. The app also accepts simple event-level `.csv` tables for fallback testing.

## Demo Helpers

This folder includes two tiny CSV helpers that are safe to keep in source control:

- `demo_manifest.csv`: sample labels for condition, replicate, control type, and notes.
- `demo_panel_setup.csv`: channel/marker labels for a common public demo FCS naming style.

Suggested local demo:

1. Download a small public FCS file from `https://github.com/tlnagy/fcsexamples`.
2. Put it in this folder or upload it directly through the app.
3. If using the local public file named `Beckman Coulter - Cyan.fcs`, upload `demo_manifest.csv` as the optional manifest.
4. Upload `demo_panel_setup.csv` as the optional panel setup.
5. Open Explore, Gates, QC, Compare, Reports, and Ask Flow.

If your FCS filename differs, edit `demo_manifest.csv` so `file_name` exactly matches the uploaded file. If your channel names differ, edit `demo_panel_setup.csv` so `channel` matches the raw FCS channel name shown in the Channel Inspector.

These files are examples only; marker and antibody names are placeholders until the user supplies the real panel meaning.
