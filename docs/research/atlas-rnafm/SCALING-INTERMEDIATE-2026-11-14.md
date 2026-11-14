# Atlas LoRA scaling: intermediate checkpoint

Snapshot: **2026-11-14 20:44:57 UTC**. Branch: `codex/atlas-lora-scaling`.
This is an immutable progress snapshot, not a completed study or a positive result.

## Execution status

- **136/240** planned fit/calibration records completed;
  **0 failures**; recorded elapsed time **69.77 minutes**.
- Both source budgets are complete for paired source seeds 510 and 511;
  seed 512 and target-only controls remain in the planned matrix.
- No target test metrics have been scored. Seven reserved targets remain unscored.
- Training continues in the isolated worktree. This publication does not change
  the frozen config, model recipe, stopping rules or evaluation schedule.

## Completed source neural fits

RMSE is measured inhibition percentage points. These are internal patent-validation
results used for checkpoint selection, not final target-transfer scores.

| Source seed | Source fraction | Model | Epochs run | Selected epoch | Selected validation RMSE | Last validation RMSE |
| --- | --- | --- | --- | --- | --- | --- |
| 510 | 3% | frozen_chemistry | 11 | 6 | 25.559 | 26.387 |
| 510 | 3% | lora_chemistry | 6 | 1 | 26.179 | 29.294 |
| 511 | 3% | frozen_chemistry | 11 | 6 | 31.121 | 32.745 |
| 511 | 3% | lora_chemistry | 7 | 2 | 30.757 | 33.755 |
| 510 | 5% | frozen_chemistry | 10 | 5 | 30.345 | 34.884 |
| 510 | 5% | lora_chemistry | 8 | 3 | 31.018 | 34.755 |
| 511 | 5% | frozen_chemistry | 10 | 5 | 29.126 | 32.339 |
| 511 | 5% | lora_chemistry | 9 | 4 | 28.987 | 33.273 |

Training longer is not uniformly beneficial: some fits select early epochs while
others improve later. The selected checkpoint is restored after early stopping.
Neither more-data superiority nor superiority over classical models is established.
Validation membership differs between 3% and 5%, so comparing these raw validation
RMSEs does not estimate the effect of source-data size. That contrast requires the
same development-target test rows after matched target adaptation.

## Protocol and limitations

The percentages refer to 95,638 eligible source-training observations: 2,869 and
4,781 total labels respectively, including internal validation labels. They do not
refer to the entire Atlas release. Three source seeds pair with three acquisition
seeds on three development targets, F7, STAT3 and NLRP3. There are three target
identifiers, not nine independent target genes.

At the target stage, fixed-three-epoch fits use all 200 acquired labels. The
validation-selected duration arm uses 160–166 for gradients and 34–40 for validation;
this comparison changes both duration selection and gradient-row count.

Source validation is patent-held-out, not strictly compound-held-out: three of six
partitions contain one exact normalized compound on both sides, with 0–4 natural-base
identity intersections. The frozen partitions and this caveat are retained. Existing
source-to-target exclusions remain enforced. No toxicity, molecular-design RL,
therapeutic improvement or experimental label savings is demonstrated by this study.

## Verification and provenance

At publication preparation: **160 core tests passed**, **28 focused optional tests
passed** (these suites overlap and should not be summed), Ruff lint and formatting
passed for 130 files, and completed-receipt audits passed. Audits include label-budget
and split boundaries, unchanged base weights, and exact prediction equality when
source epoch 3 equals the selected source checkpoint.

The active process predates later runner validation/audit refinements. Its original
invocation sources and hashes are archived locally under `scaling-v1/provenance/`;
do not describe it as having launched from the publication commit. No model recipe
was changed in response to observed outcomes. The initial profile read the cohort
before subsetting permitted labels; subsequent execution filters endpoint reads at
the Parquet boundary. No reserved outcomes entered fitting, stopping or analysis.

Snapshot suite SHA-256: `9384f01230295d8d5ccd761f4972771eda3fa6e3aef4a83f3ee3f8f7966cc5de`.
This hash identifies the local machine-readable checkpoint; that live file continues
to change. Raw artifacts, predictions, histories, model weights and PNGs remain
ignored and are not published. The repository contains methods, source code, tests,
configuration and this aggregate summary. The local borrowed-path runtime and
checkpoint paths remain a documented clean-install portability limitation.

## Continue and inspect

- [Methods and commands](SCALING-METHODS.md)
- [Live status and accounting](SCALING-STATUS.md)
- [Environment and portability](ENVIRONMENT.md)
- [Earlier completed study](RESULTS.md)

Local curves: `artifacts/atlas-rnafm/scaling-v1/source-loss-epochs.png` and
`source-loss-time.png`. Training/report scripts regenerate artifacts locally;
do not run final target scoring until the planned fitting phase ends.
