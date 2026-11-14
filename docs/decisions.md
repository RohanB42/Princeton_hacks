# Decisions and status

- Existing `main` repository and GitHub remote are preserved. Working project and import names are `oligo-design-engine` and `oligo_engine`.
- Python 3.11 and Poetry 2.1.4 remain selected. Current core checks run locally on
  Python 3.11.13, Ruff 0.12.12 and pytest 8.4.2. Existing project lock is preserved;
  no scientific dependency was added to core. CI targets Python 3.11, not yet run remotely.
- Source PDFs are context, not files to publish. Older v2 target-split headline text is superseded by v5 nucleobase headline protocol.
- No license or author attribution is chosen. Project code license and rights to upstream datasets/weights need owner review.
- November 13 revised handoff supersedes incompatible v5 multi-task, novelty and
  commercial claims. Default is independent siRNA efficacy replay; negative results
  count. Biological design, ASO safety and RL remain separate workstreams.
- Typed contracts and synthetic random replay now execute, with label-isolation
  tests and source auditing. Synthetic output is plumbing evidence only.
- Upstream 97f5b9f58d9e445a8ecb0218037af7465c3708c0 is verified; Huesken is the loader
  key and Analysis.ipynb maps benchmark alias siRNA1 to it. TLR descriptions conflict.
- The published linear configuration reran on five seeds: mean r=0.584832 versus
  0.615865 reference, gap -0.031032, outside frozen 0.03 tolerance. Gate 1 remains
  open. Ill-conditioning and missing historical seeds warrant investigation; the
  cause is not established. See upstream-verification.md.
- A training-diagnostics-motivated published RF cross-check also missed tolerance:
  mean 0.559096 vs reference 0.591037, difference -0.031941. Do not choose further
  models/seeds just to pass. Historical split/environment comparability remains open.
- Integrator owns shared contracts/configs/metadata; independent ownership and
  worktrees are planned, not assigned. See IMPLEMENTATION_TASKS.md.
- November 14 user request overrides the prior data exclusion: all 12 released
  datasets are vendored byte-for-byte with metadata/license/manifest. Extra data
  remain ignored. Source-specific rights and project licensing are not redefined.
- That request also authorizes general measured engineering diagnostics while Gate 1
  is open. Research mode stays gated. The catalog, local group splits, adaptive
  budgets, HELM-hash RF and random/uncertainty replay work across all 12 datasets;
  128-row-per-dataset runs are plumbing evidence, not generalization claims.
- The optional science group pins numpy/scipy/sklearn, supports Python 3.11/3.12,
  and is exercised in the local cross-dataset tests and configured CI job. No
  scientific endpoint direction, clinical safety label or calibration is assumed.
- Full-data comparisons are complete: 120 campaigns on exact-sequence-group holdout,
  60 on six supported target-ID holdouts, five seeds, 50 initial / 50 batch / 500
  maximum labels (pool-adapted). Purpose remains diagnostic; the original sparse
  representation is retained throughout.
- Canonical sample-ID fitting removes an RF bootstrap-order confound; regression
  tests require terminal complete-pool equality. The earlier attempt is explicitly
  superseded. Feature and full-reference caches are label-isolated.
- Primary paired normalized area improves under uncertainty in 5/12 sequence-group
  tasks and declines in 7/12. No consistent advantage is established. Values and
  counts are in full-experiment-protocol.md and local generated reports. 59 tests pass.
- The subsequent November 14 scope decision focuses the main study on efficacy:
  Huesken first, independent siRNA replications, then separate ASO efficacy studies.
  Retain all data and existing diagnostic results; safety and immunomodulation are
  auxiliary. Baseline reproduction is the immediate next task. Concentration-aware
  experimental design is a proposed extension, not implemented functionality.
