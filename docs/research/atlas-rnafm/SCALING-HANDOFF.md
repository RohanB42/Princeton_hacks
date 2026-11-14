# Atlas LoRA data/epoch follow-up — execution authorization

Prepared 2026-11-14 14:26 EST / 19:26 UTC. User explicitly requests a separate
subagent to run additional LoRA epochs and 3%/5% source-data experiments while the
main conversation continues planning RL. This is an independent efficacy study,
not implementation of RL or synthetic reward augmentation.

## Worktree and prior evidence

Work ONLY in `/private/tmp/oligoal-atlas-lora-scaling-20261114`, branch
`codex/atlas-lora-scaling`, base `9fd9f10`. The main repository and original research
worktree must remain unchanged. Set workdir explicitly on all shell calls.

Read AGENTS.md, canonical project/evaluation/interface docs, the inherited Atlas
plan/handoff, and `docs/research/atlas-rnafm/{RESULTS,ENVIRONMENT,DECISIONS}.md`.
This file supersedes their old fixed-three-epoch/1,000-source-label defaults only
for the new, separately named follow-up. Preserve historical runs and conclusions.

Original comparison: 1,000 source labels; fixed three epochs; three development
targets F7/STAT3/NLRP3; target seeds610–612; 50/100/200 target budgets. Mean RMSE
at200: target Ridge19.6256, source Ridge+offset19.6342, frozen FM22.3546,
LoRA21.9861. Training loss was still decreasing in a later identical-settings
replay, but no historical per-epoch validation losses exist. This is evidence
to test undertraining, not evidence that extra training will improve generalization.

## Frozen scope and percentage denominator

The denominator is **95,638 leakage-filtered source-training records**, not all
Atlas rows. Use nested deterministic budgets `floor(0.03*N)=2869` and
`floor(0.05*N)=4781`. Record actual fractions and immutable selected IDs. Count
all source labels used for validation against these budgets. The existing external
14,614-row source-validation partition is NOT free extra tuning data; leave it
unused in the primary budgeted study unless a separate, explicitly costed diagnostic
is justified and reported. Do not read the seven reserved target outcomes.

Before executing fits, freeze a study config with the following initial design:

- Source seeds510,511,512; matched nested source cohorts for all model arms.
- Source arms: frozen chemistry-aware RNA-FM, LoRA chemistry-aware RNA-FM, Ridge
  and XGBoost controls with equal access to the same real data and validation.
- Keep architecture, chemistry representation, LoRA rank4/alpha8, batch8,
  AdamW lr0.001 and weight decay0 from the original comparison. This experiment
  isolates data quantity and training duration; do not silently add a learning-rate
  or architecture sweep. Record optimization failures rather than changing settings
  after final outcomes. A subsequent LR study can be proposed separately.
- Record source training and validation loss after EVERY epoch, with elapsed time,
  raw percentage-point RMSE/MSE and source-normalized loss. Prefer fixed-model
  end-of-epoch evaluation for comparable curves; distinguish it from the minibatch
  running loss logged during updates. Preserve finite/undefined status explicitly.
- Maximum20 epochs; minimum3; patience5 for validation RMSE with a documented
  tie/minimum-improvement rule. Save epoch3 and, if reached, epoch10/20, plus the
  best validation checkpoint. Do not fabricate missing later checkpoints after
  stopping. Plot actual epoch and wall-time histories.
- Reserve about20% of each source budget for internal validation by patent groups,
  documenting achieved fractions and any inability to split. Keep identical
  inner train/validation membership across arms. Use the saved best checkpoint
  trained on the inner-fit portion for the primary comparison; give classical
  models the same fitting rows. Explicitly report fitting-label and validation-label
  counts, both included in the source budget. This avoids hiding an extra all-data
  refit or additional validation labels in the claimed3%/5% cost.
- Target adaptation stays on the THREE DEVELOPMENT targets only. First compare
  source checkpoint3 vs validation-selected source checkpoints with the original
  fixed three-epoch target adaptation at200 labels. This isolates source scaling.
  Then assess target training duration up to20 epochs using grouped internal
  validation entirely inside the acquired target budget; retain a predeclared
  50/100/200 schedule if compute permits, with200 the required initial contrast.
- Target seeds610–612 are paired. To bound compute, pair source seed510 with610,
  511 with611 and512 with612 (not a9-way source/target Cartesian product). Record
  the reduced design clearly and treat all outcomes as development diagnostics.
- For target validation-selected fits, include all inner labels in the target
  budget and match comparator access. Report fixed-three-epoch/all-acquired and
  validation-selected/inner-fit protocols separately; do not attribute their
  difference solely to epoch count. An all-acquired refit at selected epochs may
  be added as a clearly recorded arm if needed for a clean final comparison.
- No acquisition/PPO/toxicity runs and no reserved-target confirmation in this task.

## Execution, compute and tests

Implement permanent optional history/checkpoint instrumentation with regression
tests so old fixed-epoch callers retain behavior. Keep source and target checkpoint
selection distinct. Test that poisoned evaluation labels cannot change histories,
stopping epoch or selected checkpoint; validation groups cannot enter gradient fits;
best-checkpoint restore includes head/adapters/context; base weights remain unchanged.

Profile the3% LoRA run before the full matrix. One heavy process at a time, CPU
single thread initially; no paid compute. Avoid large-memory caches. Freeze a realistic
wall cap and write partial status after every fit; do not truncate and present the
remaining subset as full. Prior source LoRA took~67s for1,000 labels/3epochs;
3%/5% and20epochs can take substantially longer. Validation adds cost. Run the
three-seed matrix if feasible; otherwise report the exact cap/failure and complete
the necessary paired pilot rather than silently dropping difficult seeds.

Prepared cohort/manifests/audit have been copied unchanged into this worktree's
`artifacts/atlas-rnafm/preparation-v1/`. New outputs go to
`artifacts/atlas-rnafm/scaling-v1/`, separate from all previous results.

Read-only runtime:
`/private/tmp/oligoal-atlas-rnafm-20261114/.venv-atlas/bin/python`.
Set `PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1` and verify imported
oligo_engine resolves to THIS worktree. Read-only checkpoint:
`/private/tmp/oligoal-rnafm-20261114/artifacts/rnafm-checkpoint/RNA-FM_pretrained.pth`.
Use separate local caches, never mutate the prior worktree or shared environments.

Deliver: frozen config, actual histories and training/validation PNGs (epochs and
time), paired source-size/epoch/target metrics, model/source/environment receipts,
test evidence, and a clear answer about undertraining versus overfitting. Better
training loss alone is not a success criterion. Classical baselines must be rerun
at matched budgets;19.63 is a historical reference, not a fixed score to beat.

Maintain `SCALING-STATUS.md` after every meaningful milestone, with active command,
process ID, completed counts, elapsed time and next step. Commit tested code/docs
on this branch; no merge/push or edits to main. Send the parent initial confirmation,
first validation curves, profile estimate and final results. Do not stop at a plan.
