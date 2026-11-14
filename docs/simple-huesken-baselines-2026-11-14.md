# Simple Huesken statistical baselines, 2026-11-14

This is a **local measured-data diagnostic**, not a reproduction of the
published OligoGym benchmark. At the time of this run, the earlier five-seed
Gate 1 criterion remained open; the subsequent 30-seed reassessment is recorded
in [Gate 1 resolution](gate1-resolution.md). The model and split settings
were fixed before inspecting the five-seed results. No source labels or rows
were changed, clipped, averaged, or excluded. The 134 Huesken labels above
100 remain in training or testing according to the saved splits.

## Protocol

- Source: pinned `Huesken` / `Ichihara_2007_1`, 2,431 rows, 30 populated source
  target strings. Source SHA-256 and revision are in each run JSON.
- Input: the first 19 nucleobases in the source FASTA's `RNA1` strand, encoded
  as 57 fixed position indicators (C/G/U; A is the reference). No vocabulary,
  scaling, imputation, or target-dependent feature transform is fitted.
  This is a deliberately simple representation, not OligoGym's published
  chemistry-aware one-hot encoder. The 19-base `RNA1` label does not assert it
  is the guide strand.
- Models: training-mean predictor; ordinary least-squares linear regression;
  Ridge with alpha in {0.01, 0.1, 1, 10, 100, 1000}; fixed Random Forest with
  200 trees, max depth 12, minimum leaf size 3, and seed-matched randomness.
  Only Ridge has hyperparameter selection.
- Outer evaluation: repository `make_split` with seeds 0–4 and 20% of groups
  held out. Report `sequence_group` (exact HELM identity) and `target` separately.
  Complete train/test IDs and label-free repeat/target audits are saved per run.
- Inner Ridge selection: five folds **inside the outer training rows**, scored
  by mean validation RMSE. The exact-HELM outer split uses shuffled KFold by
  row, with the outer seed. Since every Huesken HELM is unique, this keeps
  molecule identities separate. The target outer split uses GroupKFold by
  source target ID. Each inner validation ID is saved; all are members of the
  corresponding outer training partition. The winning alpha is refit on all
  outer training rows before the held-out test is scored.
- Metrics: Pearson r, RMSE, and MAE on held-out rows. Means and sample SDs are
  across five outer seeds, without pooling test rows. The training-mean model
  makes constant predictions, so its Pearson r is undefined rather than zero.
  No test score was used for Ridge alpha selection or for changing model settings.

The script is `scripts/train_simple_huesken.py`. Reproduce with:

```sh
PYTHONPATH=src python scripts/train_simple_huesken.py \
  --output artifacts/simple-huesken-statistical-new
```

Use an empty output directory. The completed local run is in ignored
`artifacts/simple-huesken-statistical-final-20261114/`, containing
`protocol.json`, `scores.csv`, `summary.json`, and ten run JSON files.
The protocol stores a hash of the script, source/code environment identity,
feature definition, models, seeds, and settings. This execution used Python
3.11.16, NumPy 1.26.4, scikit-learn 1.4.0, and SciPy 1.17.1; the SciPy version
differs from the project lock's 1.15.3.

## Held-out results

Each cell shows five-seed mean ± sample SD. RMSE and MAE use the source label
scale (percentage-inhibition points); lower is better. Higher Pearson r is
better, but these results are specific to their local split.

| Outer split | Model | Pearson r | RMSE | MAE |
| --- | --- | ---: | ---: | ---: |
| Exact HELM | Training mean | undefined | 20.03 ± 0.68 | 16.28 ± 0.45 |
| Exact HELM | Linear | 0.621 ± 0.020 | 15.70 ± 0.76 | 12.48 ± 0.59 |
| Exact HELM | Ridge | 0.621 ± 0.020 | 15.70 ± 0.76 | 12.47 ± 0.59 |
| Exact HELM | Random Forest | 0.570 ± 0.021 | 16.45 ± 0.68 | 12.98 ± 0.50 |
| Target | Training mean | undefined | 19.88 ± 1.89 | 16.19 ± 1.57 |
| Target | Linear | 0.627 ± 0.018 | 15.57 ± 1.51 | 12.39 ± 1.23 |
| Target | Ridge | 0.627 ± 0.018 | 15.55 ± 1.56 | 12.38 ± 1.28 |
| Target | Random Forest | 0.580 ± 0.033 | 16.22 ± 1.94 | 12.88 ± 1.54 |

Individual held-out Pearson r values:

| Split | Seed | Test rows | Linear | Ridge | Forest | Selected Ridge alpha |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Exact HELM | 0 | 487 | 0.638 | 0.638 | 0.605 | 1 |
| Exact HELM | 1 | 487 | 0.611 | 0.611 | 0.574 | 1 |
| Exact HELM | 2 | 487 | 0.638 | 0.637 | 0.559 | 10 |
| Exact HELM | 3 | 487 | 0.591 | 0.591 | 0.549 | 10 |
| Exact HELM | 4 | 487 | 0.628 | 0.628 | 0.564 | 1 |
| Target | 0 | 442 | 0.625 | 0.625 | 0.589 | 10 |
| Target | 1 | 507 | 0.598 | 0.597 | 0.526 | 10 |
| Target | 2 | 418 | 0.637 | 0.636 | 0.618 | 10 |
| Target | 3 | 452 | 0.642 | 0.645 | 0.578 | 10 |
| Target | 4 | 512 | 0.634 | 0.634 | 0.587 | 10 |

The fixed forest fits its training rows much more closely than its held-out
rows: mean training r is 0.909 versus test r 0.570 on exact-HELM splits.
The linear and Ridge models have mean training r about 0.635 and test r about
0.621. This suggests overfitting in the forest under this fixed setting; its
hyperparameters were not changed after inspecting these results.

## Interpretation limits

The exact-HELM split has no repeated Huesken HELMs to group, so it is a
row-level holdout with all 30 targets appearing on both sides. The target
split tests six held-out target strings per seed. Neither is the published
OligoGym nucleobase-cluster protocol, and this 19-base representation differs
from its winning CNN. The numeric proximity of some scores to the published
0.631 does **not** establish comparable performance or Gate 1 reproduction.
The five folds share data across seeds; sample SD is descriptive, not a
confidence interval or significance test. No active learning or RL was run.
