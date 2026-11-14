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
- Gate 1 study finds that upstream prepare_model filters RF max_depth out, whereas
  the earlier local rerun applied it. Preserve the earlier result as a non-equivalent
  effective-model attempt. A controlled five-seed correction gives r=0.560466;
  native helpers give r=0.559769, exactly repeated across another five fits. Both
  remain outside the unchanged 0.03 tolerance against r=0.591037. Historical split
  manifests, effective settings and environment remain unresolved. See
  gate1-reproducibility-study.md; no acquisition settings or gate were changed.
  Final local checks now pass 77 tests, lint, formatting and whitespace validation.
- The user subsequently confirms Gate 1 scope as published best models on all
  efficacy datasets. Freeze all seven winning nucleobase configurations from the
  released CSV before local execution; no local model selection or row caps.
  All 35 fits complete with native helpers and explicitly declared neural runtime
  settings. Huesken, Shmushkovich, siRNAmod and Sherwood meet the fixed 0.03
  tolerance; Ichihara, OpenASO and ASOptimizer do not. The headline Huesken CNN
  now reaches r=0.609600 vs 0.630914 reference. Full numerical reproduction remains
  unresolved. Exact source/config and per-run provenance are preserved locally.
  Final checks pass 88 tests, lint, formatting, whitespace and source/hash audits.
- The user explicitly requests a subagent to implement and execute the next Huesken
  learning-curve experiment after assessing its fit with the broader spec. Frozen
  protocol/config: huesken-learning-protocol.md / configs/huesken-learning.toml.
  Compare random with label-blind native k-mer diversity using the validated CNN,
  official nucleobase holdouts, five paired seeds and 50–500 labels. Refit study
  full-pool references under the existing canonical fit order. Keep diagnostic
  status and global Gate 1 caveats; no premature acquisition-benefit claim.

- User authorization to proceed with active-learning development implements the
  separate four-policy Huesken GP study documented in active-learning-development.md.
  Initial50-only internal kernel selection counts all labels; frozen primary contrast
  is hybrid minus random over50–1000 labels. Development seeds200–204 precede a
  separately frozen evaluation declaration. Diagnostic purpose remains explicit;
  the earlier CNN pilot and historical attempts are preserved. The incoming
  gate1-resolution.md closes only its own two-baseline reassessment, not the user's
  expanded seven-dataset published-best-model reproduction requirement.
