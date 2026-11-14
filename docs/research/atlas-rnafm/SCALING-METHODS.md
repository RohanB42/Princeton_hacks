# Atlas RNA-FM source-size and duration follow-up

Authorized November14,2026. This study independently tests whether increasing
source measurements from the historical1,000-label run to3%/5% of the eligible
source pool, and selecting training duration using internal validation, improves
chemistry-aware ASO efficacy prediction. It supplies evidence for possible future
reward heads; it does not train RL, evaluate generated molecules or model toxicity.
Historical results in RESULTS.md remain unchanged.

## Experimental units and label accounting

The endpoint is original measured `Inhibition_pct` under recorded dose/assay
conditions, in percentage points. The strict Atlas cohort and existing target,
patent, compound and base-equivalence exclusions are reused unchanged. The source
fraction denominator is95,638 eligible source-training records. Total source budgets
are2,869 and4,781, with nested uniform row samples for each source seed510–512.
About20% of each selected cohort is assigned to internal validation by patent
identifier, using a random group prefix closest to20% of rows. Validation membership can change between source budgets, so raw source-validation
scores across3%/5% are not a common-test learning curve. The source-size comparison
uses identical development-target test rows after matched target adaptation. Feature
fitting, label normalization and gradient updates use only the remaining rows. Validation
labels count against the source budget. The external14,614 source-validation rows
are unused in this follow-up.

Source seeds510/511/512 pair with target acquisition seeds610/611/612. Three
previously designated development target identifiers—F7, STAT3 and NLRP3—retain
original sequence-component pool/test partitions. Seven reserved target campaigns
remain outside model fitting, selection and scoring. Source names are not verified
canonical gene aliases, and patent identifiers are not verified patent families.
There are three development target identifiers, not nine independent target genes.

For each paired seed, sample200 acquired target labels uniformly without replacement.
For the duration-selected protocol, split these200 rows into fitting/validation by
pool-wide sequence components (same-length Hamming distance<=2 and exact one-base
shifts). This produces160–166 fitting and34–40 validation labels. Pool-wide grouping
retains connections mediated by unacquired rows and uses no efficacy labels.

## Fixed models and contrasts

Frozen RNA-FM and actual Q/V LoRA share the existing chemistry/context fusion head,
rank4/alpha8 where applicable, AdamW learning rate0.001, weight decay0, batch8 and
CPU single-thread execution. No learning-rate, architecture or chemistry sweep is
added. The frozen encoder uses a separate verified token cache; adapted encoders
never use frozen cached states. Original base weights are checked after each fit.

Every source neural fit runs at least3 and at most20 epochs. Validation RMSE must
improve by more than1e-6 to replace the selected checkpoint; ties retain the earlier
one. Stop after5 consecutive non-improving epochs once3 epochs have executed.
Selection considers all completed epochs, so the best checkpoint can be epoch1 or2.
Restore head, adapters, source-fitted context, label mean/scale and source IDs.
Retain epoch3, and epochs10/20 only if actually reached, plus the selected checkpoint.
Logs contain fixed-model end-of-epoch training/validation MSE and RMSE, normalized
MSE, separate evolving-minibatch loss, elapsed time and checkpoint decisions.

Three neural target protocols are reported separately:

1. **Source3 / target3 / all200:** source checkpoint after3 epochs; fixed3 target
   epochs on all200 acquired labels.
2. **Source selected / target3 / all200:** validation-selected source; the same
   fixed3 target epochs and all200 labels. The paired contrast with1 isolates source
   checkpoint duration under the same target training protocol.
3. **Source selected / target selected / inner fit:** validation-selected source;
   up to20 target epochs using group validation within the200-label budget. This
   differs from2 in both duration selection and gradient-row count; its contrast
   must not be described as the causal effect of extra target epochs alone.

No target all-data selected-epoch refit is hidden in the primary arm. Every target
fit resets to the specified source checkpoint, with a fresh optimizer. The source
context scaler remains frozen during target adaptation, matching the historical
implementation.

Ridge and XGBoost source controls receive exactly the same inner fit/validation
rows. Select among the historical three hyperparameter candidates using the explicit
validation partition; retain the model fitted on inner rows only. Transfer uses a
mean residual offset fitted on either all200 or matching inner target rows. The
inner-offset control deliberately excludes target validation labels from its
calibration; those rows remain included in the declared200-label allocation.
Target-only Ridge/XGBoost controls fit each partition once: historical grouped CV
for all200, or explicit holdout selection for inner fits. Historical source data
are accounted separately, so target-only models are additional comparators.

Total planned records:24 source models,180 source-conditioned target fits/offsets,
and36 target-only controls;216 target test-scoring records. Counts distinguish
optimizer-trained models from cheap offset calibrations. Four-hour study wall cap
includes the retained source profile; partial completion is reported explicitly.

## Evaluation and limitations

All target predictions are written before any test metrics are calculated. Model
code receives only fitting and permitted internal validation labels. The full
runner reads label-free records separately and filters Parquet endpoint reads to
caller-authorized IDs. The initial profile used an earlier whole-table read before
restricting its fitting Series; no reserved labels entered fitting, stopping or
metrics. Invocation/source hashes preserve this implementation detail.

Primary descriptive metric is target RMSE at200 acquired labels; Pearson, Spearman
and MAE are retained. Compare source budgets, paired source-duration contrasts and
matched classical controls. Average seeds within target and targets equally. Seed
standard deviations describe repeatability and are not confidence intervals for
new genes. No threshold or label-savings claim is made from two source sizes and
one new-target budget. Test results remain development diagnostics.

Internal source validation is patent-held-out, not a strict molecular-identity
holdout: three of six source partitions have one repeated normalized compound
identity across fit/validation, and natural-base intersections range0–4. Preserve
this audit and the frozen partitions; do not silently change data after outcomes.
The source-to-target compound/base exclusions remain in force. Sequence-component
splits do not establish all-homology isolation. Repeated patent-derived assays also
retain source-selection and experimental-context biases.

## Reproduction and continuation

Worktree: `/private/tmp/oligoal-atlas-lora-scaling-20261114`.
Optional read-only runtime:
`/private/tmp/oligoal-atlas-rnafm-20261114/.venv-atlas/bin/python`.
See ENVIRONMENT.md for pinned package versions; no lockfile changed. The runner
accepts a local output directory, reuses completed receipts, and rejects changed
frozen configs. Use a new output path for an independent rerun. Its verified local
checkpoint path is declared in `scripts/run_atlas_scaling.py`; weights stay ignored.

```sh
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
atlas_python=/private/tmp/oligoal-atlas-rnafm-20261114/.venv-atlas/bin/python
"$atlas_python" scripts/run_atlas_scaling.py --phase prepare
"$atlas_python" scripts/run_atlas_scaling.py --phase profile
"$atlas_python" scripts/run_atlas_scaling.py --phase run
MPLCONFIGDIR=artifacts/atlas-rnafm/scaling-v1/mpl "$atlas_python" scripts/report_atlas_scaling.py
"$atlas_python" scripts/audit_atlas_scaling.py
```

Live status and process IDs: SCALING-STATUS.md. Frozen config:
`configs/atlas/scaling-v1.json`. Generated artifacts:
`artifacts/atlas-rnafm/scaling-v1/`; all manifests, histories, checkpoint weights,
predictions and generated figures remain ignored by Git. The user subsequently authorized publication of the intermediate work on
`codex/atlas-lora-scaling`; the integrator pushes this branch without merging into
main or interrupting training. See SCALING-INTERMEDIATE-2026-11-14.md.
