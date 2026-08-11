# Trace and Visualization Protocol

Every packet task writes:

- `REPORT.md` with a direct YES/NO all-cell verdict and full prediction;
- `learning_trace.json` with explicit IHL action/evidence/revision records;
- `corpus_callosum.svg` showing actual test input, compatibility core, selected generic operator, and committed output;
- `receipt.json` with source pin, boundary checks, and post-answer V&V.

The diagram depicts factor-level support rather than inventing false pixel-to-pixel causal fibers. It must remain readable after raster rendering; P0001 uses a native SVG so reviewers can inspect it directly on GitHub and regenerate PNGs for visual QA.

`P0004` uses the same format for a real recorded ARC3 transition: the before/after public frames appear beside the shared compatibility core, explicit hypothesis revisions, and observed external action. Red cell outlines mark actual frame differences, not inferred or simulated effects. Its report declares a transition-contract result and explicitly states that it is not an ARC3 level-solved claim.

For an ARC12 shape-changing residual theory, the diagram names the generic family (for example, `dihedral macro-tile`) and labels the path `UNKNOWN RESIDUAL → REVISE/COMPOSE → COMMIT`. This distinguishes a missing-shape residual from an observed contradiction and lets the report trace show the full ordered rule composition.
