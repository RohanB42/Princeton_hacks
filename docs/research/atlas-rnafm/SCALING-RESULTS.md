# Atlas RNA-FM: completed 3% / 5% source and duration study

Completed November 14, 2026. **Increasing source labels and allowing validation-selected
training duration did not establish a LoRA advantage over classical controls.** The
frozen FM benefited from better source training duration, but its overall target
error also remained above the strongest classical controls. This is a completed
negative development result for the tested recipe, not a conclusion that all RNA
foundation models or all fine-tuning strategies fail.

All 240 planned fit/calibration records completed without failure: 24 source models,
180 source-conditioned target fits/offset calibrations, and 36 target-only controls.
The 216 target score records were calculated after every fitting decision finished.
Total study wall time, including the retained source profile, was 6,037.1 seconds
(100.6 minutes). The resumed full-matrix process recorded peak RSS 1.64 GiB; the
first profile's separate process peak was not retained independently. No paid compute,
RL, acquisition, toxicity fitting or reserved-target scoring was performed.

## What was compared

The endpoint remains measured ASO `Inhibition_pct`, in percentage points, conditional
on recorded assay context. Source budgets are 2,869 and 4,781 measured records—floored
3% and 5% of the 95,638 eligible source-training records, **including validation**.
They are not percentages of the entire Atlas release. Source fitting uses 2,284–2,300
or 3,813–3,847 rows; the rest are patent-group validation. The external 14,614-row
source-validation partition was unused.

Three source seeds pair with three target seeds, on the same F7, STAT3 and NLRP3
development campaigns. Each target allocation contains 200 measured labels. All
models share the prescribed data access within each protocol. Architecture, LoRA
rank 4 / alpha 8, learning rate 0.001, weight decay 0, batch size 8 and CPU execution
remain fixed. Maximum 20 epochs, minimum 3 executed, patience 5 and validation RMSE
select duration. See [SCALING-METHODS.md](SCALING-METHODS.md) for exact contracts.

The two target protocols below must remain separate. Fixed-duration neural models
fit all 200 target labels for three epochs. Validation-selected target models fit
160–166 labels and reserve 34–40 inside that same 200-label allocation. Their
contrast changes both training duration selection and gradient-row count.

## Held-out target performance

Means first average the three paired seeds within each target, then the three
targets equally. Lower RMSE is better. All reported Pearson correlations are defined
for all nine contributing records in each table cell. These are development means,
not confidence intervals or nine independent target-gene experiments.

**Validation-selected source, fixed three target epochs / all 200 target labels.**
Classical transfer controls fit a target offset on the same 200 rows.

| Predictor | 3% source RMSE | 5% source RMSE | 3% Pearson r | 5% Pearson r |
|---|---:|---:|---:|---:|
| Frozen RNA-FM + chemistry | 20.893 | 21.208 | 0.205 | 0.213 |
| LoRA RNA-FM + chemistry | 22.391 | 22.340 | 0.210 | 0.225 |
| Source Ridge + offset | 19.883 | 19.656 | 0.250 | 0.293 |
| Source XGBoost + offset | 20.403 | 20.292 | 0.125 | 0.167 |

Additional controls using **no source labels**, only the 200 target measurements:
target-only Ridge RMSE **19.625611**, r **0.334**; target-only XGBoost RMSE **19.366212**,
r **0.327**. The Ridge value reproduces the previous target-only control to the
shown precision. This is local control repeatability, not source-paper reproduction.

**Validation-selected source and target duration / inner target fitting rows.**
Classical offsets use exactly the same inner fitting IDs as the neural models.

| Predictor | 3% source RMSE | 5% source RMSE | 3% Pearson r | 5% Pearson r |
|---|---:|---:|---:|---:|
| Frozen RNA-FM + chemistry | 22.164 | 21.754 | 0.220 | 0.204 |
| LoRA RNA-FM + chemistry | 21.777 | 22.604 | 0.201 | 0.233 |
| Source Ridge + offset | 20.027 | 19.753 | 0.250 | 0.293 |
| Source XGBoost + offset | 20.509 | 20.350 | 0.125 | 0.167 |

Target-only inner-fit controls: Ridge RMSE **19.559559**, r **0.344**; XGBoost RMSE
**20.102607**, r **0.299**. Their hyperparameters are selected on the same target
validation partition; validation remains included in the 200-label allocation.

LoRA minus matched source Ridge RMSE is **+2.508 / +2.683** at 3% / 5% under fixed
target training, and **+1.750 / +2.850** under the inner-fit selected-duration protocol.
The LoRA difference is unfavorable on **all three target-level averages** in every
one of these four comparisons. Frozen FM has a favorable NLRP3 result under fixed
target training, but this does not extend to the overall target-macro comparison.

## What extra epochs and data actually changed

Source-validation selected epochs, ordered by source seeds 510, 511, 512:

| Encoder training | 3% selected epochs | 5% selected epochs |
|---|---|---|
| Frozen FM, trainable chemistry/head | 6, 6, 9 | 5, 5, 5 |
| LoRA FM, trainable chemistry/head | 1, 2, 2 | 3, 4, 3 |

All source fits stopped by the predeclared patience rule: frozen fits executed
10–14 epochs, LoRA fits 6–9. Later LoRA source epochs commonly reduce training
error while validation error increases. That supports an overfitting diagnosis
for this fixed recipe; it does not identify data scarcity, learning rate,
regularization or representation mismatch as a unique cause.

The clean within-budget source-checkpoint comparison keeps target fitting fixed
at three epochs on all 200 labels. Selecting the source checkpoint improves frozen
FM target RMSE by **1.892 / 1.490** points at 3% / 5%, versus source epoch 3. For
LoRA it **worsens** 3% target RMSE by **0.711** and improves 5% by only **0.026**.
Thus source validation RMSE is not a guaranteed proxy for downstream few-shot
transfer quality, even when label isolation and checkpoint restoration are correct.

Moving to target validation-selected training changes frozen RMSE by **+1.270 /
+0.546** and LoRA by **−0.614 / +0.264**, relative to fixed three-epoch target fits.
These are protocol differences, not isolated causal effects of extra target epochs.
Four target duration runs reached the 20-epoch cap; two selected epoch 20. We do not
claim that every target head fully converged or invent later unrun checkpoints.

Moving source allocation from 3% to 5% leaves selected-source / fixed-target LoRA
almost unchanged (**−0.052 RMSE**) and worsens its selected-target protocol
(**+0.826**). Frozen FM changes by **+0.315 / −0.409** in those protocols. There is
no consistent FM scaling improvement across the tested settings. The historical
1,000-label / three-epoch experiment remains a separate preserved result; its
source validation and fitting protocol differs from this follow-up.

## Methodological limits that affect interpretation

- **Total cohorts are nested; inner fitting cohorts are not.** Patent validation is
  repartitioned within each budget. Moving from 3% to 5% replaces 440 / 340 / 336
  earlier fitting rows for the three seeds. Source-size contrasts therefore include
  changes in source patent/target composition. For example, seed 512 has 56 fitting
  target identifiers at 3% but 53 at 5%. A clean append-only data-size follow-up
  should freeze patent partition membership before sampling nested budgets.
- Internal source patent validation is not a strict molecular-identity holdout:
  three of six partitions share one normalized compound identity across fit and
  validation; natural-base intersections range 0–4. The frozen memberships were
  retained and the overlap is audited. Source-to-target exclusions remain intact.
- There are three previously used development target identifiers. Target aliases
  and patent families are not externally resolved; sequence components do not
  establish every form of homology isolation. Seven reserved campaigns remain
  unscored. Repeated seeds do not create independent biological targets.
- Target-duration comparison changes validation allocation and fitting-row count;
  source-epoch comparison does not. Both deserve their own conclusions. Fixed
  learning rate / regularization / architecture are the tested recipe, not a search
  over all plausible adaptation strategies.
- No 50/100-label target extension, active acquisition, label-savings threshold,
  novel-candidate validation or multi-endpoint safety model was run here. Improved
  source validation or training loss cannot establish any of those outcomes.

The practical decision is to retain the stronger classical controls and avoid
promoting this LoRA recipe into an RL reward head on the strength of training loss.
A separately declared optimization/regularization and transfer-aware validation
study could still be useful. It should repair the nonnested inner fitting comparison
before attributing gains to data quantity and preserve reserved targets for later
confirmation. No further experiments were automatically launched.

## Verification, provenance and artifacts

The actual receipt audit passes **120 neural fits and 120 classical/calibration
records**. All neural fits preserved base weights; all **60 LoRA fits** changed
adapters. Target fitting/validation IDs match the frozen partitions; source IDs in
target checkpoints match their source fitting cohorts. Six pairs whose selected
source equals epoch 3 produce exactly identical target predictions. The finished
report has **216 unique scoring records**, matching saved prediction bundles.

Repository checks: **160 core tests**, **28 focused optional tests** (overlapping
counts), Ruff lint/format on 130 files, import verification and whitespace checks
pass. Per-epoch loss logging, validation-gradient exclusion, complete checkpoint
restoration, fixed-epoch invariance, endpoint filtering and held-out-label poisoning
are covered. Source/target figures were rendered and visually checked.

Current artifacts remain local and ignored under `artifacts/atlas-rnafm/scaling-v1/`:

- `source-loss-epochs.png`, `source-loss-time.png`: all actual source histories.
- `target-loss-{lora_chemistry,frozen_chemistry}.png` and corresponding `-time.png`:
  actual target training/validation histories, without fabricated later epochs.
- `target-scaling-comparison.png`: fixed three-epoch target protocol.
- `target-scaling-selected-target.png`: validation-selected inner-fit protocol.
- `target-summary.csv`, `target-results.csv`, `source-summary.csv`, `report.json`:
  complete metrics and per-condition results.
- `paired-comparisons.json`, `model-and-size-comparisons.json`: paired descriptive
  source-duration, target-protocol, source-budget and model differences.
- `partitions.json`, per-fit `history.json` / `receipt.json`, checkpoint files and
  `audit.json`: identities, label accounting, actual durations and integrity checks.
- `provenance/`: exact profile/full-run source bytes verified against their recorded
  hashes, cohort/encoder identity, and analysis receipts. The model training source
  hash is unchanged across invocations. Cohort SHA-256:
  `bbc3edbef73f2f2b926cd1fcc63946f16d52238f994e99c620be9f756522165d`.

The initial profile loaded a label-bearing table before restricting its fitting
Series; no reserved outcomes reached fitting, stopping or scoring. The full runner
uses filtered endpoint reads. That implementation difference is preserved in the
archived source hashes. Fixed-target console logs from the running invocation print
`validation 0` as a placeholder where no validation was used; structured histories
correctly omit that metric, and no plot treats the placeholder as an observation.
The current script displays `None` instead.

The immutable published 136-record snapshot remains unchanged. Later local commits
and this completed report require integrator review; the research task does not
merge or push them automatically. All checkpoints and generated run artifacts remain
outside Git. See [SCALING-STATUS.md](SCALING-STATUS.md) for execution history and
[SCALING-METHODS.md](SCALING-METHODS.md) for rerun commands and environment limits.
