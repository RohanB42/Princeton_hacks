# Supported ASO execution: authorized sequence

> Historical record: the target-window RL scaffold and its experiment runners
> were removed on November 14 at the user's request. Commands for that scaffold
> require the pre-removal checkout (`f26922f`); they are not current entry points.
> Shared prediction/scoring utilities remain. Local retired runs were moved outside
> the checkout; old artifact links below are historical locations.

November 14, 2026, 18:45 EST / 23:45 UTC. The user authorized saving/publishing the
assessment and then executing the following sequence, rather than merely planning:

1. Select an evidence-supported chemistry/assay profile using training metadata.
2. Package a frozen classical efficacy predictor and verify inference parity.
3. Evaluate candidate ranking against held-out exact measured assays.
4. Compare optimizers with equivalent proposal access and explicit cost accounting.
5. Expand RL only if the previous stages establish a useful, interpretable task.

The preceding assessment is [documented here](../aso-environment-assessment-2026-11-14.md).
It found valid engineering behavior but an unsupported exact 19-mer Atlas template,
an action-access confound in the tight-budget fixture comparison, and encouraging
post-hoc ranking of recorded assays. Those results do not validate generated ASOs.

Execution invariants: choose chemistry and assay from metadata, never final efficacy;
separate internal validation from held-out assessment; use compatible measured
efficacy only; missing safety endpoints remain unknown. Predictor normalization,
checkpoint selection and PPO rewards must not read held-out measured outcomes.
Preserve earlier experiments and the seven reserved target campaigns. Source-only
versus target-adapted access must be explicit. A held-out measured panel is a
retrospective ranking task, not a wet-lab or novel-molecule validation claim.

The real-stage protocol will record exact cohort/profile, stable groups, label
budgets, model controls, and independent assessment before outcome inspection.
If evidence blocks a later stage, record that reason and complete useful preceding
infrastructure; do not force a positive conclusion or enlarge PPO runs blindly.

No source datasets, generated artifacts, model weights or PDFs belong in these
commits. New code and aggregate reports may be published within the user's request.
