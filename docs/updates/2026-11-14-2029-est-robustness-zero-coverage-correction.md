# Predictor robustness: model integration and zero-coverage correction

Recorded November 14, 2026, 20:29 EST / November 15, 01:29 UTC.
Inspected main at `d9836e9` after pulling the predictor-robustness implementation.
This records the subsequent discussion, code inspection and outcome-free metadata
audit. It changes no models, admission rules, splits or experimental results.

## Intended experiment

The scientific goal is to determine whether uncertainty, distance from training
data and disagreement between comparable predictors identify prediction errors,
and whether using those signals improves candidate selection under matched
budgets. These are two separate questions: a warning can correlate with error
without improving a shortlist, and rejecting nearly everything is not useful
without an explicit coverage requirement.

A convincing measured result would compare shortlisted experimental efficacy
against ordinary predicted-score ranking, using the same query budget and
shortlist size. The evaluation outcomes must be unavailable until predictions,
warning thresholds and selected IDs are fixed. Such a result could motivate a
safeguard in the RL reward system; it would not validate novel molecules or safety.

## What was actually connected

The measured CLI did **not** evaluate our existing frozen GP, LoRA or Atlas
efficacy checkpoints. `AuditPipeline._models()` fits two new audit models on the
same 1,920 permitted ASOptimizer fitting labels:

- Primary Random Forest: 64 trees, maximum depth 12, seed 1729.
- Secondary Ridge: alpha 10, LSQR solver, tolerance 1e-8.
- Both use position-specific base, sugar and linkage features with explicit
  absence indicators and terminal chemistry. Cell line and concentration are
  **not predictive inputs**.
- RF tree-to-tree standard deviation is labelled uncalibrated. RF/Ridge
  disagreement is a diagnostic, not independent biological evidence.

A programmatic `portable_adapter()` bridge to the existing supported 20-mer Atlas
Ridge bundle exists, including training-membership and endpoint/context checks,
but the measured CLI run did not invoke it. Availability of a bridge is not
equivalent to executing an experiment with the intended checkpoint.

Sources: [model adapters](../../src/oligo_engine/robustness/adapters.py),
[pipeline](../../src/oligo_engine/robustness/pipeline.py), and
[measured configuration](../../configs/robustness/asoptimizer-v1.json).

## Why every final record was rejected

The wrapper records exact fitting-supported `(cell_line, concentration)` tuples.
`FrozenAuditModel.predict()` emits `CONTEXT_UNSUPPORTED` with no predicted mean
when the evaluation tuple is absent. Rejected rows never reach the underlying
estimator's `predict()` call. The rule compares recorded metadata; it is not a
learned uncertainty threshold or an observed prediction-error result.

The frozen target split assigns HBV/SOD1 to fitting, MALAT1 to development, KLKB1
to calibration and DGAT2 to final evaluation. The metadata-only inspection
confirmed these final DGAT2 contexts:

| Cell line | Recorded concentration value | Final records | Same tuple in fitting? |
|---|---:|---:|---|
| HepG2 | 0.12 | 674 | No |
| HepG2 | 2.5 | 921 | No |
| HepG2 | 10.0 | 886 | No |
| HepG2 | 20.0 | 55 | No |
| **Total** | | **2,536** | **0 admitted** |

These are source concentration values; this audit did not establish their units
and does not relabel them as nM or any other unit. Training does include HepG2,
and includes concentration 0.12 in A431, but neither fact supplies the missing
exact HepG2/concentration combinations. The observed mismatch is in the actual
listed values, not merely an assumed formatting problem.

Thus 0/2,536 represents **four unsupported context combinations**, not 2,536
independent prediction failures. In this dataset, holding out a target also
withholds its assay contexts. Target and assay shifts are entangled. The
development and calibration partitions were likewise entirely rejected under
this rule.

## Correct interpretation and correction to earlier summaries

This is a fundamental incompatibility between the chosen experimental split and
the imposed admission rule. The pipeline should have stopped during metadata
preflight with **no evaluable final cohort**, before presenting downstream
execution as a substantive measured robustness experiment.

The exact-context restriction is a conservative wrapper decision, not evidence
that the fitted models are incapable of predicting other concentrations. However,
simply deleting it would not demonstrate valid context transfer: these models do
not encode dose or cell line, so their treatment of changed assay conditions would
still need explicit evaluation and justification.

The original reported outcomes remain:

- A constructed synthetic failure fixture showed a +28.08 synthetic-unit mean
  shortlist improvement across five paired query seeds. This tests the machinery
  on a known artificial failure; it is not biological evidence.
- The ASOptimizer diagnostic had zero admitted final predictions. Accuracy,
  error-warning associations and measured shortlist benefits were undefined.
  It established neither a successful biological safeguard nor poor numerical
  predictor accuracy.
- The implementation handoff reports 212 core tests and three optional science
  tests passing. Those suites were not rerun during this explanatory review;
  the new verification here was code inspection and metadata-only loading.

Earlier explanations should have made the fresh-model versus existing-checkpoint
distinction explicit and described the measured run as a preflight failure. The
intended robustness test of our existing predictive models has not been completed.
This does not negate the separate supported-profile Atlas ranking results or the
earlier PPO studies, which used different models and protocols.

## Corrective evaluation plan — not implemented by this update

1. **Identify the intended frozen models.** Record checkpoint hashes, exact
   training IDs, endpoint direction/units, chemistry and supported context. Verify
   direct-inference parity and exclude evaluation overlap. An all-label model
   cannot be declared held out by creating a split after it was trained.
2. **Perform an outcome-free eligibility preflight.** Audit source units and
   context representations, duplicate compounds and split groups. Report expected
   admitted counts for fitting, development, calibration and final evaluation.
   Predeclare sufficient coverage and group counts; stop before fitting or reading
   final labels if the benchmark cannot answer its question.
3. **Separate two scientific tasks.** Use compatible assay contexts for the primary
   robustness benchmark while preserving compound/sequence separation. If a valid
   target-held-out comparison is impossible under that scope, explicitly choose
   and name another split/task before outcomes. Separately declare an assay-transfer
   stress test where extrapolation is permitted, flagged and measured. Do not
   pool those conclusions or imply that context-aware modeling is already solved.
4. **Freeze the new protocol.** Specify cohorts, models, diagnostics, thresholds,
   tuning/calibration partitions, metrics, query budgets and shortlist cardinality.
   Treat previously examined outcomes as development evidence; do not reuse them
   as untouched confirmation or choose alternate seeds until a favorable run appears.
5. **Test warnings and decisions separately.** Measure whether warnings predict
   error, then compare guarded and ordinary ranking on held-out measured outcomes.
   Report error alongside retained coverage and match shortlist sizes and costs.
   Only then assess whether a supported safeguard improves RL optimization.

Do not silently loosen the old gate, overwrite the zero-coverage run, or describe
missing endpoints as zero risk. This file records the diagnosis and proposed next
steps; it does not authorize or claim execution of a replacement study.

Related context: [implementation and original results](../predictor-robustness-implementation.md),
[design specification](../predictor-robustness-design-spec.md), and
[separate supported-profile study](../supported-aso-results-2026-11-14.md).
