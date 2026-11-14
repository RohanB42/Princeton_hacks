# Gate 1 resolution: multi-seed re-test, 2026-11-14

Supersedes the pass/fail reading in `upstream-verification.md`. Nothing there was
altered; the 5-seed misses (0.5848 vs 0.6159; 0.5591 vs 0.5910) stand as recorded.

## Why the 5-seed criterion was ill-posed

- Upstream's `train_model.py` (97f5b9f, line 206) calls the nucleobase split five
  times with no `random_state`, so KMeans and GroupShuffleSplit are unseeded. The
  published folds are random draws. No seed schedule exists to recover.
- Fold-to-fold SD of test Pearson r across the 372 siRNA1 nucleobase configs has
  median 0.059 (10th-90th percentile 0.024-0.175). For the two frozen configs the
  local SD over 30 seeds is about 0.030; upstream's own five-fold SDs for them
  (0.0099, 0.0091) are unusually tight and should not be used as the noise scale.
- A difference of two 5-seed means then has SE of about 0.015, so a fixed 0.03
  tolerance is only about 2 SE wide and the 0.031/0.032 misses are 1.4-1.8 sigma
  events. The linear ill-conditioning noted earlier is real but did not explain
  the gap.

## Revised criterion (tolerance unchanged at 0.03)

With at least 30 local seeds, both must hold per frozen config:
(a) |local mean - published mean| <= 0.03; and
(b) |gap| <= 2 combined SE, where combined SE = sqrt(SD^2/n_local + SD^2/5), with SD
the local sample SD (the published mean is itself a 5-fold mean).

The threshold was not loosened. The estimator changed from 5 to 30 seeds. This
revision was made after seeing the 5-seed result; its justification (unseeded
upstream splits, fold variance) comes from the upstream source and CSV.

## Result (seeds 0-29, `scripts/gate1_multiseed.py`)

| Config | Local mean +- SD | Published | Gap | (a) | z | (b) |
| --- | ---: | ---: | ---: | :-: | ---: | :-: |
| Linear, KMers k=1-3 | 0.5945 +- 0.0313 | 0.6159 | -0.0214 | pass | -1.41 | pass |
| RF, one-hot base, 100 trees, depth 20 | 0.5645 +- 0.0298 | 0.5910 | -0.0265 | pass | -1.84 | pass (marginal) |

Seeds 0-4 reproduce the earlier recorded values to 1e-11, so the pipeline is
deterministic. Environment: pinned upstream 97f5b9f, Python 3.11, numpy 1.26.4,
pandas 2.2.3, scikit-learn 1.4.0, scipy 1.15.3, torch 2.7.0, tabpfn 2.0.9
(newer tabpfn fails to import against scikit-learn 1.4.0), setuptools < 81, plus
catboost 1.2.8, torch-geometric 2.6.1, torchinfo.

## Verdict and residual caveat

Gate 1 is closed: the frozen baselines reproduce within noise, not exactly. Both
gaps are negative. The two upstream draws are independent, and the combined z is
about -2.3, so a small real shift (about 0.02-0.03) may remain; cause unknown
(BLAS/environment, scikit-learn behavior, or optimistic published draws). State
this in any write-up; do not claim exact reproduction. The published 0.631 (CNN)
is the best of 372 configs and carries selection bias; compare against specific
configs, and judge a new predictor by indistinguishability over 20+ seeds.

Earlier diagnostic acquisition results (180 campaigns) used the hashed-HELM forest
on a different split (r about 0.25 on Huesken) and are not comparable to these
baselines; rerun them on the baseline-grade predictor before drawing conclusions.
