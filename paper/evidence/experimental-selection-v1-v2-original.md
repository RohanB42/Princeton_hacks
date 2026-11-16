# Experimental-selection RL results

## Cohort and frozen protocol

Primary endpoint is recorded Atlas inhibition in percentage points. Complete,
positive-dose and positive-duration context retained 136,901 of 174,459 released
records. The verified parser and DNA/MOE/cEt gapmer restriction retained 135,298.
Selecting the first source record per normalized chemical identity and campaign
left 133,304 records. Raw acquired values are preserved. The rankers never
use an outcome to select the retained record or define its assay stratum.

| Role | Targets | Outcome access |
| --- | --- | --- |
| Source fit | 12,000 rows from separate Atlas groups | Ridge only |
| Source calibration | 2,500 rows from distinct targets, patents and compounds | Residual scale only |
| Policy training | F7, NLRP3, STAT3 | Selected outcomes in simulated episodes |
| Policy development | DMPK, PLN | Selected outcomes for checkpoint selection |
| Final replay | DUX4, KCNQ2, PSD3, PTBP1, SMAD7 | Selected outcomes with a frozen policy |

Each final target contributes one patent-table assay campaign. The source and
campaign partitions have zero observed overlap in target keys, patent IDs,
exact normalized chemistry, natural base sequence and patent-scoped compound
IDs. Within a campaign, same-length sequences within two substitutions or one
exact base shift stay in the same pool/sentinel group. Human target aliases and
patent families are unverified. Cross-role exact checks plus within-campaign
near-sequence grouping leave broader cross-target homology unassessed.
The recorded panel's unlabeled candidate features are available at episode start.
The fixed feature hash consumes no policy-test labels or fitted test statistics.

The release/cleaned efficacy file and all supplied fold-file hashes are verified.
Supplied fold numbers are provenance only. A single generated manifest defines
access for this study and has identity
`71b77e49577aab2b76582dde7eb57688a215f8d49e6ebb2597545162fbccea79`.
The new source prior's identity is
`fb851252e1e1e7c502f48f7ffb1c410b7f3b487c150ee510f9f197679da138b6`.
LoRA is a separate research result, and no task labels enter this source prior.

Five paired seeds per target share **10 initial measurements plus 40 new
measurements**. Every acquisition spends one assay. An outcome strictly above
80 percentage points is a hit in this fixed diagnostic definition. The seed
assays are included in total cost and excluded from new-hit credit. Stop is
masked for the fixed-budget comparison. A trained policy is selected on
development campaigns and evaluated deterministically. Different replay seeds
share the same five biological tasks.

## Discovery

| Method | V1 mean new hits | V2 mean new hits |
| --- | ---: | ---: |
| Random | 3.76 | 3.76 |
| Highest current predicted mean | 8.36 | **9.20** |
| Fixed source predicted mean | 8.36 | 8.36 |
| Sequence diversity | 4.96 | 4.96 |
| Chemistry diversity | 5.68 | 5.68 |
| Budget-scheduled diversity then mean | 8.08 | 8.72 |
| Latent uncertainty | — | 4.60 |
| Total predictive uncertainty | — | 4.60 |
| Mean/latent/diversity hybrid | — | 6.48 |
| MaskablePPO | 8.36 | 8.36 |

V1 includes 150 held-out episodes and V2 includes 250. V1 PPO chose the fixed
mean expert on all 1,000 final decisions. V2 PPO chose the source mean expert
on all 1,000 final decisions. PPO minus random was +4.60 hits in both versions
(descriptive target-bootstrap 95% interval −0.24 to +10.68). V2 PPO minus
highest updated mean was −0.84 (−2.60 to +0.80). This single-training-seed
study found no PPO benefit over the strongest heuristic. An exact V1 re-run
reproduced all 150 scientific episode records, and both checkpoints reproduced
their validation probe ledger after reload.

## V2 uncertainty and prediction

The online update conditions a 32-dimensional chemistry representation plus
intercept on the residual from the fixed source prior. It reports posterior
latent SD and modeled observed-outcome SD separately. The disjoint source
calibration residual RMS, **27.65 percentage points**, is the assumed
homoscedastic noise scale. It includes model error and target/context shift.
The metadata has 1,539 same-table/context duplicate groups, with batch
independence unverified, so experimentally identified aleatoric SD is null.
A fixed RBF-plus-offset GP provides a same-trajectory posterior reference.

Final never-acquired sentinel findings on identical V2 PPO acquisition ledgers,
averaged across paired seeds and targets:

| Predictor | RMSE | Gaussian NLL | CRPS | 50% coverage | 80% coverage | 90% coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen source | 29.42 | 4.815 | 16.82 | 41.7% | 77.6% | 88.0% |
| Online Bayesian linear | 25.80 | 4.703 | 14.80 | 55.9% | 87.8% | 95.5% |
| Fixed-kernel GP residual | 25.76 | 4.701 | 14.78 | 55.6% | 88.0% | 95.6% |
| Online linear mean, constant scale | 25.80 | 4.685 | 14.72 | 50.3% | 84.1% | 92.7% |

Prediction RMSE improved relative to the fixed source model. On these
discovery-selected trajectories the online linear RMSE was 25.24 after 10
measurements, 25.14 after 25, and 25.80 after 50, so improvement was not
monotonic. Nominal 90% intervals averaged 100.53 points wide for the adaptive
linear model and 90.95 for the same mean with constant scale. The posterior
scales are model-conditional and showed aggregate overcoverage and weaker
NLL than that constant-scale control. All final latent- and total-uncertainty
ledgers matched under the homoscedastic assumption, as expected from their
monotone ranking relationship. Per-target checkpoints, widths, NLL, CRPS and
scale/error rank diagnostics are available in the run artifacts.

## V3 readiness

A label-free same-patent, normalized-chemistry and matched-context join across
separate source tables found **5,126 candidate compounds** in 44 target/patent
groups. Thirty groups have at least 20 candidate matches. The source curves
have four or more distinct positive doses. These are metadata matches and
exceed the planning floor. Independent assays, usable fitted curves,
censoring, advancement bias and downstream partition integrity still require
validation. The V3 implementation gate remains closed.
