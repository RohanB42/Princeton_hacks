# Existing-predictor robustness: corrective replay

Main was pulled first and is synchronized at `47b7c1d`. Local implementation is
on `codex/robustness-correction-tests`; it is uncommitted and has not been pushed.
This executes a bounded part of the
[correction](2026-11-14-2029-est-robustness-zero-coverage-correction.md), under the
user's subsequent request to plan and test the existing predictors.

## What changed

Added an inference-only runner, checkpoint/source/protocol hash checks, compatible
runtime enforcement for trusted local joblib artifacts, exact training-membership
checks, metadata preflight, development-only threshold selection, sealed matched
query searches, and deferred measured evaluation. No replacement model is fitted.
The earlier ASOptimizer runner, admission rule and zero-coverage result are intact.

All 287 published checkpoint files passed their recorded byte counts and SHA-256
hashes: 154,567,206 bytes. Integrity is different from inference validation. Only
the named models below underwent inference and measured replay.

The supported ASO checkpoint is the published JSON bundle with SHA-256
`44f975ae47c1a073ec52bde1e3403baa21de8a1b0b733e4bcac1a9b236252a84`.
Its new cohort excludes its 2,000 training IDs, training patents, exact compounds,
Hamming-distance <=2 analogues and one-base shifts relative to training. It uses
the exact supported chemistry and five-field assay. Evaluation components connect
targets, patents and exact compounds. This is a new historical diagnostic cohort,
not reproduction of the bundle's original prepared-cohort assessment.

## Actual results

Errors below are equal-group, then equal-compound weighted, in inhibition percentage
points. They need not equal historical row-weighted RMSE. All runs had 100% admitted
prediction coverage, zero refits, unchanged checkpoint hashes, and five paired
query seeds. The maximum query budget was 50 per group/arm, with k=5; small pools
were exhausted earlier. All reported panels contained five distinct compounds.
Shortlist outcomes average recorded assay replicates within compound/context group.

| Frozen predictor | Fit / development / final rows | Final groups | Primary RMSE | Guarded minus ordinary shortlist efficacy |
| --- | ---: | ---: | ---: | ---: |
| Huesken siRNA GP, RF comparator | 1,944 / 144 / 343 | 20 | 14.55 | 0.00 |
| Earlier Atlas pilot Ridge, HGB comparator | 3,800 / 700 / 273 | 1 | 20.92 | +3.66 |
| Published supported ASO Ridge | 2,000 / 80 / 1,869 | 2 | 28.10 | -1.90 |

The Huesken warning threshold was GP latent SD <=10. It retained all final records,
so it did not improve decisions or error. These targets already occur in training;
20 final groups do not establish unseen-target generalization.

The Atlas pilot threshold was Ridge/HGB disagreement <=5. It retained 75.09% of
final records, but compound-balanced MAE **increased** from 18.67 to 19.46.
A +3.66 shortlist difference on one component is descriptive and does not establish
a useful safeguard or generalization. No confidence interval is reported.

The supported ASO threshold was normalized Hamming distance <=0.4. It retained
93.69% of final records. Macro MAE changed only from 25.519 to 25.501, while measured
shortlist quality declined by 1.90 points. With two final components and two
development components, this supplies no basis for deploying that guardrail.
No confidence interval is reported.

Direct/wrapper maximum errors were zero for the GP/RF and pilot Ridge/HGB and
7.11e-15 for the portable ASO Ridge probe; reverse-order differences were zero.
Warnings were not calibrated probabilities. Ridge/HGB disagreement is not an
independent biological evaluation. All outcomes are retrospective development
replay; none are untouched external confirmation or novel-molecule measurements.

## Preserved failures and corrections during implementation

The first supported-bundle preflight produced six development rows and stopped
before any endpoint read. The outcome-free rule was amended to consume the same
shuffled component order until the predeclared ten-row minimum was reached.
No alternate seed was selected. The failed run remains preserved.

A regression test caught floating-point threshold ties in sqrt/squared Euclidean
conversion. The runner now recovers integer Hamming mismatches before normalizing.
A further invariant test requires shortlisted compounds to use the mean of their
recorded assay replicates rather than an arbitrary representative row. The latter
changed the pilot shortlist contrast from the provisional +3.92 to +3.66.
Reruns used unchanged cohorts, thresholds/grids and seeds; superseded local outputs
were preserved. No favorable outcome was used to select a replacement configuration.

## Local artifacts and repeat commands

Current reports:

- `artifacts/robustness/existing-huesken-correction-v3/report.json`
- `artifacts/robustness/existing-atlas-correction-v4/report.json`
- `artifacts/robustness/existing-supported-correction-v5/report.json`
- `artifacts/robustness/published-checkpoint-integrity-correction.json`

Each successful directory includes metadata/preflight, frozen predictions,
development guardrail selection, sealed search and report JSON/Markdown. Generated
artifacts remain ignored. Outputs must be fresh directories; existing results
cannot be silently overwritten.

Use `scripts/test_existing_predictors.py --suite huesken|atlas|supported --output PATH`
with `PYTHONPATH=src` and the suite's compatible Python 3.11 runtime. Joblib suites
also require `--trust-owner-local-artifacts`; the portable JSON suite does not.
Hashes and exact configuration are in
[existing-predictors-v1.json](../../configs/robustness/existing-predictors-v1.json).

Huesken ran in `/private/tmp/oligo-train-venv` with pinned OligoGym and sklearn
1.4.0. Atlas and supported ASO ran in isolated `.venv-artifact-interop` with NumPy
2.2.6, scipy 1.16.3, sklearn 1.7.2, joblib 1.5.2 and PyArrow 22.0.0. The core lockfile
and shared runtime were not modified. Portable model inference itself uses only
standard-library JSON/math; the study runner uses the scientific packages.

## Remaining work

Atlas LoRA weights are present and integrity-checked, but neural inference was
**not executed**. The recorded 1.2 GB RNA-FM backbone path is absent in this
workspace. Loaders and original cohort/split reconstruction live on pinned research
branches. Restore the verified backbone, matching runtime and original membership
receipts before inference; do not guess classes, training splits or normalization.
The published checkpoint README documents those dependencies. No ASO GP is identified
in the published inventory; the existing tested GP is siRNA-specific.

The [implementation plan](../existing-predictor-robustness-plan.md) specifies that
next phase. Controlled perturbations of these checkpoints, a separate assay-transfer
protocol, calibrated intervals and prospective confirmation remain unfinished.
These diagnostics neither establish an end-to-end robustness system nor validate a
safety model. Current main has retired the old RL environment.

## Verification

Python 3.11 / Poetry 2.1.4: `make lint format-check import-check test` passed,
including **207 core tests**. The three optional robustness science tests also
passed. Seven new invariant tests cover hash/trust rejection before loading,
training/compound overlap, zero-context preflight, final-label poisoning, seals,
published portable inference/context gates, exact Hamming threshold ties and
replicate-aware shortlist evaluation. Checkpoint integrity and the three measured
replays above were executed separately. No CI run or remote publication is claimed.
