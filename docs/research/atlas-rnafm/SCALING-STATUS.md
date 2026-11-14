# LoRA source-data and epoch scaling status

Updated November 14, 2026. Isolated branch `codex/atlas-lora-scaling`, base `9fd9f10`.
Read SCALING-HANDOFF.md for authorization and scientific boundaries.

State: instrumentation implemented and nine focused tests pass; all six source and
nine target validation partitions frozen before fitting. First 3% LoRA source profile
is running. No new target test outcomes have been scored.

Active command (from this worktree):

```sh
PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 /private/tmp/oligoal-atlas-rnafm-20261114/.venv-atlas/bin/python scripts/run_atlas_scaling.py --phase profile > artifacts/atlas-rnafm/scaling-v1/profile.log 2>&1
```

Process PID77779; execution-tool session79735. One heavy process only. Frozen
whole-study wall cap14,400 seconds; source seeds510–512 paired with target610–612.
First profile is retained as the first planned source fit. Target duration begins
only after the source profile and matched source3/sourcebest contrasts.

Source counts (fit / validation, both charged to the stated budget):

| Source seed |3%:2,869 labels|5%:4,781 labels|
|---|---:|---:|
|510|2,284 /585|3,813 /968|
|511|2,300 /569|3,834 /947|
|512|2,295 /574|3,847 /934|

Denominator95,638 source-training records. External14,614-row source-validation
partition unused; seven reserved targets untouched. Target200 budgets reserve34–40
labels for sequence-group validation in the duration-selected arm; fixed3 target
fits use all200. These are different fitting protocols and reported separately.

Artifacts: `artifacts/atlas-rnafm/scaling-v1/{config,partitions,suite}.json`;
per-fit history/checkpoints/receipts appear in source/target subdirectories. Source
validation uses patent groups; target validation uses pool-wide sequence components.
All feature fitting and gradients exclude validation rows.

Checks: nine focused tests passed; changed-file Ruff lint and format pass. Tests cover
best-state restoration, base integrity, validation-gradient exclusion, held-out label
poison invariance, group/budget integrity and preservation of legacy fixed epochs.
Core/full optional checks remain pending. No new dependencies or main files changed.

Next: collect source per-epoch validation profile, publish first curves/time estimate,
then resume the matched frozen/LoRA/Ridge/XGBoost matrix within the declared cap.

First measured epoch: 65.41 seconds, source train RMSE30.626 and patent-validation RMSE26.179. One epoch cannot diagnose undertraining/overfitting. A20-epoch3% LoRA source fit projects about22minutes;5% about36minutes if throughput scales linearly. Six maximum-duration LoRA source fits alone project roughly3hours; early stopping may reduce this. The four-hour cap is retained; exact incomplete counts will be reported if reached. First actual PNGs: `scaling-v1/source-loss-epochs.png` and `source-loss-time.png` (pending panels explicitly marked).

Implementation verification:160 core tests and27 focused optional tests passed
(counts overlap for existing parser tests); full-repository Ruff lint/format,
import-path verification and git whitespace checks pass. New tests additionally
show that enabling history does not alter fixed-epoch optimization and endpoint
subset reads return only explicitly permitted IDs.

Source-only first four epochs: training RMSE30.626→21.803 while validation
RMSE26.179→28.284. This preliminary divergence does not establish target behavior.
Selection remains unchanged: lowest validation RMSE among all completed epochs,
minimum3 epochs executed, patience5 without an improvement greater than1e-6.
The selected epoch may precede3; the epoch3 checkpoint is independently retained.

Audit limitation: internal source patent groups are disjoint, but three of six
partitions have one identical normalized compound identity across fit/validation;
natural-base identity intersections range0–4. These memberships were frozen before
outcomes and remain unchanged. Their patent-held-out validation is not a strict
molecular-identity holdout. Existing source/target exclusions and target sequence
components are preserved. Metadata-only audit output: `scaling-v1/audit.json`.

The first profile loaded the label-bearing cohort before restricting the label
Series to permitted fitting rows; no reserved outcomes reached models, stopping,
metrics or any analysis. The full runner now reads feature columns separately and
filters endpoint reads to permitted IDs at the Parquet read boundary. This strengthens
access control without changing any training row, label, split or hyperparameter.
Per-invocation script hashes preserve the implementation difference.

Profile completed:6 epochs in383.70seconds; selected source checkpoint epoch1
(validation RMSE26.179, versus27.557 at epoch3 and29.294 at epoch6). Training
RMSE fell to15.555. Base weights unchanged and LoRA adapters updated. This first
source condition shows overfitting with extra epochs at the fixed learning rate;
it does not yet answer target transfer or the larger-source comparison.

Full matrix resumed with `scripts/run_atlas_scaling.py --phase run`, output redirected
to `artifacts/atlas-rnafm/scaling-v1/run.log`. Active PID78172; tool session70225.
The completed profile is reused unchanged. All three paired seeds remain scheduled
within the original4h cap. Code commits5ec29dc andf509ff3 are isolated, unmerged and
unpushed. Current completed count:1; failed count:0.

First complete paired source condition (3%, source seed510 / target seed610):
34/240 planned fit/calibration records now complete, no failures. Both FM arms,
source Ridge/XGBoost and all three target protocols/offset controls completed for
F7/STAT3/NLRP3. LoRA source ran6 epochs (best1); frozen source ran11 (best6).
The5%/seed510 source run is active. Target scoring remains deferred until the whole
matrix is fitted. Metadata/receipt audit passed for all completed records; actual
source curves refreshed. Planned totals are24 source models,180 source-conditioned
adaptations/calibrations and36 target-only controls, yielding216 final scoring rows.

Log formatting caveat: this running invocation prints `validation 0` for the fixed3
protocols that have no validation input. Their structured histories correctly omit
validation metrics; zero is not a measured validation error. The script's display
has been corrected to `None` for future invocations, without changing this run.
