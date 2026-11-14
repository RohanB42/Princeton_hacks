# Full-data acquisition comparison, 2026-11-14

The user requested full experiments after the preliminary smoke checks. This is a
predefined diagnostic comparison using the current HELM-hash Random Forest. It is
not a reproduction of the published nucleobase benchmark or therapeutic validation.

## Fixed experimental settings

- All 12 complete released datasets; no sampled-row cap. Preserve source endpoints
  and evaluate each dataset separately.
- Seeds 0–4, paired random/uncertainty acquisition, identical eligible/test IDs,
  initial labels, predictor seed/hyperparameters and cumulative label budgets.
- Initial 50 labels, batches of 50, maximum 500 or the eligible pool size. Tiny
  datasets therefore reach the complete pool; terminal equality is expected and
  learning-curve area is the primary acquisition comparison.
- RF: 100 trees, depth at most 20, 512 fixed HELM character-hash features (1–3grams),
  four tree-training/prediction threads, prediction batches of 8,192. No vocabulary,
  normalization statistics or label transformations are fitted on test rows.
- Primary comparison: local exact-HELM group holdout, 20% of groups for evaluation.
  This prevents exact duplicate leakage, not sequence-family or gene leakage.
- Secondary comparison: target-group holdout, same settings. Missing targets,
  single-group data and sequence overlap fail explicitly; unsupported datasets
  remain in the ledger rather than being silently dropped or given a fallback split.
- Primary statistic: paired normalized trapezoidal Pearson learning-curve area,
  uncertainty minus random, over each seed's declared available budget interval.
  Report every seed, mean and sample SD. SD is not a confidence interval. Also
  report Pearson, RMSE and MAE per checkpoint and a separate full-pool reference.
- Secondary label-efficiency description, fixed before the run: first checkpoint
  reaching full-reference Pearson minus 0.03, conditional on a positive reference;
  record whether this used at most half the eligible training labels. This is a
  reporting criterion only, not a stopping rule or policy signal. The reference's
  absolute quality must remain visible; matching a weak reference is not a strong
  discovery result.
- Constant truth/predictions give null Pearson with a reason. Undefined points
  make that seed's AULC undefined; no replacement with zero or best-seed selection.
  Report counts of defined paired seeds alongside every aggregate.

## Fairness correction and execution audit

The initial full-data attempt exposed an acquisition-order confound: with the same
RF seed, bootstrap samples depend on input row order. Merely acquiring the same
complete pool could therefore produce different terminal models. The corrected
runner sorts fitting records by stable sample ID for every checkpoint and reference.
A regression test requires full-pool terminal equality across both policies and
the reference. Initial/acquired-ID ledgers still preserve actual acquisition order.

`artifacts/full-sequence-group-20261114/` is explicitly marked
`superseded_training_order_audit` and excluded. Corrected runs use
`artifacts/full-sequence-group-canonical-20261114/` and
`artifacts/full-target-canonical-20261114/`. Earlier smoke checks predate this
correction and must not be substituted for the corrected experiments.

Stateless feature matrices may be cached: each row's fixed transform is unchanged
and the cache holds no labels. Full-pool predictions are reused across policies
only for identical dataset/source, train/test membership and model configuration,
after a separate reference fit. They are never passed to acquisition policies.
Regression tests verify cache equivalence and reference isolation. Runtime is not
a fair policy-speed comparison because the common reference cost is shared.

Every campaign is saved immediately. Suite state is written atomically and remains
running until all selected datasets have a terminal status. Artifacts include model
settings, effective budgets, source-file hashes, current source-code SHA256,
package versions and the dirty Git revision status.

Sherwood's five independent seed campaigns may execute in separate worker processes
with unchanged settings/source. Worker configs and results are retained under
`artifacts/full-sherwood-workers-20261114/`. `scripts/merge_seed_workers.py` validates
all source hashes and scientific settings before joining them with the main suite;
it never overwrites an existing run with different scientific contents.

## Reproduction and reporting

```sh
poetry sync --with science,reporting
poetry run python -m oligo_engine.collection \
  --config configs/all-datasets-full.toml --output artifacts/full-new
poetry run python -m oligo_engine.collection \
  --config configs/all-datasets-target-full.toml --output artifacts/target-new
poetry run python scripts/analyze_full_experiments.py \
  --suite artifacts/full-new --output artifacts/full-new-report
poetry run python scripts/analyze_full_experiments.py \
  --suite artifacts/target-new --output artifacts/target-new-report
```

Use fresh output paths. The target command exits nonzero when some datasets are
unsupported; inspect its ledger to distinguish unsupported data from actual failures.
The reporter accepts explicit unsupported cases but rejects failed, incomplete or
superseded campaigns. It verifies paired IDs, counts, model settings, canonical
fitting, source consistency and complete-pool equality before computing statistics.
Reports include a machine-readable summary, CSV, learning-curve PNG/SVG and paired
AULC plot. Undefined seed counts are shown instead of fabricated precision.

## Completed results

All **180** diagnostic acquisition campaigns completed: 120 on the full 12-dataset
exact-sequence-group matrix, plus 60 on the six supported target-held-out datasets.
Full-pool references are trained separately for each dataset/split/seed and reused
only between matched policies. All reported runs retain the original sparse backend.
A training-only dense-matrix timing check was considered during the long Sherwood
fits, but the original jobs finished before an amendment was needed; no dense
results are included. The exact experiment source is archived locally and matches
current `src/oligo_engine/` byte for byte.

Sequence-group outcomes below are mean final Pearson correlations and paired
normalized learning-curve-area differences. Positive area differences favor
uncertainty. Dispersion is **sample SD**, not a confidence interval.

| Dataset | Final random r | Final uncertainty r | Area difference, uncertainty − random |
| --- | ---: | ---: | ---: |
| Huesken | 0.2457 | 0.2695 | -0.0252 ± 0.0530 |
| TLR7 | 0.4823 | 0.4823 | +0.0289 ± 0.0511 |
| TLR8 | 0.3974 | 0.3974 | -0.0291 ± 0.0204 |
| Ichihara | 0.1113 | 0.1113 | +0.0300 ± 0.0433 |
| Shmushkovich | 0.3895 | 0.3895 | -0.0101 ± 0.0540 |
| Cytotox LNA | 0.7494 | 0.7441 | -0.0137 ± 0.0276 |
| siRNAmod | 0.4663 | 0.5051 | +0.0590 ± 0.0508 |
| Neurotox LNA | 0.5881 | 0.6156 | +0.0073 ± 0.0489 |
| Neurotox MOE | 0.6740 | 0.6752 | -0.0074 ± 0.0247 |
| OpenASO | 0.2460 | 0.2666 | +0.0104 ± 0.0254 |
| ASOptimizer | 0.3485 | 0.3232 | -0.0225 ± 0.0347 |
| Sherwood | 0.2101 | 0.1435 | -0.0271 ± 0.0880 |

Uncertainty has higher mean area in 5/12 datasets and lower mean area in 7/12.
This is a descriptive count across separate tasks, not a pooled score or a
significance test. In Huesken, later improvement under uncertainty does not
compensate for lower performance at earlier budgets. No consistent general
label-efficiency advantage is established for this diagnostic representation/policy.

On Huesken target holdout, final r is 0.2128 random versus 0.2470 uncertainty;
paired area difference is +0.0082 ± 0.0448 SD. The Neurotox LNA target area uses
four valid paired folds: the fifth has only 32 eligible training rows, all consumed
by initialization, so its Pearson is valid but there is no learning-curve interval.
Its final score is retained, not imputed or discarded.

Local outputs (generated and ignored by Git):

- `artifacts/full-sequence-group-results-20261114/`: validated report JSON, summary
  CSV, learning-curve PNG/SVG and paired-area plot for all 12 datasets.
- `artifacts/full-target-results-20261114/`: the same artifacts with six explicit
  unsupported entries and reason strings.
- `artifacts/full-source-sparse-20261114/`: exact source/config/lock snapshot.

Final verification: 59 tests pass, including label isolation, cache equivalence,
canonical complete-pool equality, paired-report auditing, undefined-area handling
and safe seed-worker joining. Historical benchmark reproduction remains unresolved;
these results must not be compared directly with its leaderboard as if they used
the same representation and split.
