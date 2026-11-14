# Single-endpoint predictor, first pass (I3), 2026-11-14

Huesken / `Ichihara_2007_1` siRNA efficacy only. Every r below is on the official
OligoGym **`nucleobase` split** (8 k-mer clusters, test_size 0.2), mean over 30 seeds
(100-129) with sample SD, not a confidence interval. Seeds 100-129 were fixed before
any evaluation; the kernel was chosen on seed 0 (below). No target-split number is
reported here. Nothing is claimed about active-learning benefit.

## What was built (behind the unchanged `Predictor` contract)

- `features/upstream.py`: stateless one-hot base featurizer around OligoGym's
  `OneHotEncoder`: fixed alphabet (A,C,G,T,U), fixed 42-monomer padding (two 21-nt
  strands), 210 features. Nothing is fitted, so no feature state depends on any row.
  Unrepresentable input raises. `verify_upstream_environment()` requires an OligoGym
  git checkout at the pinned revision and scikit-learn 1.4.0 and raises otherwise.
- `models/baseline.py`: `OneHotRandomForest` (Gate 1 anchor config) and
  `OneHotGaussianProcess`. Both are refit from scratch on every `fit` and expose
  `config` including the verified upstream revision.
- Uncertainty is named and uncalibrated. GP: `gp_latent_sd_uncalibrated`, the latent
  function SD **with the fitted observation noise removed**. sklearn's `return_std`
  includes the WhiteKernel variance, which is a constant aleatoric floor (about 14
  label units here, against a label SD of 20.15) and cannot rank candidates. RF:
  `rf_tree_prediction_sd_uncalibrated`.
- Tests: `tests/test_models.py` (core, runs anywhere) and `tests/upstream/` (9 tests,
  marked `upstream`). Plain `pytest` excludes `tests/upstream` (62 pass);
  `pytest -m upstream` or `pytest tests/upstream` selects it, and it **fails, never
  skips**, without the pinned environment (verified by blocking the import).

## Kernel selection (before any evaluation seed was touched)

`scripts/select_gp_kernel.py`; preregistered 6-kernel grid in
`models.baseline.KERNEL_GRID`. Seed 0 official-split TRAIN rows only; 5-fold
GroupKFold over k-mer clusters (mirrors the evaluation split); criterion mean
Pearson r. Hyperparameters still refit by marginal likelihood on each `fit`'s revealed
labels. This is a one-time structural choice made with the full seed-0 training pool,
whose rows reappear in other seeds' test partitions; it is disclosed, not eliminated.

| Kernel (initial length scale) | Mean validation r |
| --- | ---: |
| RBF 1 (the sklearn-like default) | 0.3049 (fails: local optimum, predicts near mean) |
| RBF 4 | 0.615054 |
| RBF 8 | 0.615054 |
| RBF 16 | 0.615053 |
| Matern 1.5 / 2.5 (8) | 0.6148 / 0.6149 |

RBF 4 and RBF 8 are identical to six decimals (same fitted optimum, length scale
about 7.5-9); the argmax picked RBF 4, which is now the default. The earlier
hand-picked RBF 8 is functionally the same kernel.

## Accuracy (`nucleobase` split, seeds 100-129, `scripts/evaluate_predictors.py`)

| Model | Seeds | Mean r +- SD | Published mean (5 unseeded draws) | Gap |
| --- | ---: | ---: | ---: | ---: |
| One-hot GP (RBF+White) | 30 | 0.6163 +- 0.0294 | none (GP not in the grid) | n/a |
| One-hot RF, base, 100 trees, depth 20 | 30 | 0.5620 +- 0.0290 | 0.5910 | -0.029 |
| KMers k=1-3 + `LinearModel` standard (in-grid anchor) | 29 | 0.5880 +- 0.0340 | 0.6159 | -0.028 |

The published value lies inside our mean +- SD for both anchors. Seed 112 failed on
the linear anchor (`LinAlgError: SVD did not converge`, the same rank deficiency noted
in `upstream-verification.md`); it is recorded as a failure and excluded, not
imputed. GP beat RF on 29 of 30 seeds. Both anchors again sit about 0.03 below
upstream, as in `gate1-resolution.md` (the residual shift remains unexplained), so
the GP's 0.616 is not directly comparable to the published CNN's 0.631 (best of 372
configs, same shift likely applies). RMSE: GP 15.56, linear 15.99, RF 16.46.
Runtime per fit+predict: GP 4.7 s, RF 2.7 s, linear 1.4 s. GP r is not tuned against
these seeds.

## Uncertainty diagnosis (the gate that precedes any acquisition claim)

Test-candidate spread and agreement with truth, averaged over 30 seeds (ranges are
across seeds):

| Quantity | GP latent SD | RF tree SD |
| --- | ---: | ---: |
| Coefficient of variation across candidates | 0.020 (0.017-0.023) | 0.131 (0.122-0.139) |
| Max / min across candidates | 1.14 (1.10-1.18) | not reported |
| Spearman(SD, absolute error) | 0.057 (-0.04 to 0.18); positive in 27/30 seeds | 0.029 (-0.11 to 0.12); positive in 23/30 |
| Spearman(SD, distance to nearest training row) | 0.54 (0.46-0.59) | 0.10 (0.01-0.20) |

- Removing the noise floor fixes the semantics but the corrected GP SD is still
  nearly flat (median 6.8 label units, about 14% max-to-min). By the criterion we set
  (it must vary), **it is not a usable error-targeting signal on this representation.**
- It is, however, a real novelty signal: it tracks distance to the labelled set
  (rho 0.54). Argmax latent SD is effectively farthest-point sampling in one-hot
  space. Whether that helps is an empirical question for the loop, and it should be
  tested against an explicit diversity baseline and random.
- RF tree spread varies more but tracks neither error nor novelty. The fallback does
  not rescue the signal.
- Total GP predictive SD covers 68.8% at 1 sd and 94.6% at 1.96 sd (nominal 68.3/95),
  but only because the noise floor is nearly constant. This shows the noise level is
  right, not that uncertainty discriminates.
- This is also not why the earlier 180 campaigns were inconclusive: they used
  `HelmHashForest` tree spread (varying, uncalibrated), never a GP.

## Leakage check

Max ungapped RNA1 identity of each test siRNA to any training siRNA (register shifts
+-5, overlap >= 16 nt): median 0.74, p95 0.95, max 1.00 per seed. Near-identical
overlapping siRNAs do cross the cluster boundary. GP r by identity bin (pooled over
seeds; rows repeat across seeds, so bins are not independent): 0.609 at 0.60-0.75
(9,077 rows), 0.625 at 0.75-0.90 (6,383), 0.667 at 0.90-1.00 (3,109). Accuracy is
about the same for dissimilar test rows, so near-duplicates are not driving the
number, but they inflate the "unseen family" reading slightly.

## Not done / for the integrator

- No RunArtifact gate: "emit no artifact unless the upstream suite passed" touches the
  runner, Makefile and CI. Proposed: a `make test-upstream` target and a stamp the
  runner checks. Marker and exclusion are implemented in `tests/conftest.py`, so no
  `pyproject.toml` edit is needed.
- Lockfile: OligoGym plus catboost, torch-geometric and torchinfo are not in the
  project's locked science group; the upstream environment is built separately
  (see `gate1-resolution.md`; also tabpfn 2.0.9 and setuptools < 81).
- TabPFN skipped by decision (CPU-only here; 179 s at 1,896 rows).
- Next: wire these predictors into the replay runner and compare random, latent-SD
  and an explicit diversity policy at matched budgets. Do not rerun the 180 campaigns
  expecting the old conclusions to carry over.

## Reproduce

```sh
# pinned upstream env (docs/gate1-resolution.md), then from the repo root:
PYTHONPATH=src python -m pytest -m upstream
PYTHONPATH=src python scripts/select_gp_kernel.py --output artifacts/gp-kernel.json
PYTHONPATH=src python scripts/evaluate_predictors.py --seeds 100 130 \
    --output artifacts/predictor-eval.json
```
