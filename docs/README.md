# Ask Flow Workbench Notes

Ask Flow Workbench is a clean-room local analysis app for exported event files. It does not control instruments, does not read proprietary `.ncf` files, and does not interact with NovoExpress, firmware, drivers, lasers, fluidics, maintenance, cleaning, shutdown, or autosampler behavior.

Implementation references:

- FlowIO: lightweight FCS reading and metadata extraction.
- FlowKit: higher-level flow cytometry concepts, GatingML compatibility, transforms, compensation, and future import/export directions.
- FlowUtils: compensation and transformation utilities.
- FlowCal, Cytoflow, Freecyto, openCyto, FlowSOM, PeacoQC, and GateNet: design and algorithm inspiration only.

All gate suggestions and QC checks are review aids. They are not biological truth and should be reviewed by an experienced cytometrist.

Compensation support is intentionally narrow: Ask Flow Workbench parses FCS `$SPILL`/`$SPILLOVER` metadata, maps matrix labels to event channels when reliable, and creates a separate compensated event view. Raw exported events are not overwritten. If metadata is absent, malformed, or cannot be mapped cleanly, the app keeps raw values visible and raises a review flag instead of guessing.
