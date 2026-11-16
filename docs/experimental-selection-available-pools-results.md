# Available-pool PPO replay and comparison with random

Completed November 15, 2026. The original 6,000-candidate request failed a
metadata-only capacity preflight. No compatible campaign had 6,000 distinct
recorded compounds even before sentinel holdout. That attempt read no outcome
values, fitted no predictor and trained no policy. The configuration and failure
receipt remain preserved. The user subsequently selected PSD3's 1,759 available
pool candidates and SMAD7's 603; these are the actual evaluation sizes below.

The [protocol](experimental-selection-available-pools-protocol.md) fixed the
three-layer, 32-neuron policy, fifty-assay budget, training settings and outcome
boundaries before the new replay. Five policy seeds and five paired replay seeds
were averaged, with equal weight per target. All methods shared initial ten
measurements within each episode; those measurements spend budget but do not earn
new-hit credit. A hit has recorded inhibition strictly above 80 percentage points.

## Requested PPO versus random comparison

| Method | Mean new hits | PSD3 | SMAD7 |
|---|---:|---:|---:|
| PPO, three layers of 32 | 11.98 | 23.80 | 0.16 |
| Random screening | 5.10 | 9.80 | 0.40 |
| PPO minus random | +6.88 | +14.00 | -0.24 |

The ratio of the two target-macro means is 2.35, or approximately 135% more hits
for PPO in this observed replay. That descriptive effect is not a demonstration
of improved performance on new biological targets. The benefit is highly uneven:
large on PSD3, slightly negative on the rare-hit SMAD7 campaign.

## Statistical significance

This is a requested, post-hoc exploratory analysis. The unit is the target
campaign, with policy training seeds and assay-initialization/replay seeds averaged
within target. They are repeated runs on shared molecules, not new biological
replicates. Two target groups are available, and both have prior outcome exposure.

An exact paired permutation test swaps PPO and random within each target, using
the mean paired difference as the statistic. This assumes paired exchangeability
under the null; it does not establish that these targets are a random sample of
future tasks. There are only four sign assignments, giving null differences
`[6.88, 7.12, -7.12, -6.88]` hits. The observed difference is +6.88.

- Two-sided exact p-value: **1.00**.
- One-sided p-value for PPO outperforming random: **0.50**.
- Descriptive exact empirical two-target bootstrap 95% interval for the mean
  difference: **[-0.24, +14.00] hits**. With two groups this interval is poorly
  supported and is not reliable population-level uncertainty.

At the target level, the result is not statistically significant. This is not
evidence of equality: the design has too few independent target groups to make a
useful generalization test. Even two uniformly positive target differences could
not reach p < 0.05 with this exact two-sided test. More repeated trajectories on
the same targets do not solve the target-count limitation.

The computation uses SciPy 1.15.3's
[paired sample permutation test](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.permutation_test.html).
All four sign assignments were independently enumerated to verify SciPy's null
distribution and p-value. The mean counts were reconstructed from episode ledgers,
and matching seed IDs/budgets were checked before analysis. No outcome threshold,
policy, split or acquisition decision was changed by this analysis.

## Model behavior and verification

The source Ridge identity and all source-fit, calibration, training and development
memberships matched the original 600-candidate width-32 run. All five selected
policy checkpoints had tensor-for-tensor identical model parameters to their
original width-32 counterparts. Thus the changed outcomes reflect the expanded
evaluation pools and changed initial draws, not improved learned weights.

PPO remains an aggregate-state acquisition-expert selector. Across 2,000 final
decisions it chose updated mean 1,482 times and fixed source mean 518 times. It is
not an LLM or a direct 1,759-way candidate policy. The complete benchmark output
retains every prespecified arm and contrast; the requested plot shows only PPO
and random.

The five training/checkpoint-selection/reload phases took 21.15 seconds total; the
run function took 26.63 seconds. Core lint, formatting, imports and all 227 repository
tests passed. Fifteen optional experimental-selection tests passed in the pinned
runtime, including explicit evaluation-size overrides that preserve training/dev
membership and a 6,000-candidate failure that cannot consume sentinels or invent
additional candidates. All eighty final acquisition ledgers passed budget,
uniqueness, reward and fit-label-count checks. Acquisition seals, source-file
receipts, preflight manifests and checkpoint parameter equality were verified.

Gate 1 remains open. These are repeatedly examined retrospective campaigns, not
prospective experiments, evidence of clinical safety or verified dollar savings.
The user-approved fifty-assay budget retains an unresolved $30,000 mapping.

## Artifacts

`artifacts/experimental-selection-6000/` contains `capacity-audit.json` and
`preflight-failure.json`. The supported replay is in
`artifacts/experimental-selection-available/run-v1/`, with source/prior/policy
receipts, five checkpoints, eighty episode ledgers, the complete benchmark report,
deferred sentinel metrics and `audit.json`.

The user-requested analysis is in its `random-comparison/` directory:

- `ppo-vs-random.png`: visually checked two-method figure.
- `statistics.json`: exact results and limitations.
- `analyze.py`: reproducible analysis using sealed report/episode artifacts only.

All run artifacts and new RL weights remain ignored. Earlier results were preserved.
No commit, push or remote CI run is claimed.
