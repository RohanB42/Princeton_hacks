# RF anchors re-checked against the configuration upstream actually ran

**Correction study, 2026-11-14.** Prompted by the argument-filter finding recorded in
`gate1-reproducibility-study.md`. It changes how the published RF table should be
read; it does not change this project's endpoint conclusions.

## The finding

`benchmarks/train_model.py` builds a model with

```python
valid_args = inspect.signature(eval(config["model"])).parameters.keys()
model_args = {k: v for k, v in model_args.items() if k in valid_args}
```

`RandomForestModel`'s signature is `(task, n_estimators, **model_kwargs)`, so
`parameters.keys()` is `('task', 'n_estimators', 'model_kwargs')` and **`max_depth`
is filtered out**. Every published RF row labelled `max_depth: 10`, `20` or `30`
trained with scikit-learn's default of unlimited depth. The same applies to
`LinearModel` (`task, type, **model_kwargs`) and `GaussianProcessModel`
(`task, **model_kwargs`): any argument not named in the signature was dropped.

Our endpoint studies passed `max_depth=20` directly to `RandomForestModel`, where
`**model_kwargs` does forward it to the forest. So our anchors were **not** the
configuration they were compared against.

## Two consequences for reading the published table

1. **Nine RF rows per dataset are three models.** Only `n_estimators`
   (100/500/1000) actually varied; each value appears three times under different
   nominal depths. On `acute_neurotox_moe_cleaned` with one-hot base and 500 trees,
   the same model scored 0.3222, 0.5279 and 0.5783 across those three labels — a
   **0.256 spread with no configuration difference at all**, purely five-fold noise.
   On `immune_modulation_TLR7` the same comparison spans 0.1289.
2. **"Best published configuration" is partly a noise artifact.** Selecting the
   maximum over 372 rows, when groups of rows are the same model re-drawn, selects
   for lucky folds. Quote published bests as context, never as targets.

## Re-run: both depths, same seeds, same splits

`scripts/rf_anchor_recheck.py`.

| Dataset | Ours (depth 20) | Upstream config (unlimited) | Depth effect | Published | Gap vs upstream config | z |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MOE_Neurotox_1 (chem) | 0.5462 +- 0.1758 | 0.5453 +- 0.1779 | -0.0008 | 0.5394 | +0.0059 | +0.09 |
| Alharbi_2020_1 (base) | 0.6605 +- 0.0940 | 0.6605 +- 0.0940 | 0.0000 | 0.6590 | +0.0015 | +0.05 |
| Alharbi_2020_2 (base) | 0.5977 +- 0.0974 | 0.5977 +- 0.0974 | 0.0000 | 0.5896 | +0.0081 | +0.21 |
| Hwang_2024_1 (full, chem) | 0.4326 +- 0.0594 | 0.4314 +- 0.0594 | -0.0012 | 0.4094 | +0.0220 | +0.63 |

**The mismatch was real and immaterial.** At these row counts the trees rarely reach
depth 20, so capping there is almost the same model as not capping: the two TLR
results are identical to four decimals, and the largest effect anywhere is 0.0012.
Every anchor still reproduces under the configuration upstream actually ran, with
gaps of +0.0015 to +0.0220 and every z below 1.

## What each study should now say

`neurotox-moe-predictor.md`, `tlr-immunomodulation-predictors.md` and
`aso-efficacy-predictor.md` describe their anchor as "RF, depth 20, 100 trees". The
numbers stand; the label should read "100 trees, depth effectively unlimited
upstream, 20 locally, measured difference below 0.0012". Each of those documents now
links here rather than being rewritten, because their results tables are frozen.

This is worth reporting upstream alongside the TLR key/description swap: both are
metadata bugs rather than data bugs, and both change how the published table should
be quoted.
