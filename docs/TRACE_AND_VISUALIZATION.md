# Trace and Visualization Protocol

Every packet task writes:

- `REPORT.md` with a direct YES/NO all-cell verdict and full prediction;
- `learning_trace.json` with explicit IHL action/evidence/revision records;
- `corpus_callosum.svg` showing actual test input, compatibility core, selected generic operator, and committed output;
- `receipt.json` with source pin, boundary checks, and post-answer V&V.

The diagram depicts factor-level support rather than inventing false pixel-to-pixel causal fibers. It must remain readable after raster rendering; P0001 uses a native SVG so reviewers can inspect it directly on GitHub and regenerate PNGs for visual QA.
