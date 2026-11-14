# Published best efficacy models: reproduction protocol

User-confirmed scope, November 14, 2026: reproduce the published best models on
**all efficacy datasets**, not just one Huesken classical-model configuration.
Primary comparison uses the published nucleobase split. Random-split baselines,
toxicity/immunomodulation models and exhaustive hyperparameter grids are outside
this defined scope. ASO, siRNA and shRNA results remain separate assays/modalities.

## Frozen configurations

`configs/gate1-efficacy/manifest.json` records the source CSV hash, every selected
configuration and its hash, and all five published reference values. Selection is
the highest released mean test Pearson among complete five-repeat nucleobase
configurations, with deterministic tie-breaking. No local result informs selection.
The seven model/configuration selections were frozen before local executions.

| Dataset | Modality | Full rows | Published winning model | Reference mean r |
| --- | --- | ---: | --- | ---: |
| Huesken | siRNA | 2,431 | CNN, one-hot base/sugar/phosphate | 0.630914 |
| Ichihara | siRNA | 419 | MLP, one-hot base | 0.570440 |
| Shmushkovich | siRNA | 356 | RF, 1/2-mer counts | 0.422405 |
| siRNAmod | siRNA | 907 | RF, one-hot base/sugar/phosphate | 0.528565 |
| OpenASO | ASO | 3,913 | Ridge linear model, 1/2-mer counts | 0.290633 |
| ASOptimizer | ASO | 32,602 | CNN, one-hot base/sugar/phosphate | 0.479175 |
| Sherwood | shRNA | 291,551 | XGBoost, one-hot base/sugar/phosphate | 0.900831 |

Each uses all released observations without row caps and five declared seeds,
0–4. Execute the actual pinned downloader/split/featurizer/model-factory helpers.
Use the original source labels and per-dataset scale; no modality pooling or
post-hoc transformation. Record requested and effective estimator arguments,
including the upstream RF depth-filter behavior. Compare each mean to its own
reference under the unchanged absolute 0.03 tolerance. Preserve every result,
including numerical mismatches, undefined correlations and execution failures.

Neural training uses upstream defaults: 100 maximum epochs, batch size 32, Adam
learning rate 0.001, weight decay 0.01, and early stopping on training-internal
validation loss with patience 5. The source creates that 20% validation subset
with random_state=42, wholly within the outer training pool. Torch is seeded with
the declared per-run seed. CPU/device selection and deterministic execution are
declared; checkpoint files, logging and progress bars are disabled. The source
predicts with the final in-memory model, without loading a saved best checkpoint.

The optional performance cache memoizes only native raw HELM-to-monomer parsing,
keyed by HELM and requested strands, and returns deep copies. It does not cache
fitted encoders, normalization, models or labels. Training dictionaries are still
fit separately on each outer training partition. A native-library equivalence
check verifies exact k-mer/one-hot matrices and mutation isolation; its local
artifact is `artifacts/gate1-native-cache-validation-20261114.json`. Cache settings
and hit/miss counts are recorded. No upstream source files are modified.

## Execution and interpretation

Run with the audited upstream Python environment:

```sh
poetry run python -m oligo_engine.efficacy_reproduction \
  --checkout /tmp/oligoal-upstream-97f5b9f \
  --configs configs/gate1-efficacy \
  --python "$UPSTREAM_PYTHON" \
  --output artifacts/gate1-efficacy-new
```

Two isolated worker processes run dataset campaigns. Logs and per-seed progress
survive failures; completed JSON artifacts include all split IDs, effective model
settings, prediction hashes, metrics, environment/package inventory and runtime.
`suite.json` distinguishes execution completion from numerical agreement. No
failed dataset is omitted and no favorable seed is substituted.

The configurations can be regenerated from the audited source into a new directory
using `--freeze`; existing frozen configurations and output directories are never
overwritten. Source-script/code revisions and dataset hashes must remain explicit.

Even numerical agreement on every dataset is not recovery of historical bitwise
results: original per-run RNG states, split manifests and hardware/environment
records remain unavailable. Report protocol execution, numerical reproduction and
historical identity separately. No active-learning policy is trained or evaluated
by these baseline runs.

## Source and discrepancy checks

Historical comparison against `c85846d1f48a6d507e75644f9e510d7e8f217712`
(the benchmark-update revision) finds identical Git blob IDs for all seven efficacy
CSV/metadata pairs. AST comparison finds unchanged relevant model constructors,
`LightningModel.fit`, OneHotEncoder, KMersCounts, raw monomer parsing,
nucleobase_split, and benchmark preparation helpers. The historical neural
prediction method differs: it predicts in one batch without explicitly entering
evaluation mode; the pinned method uses batches, evaluation mode and no-grad.
This compares public source versions; it does not recover the original runtime.

An unchanged Ichihara seed-0 diagnostic retrains the frozen winning MLP and exactly
matches the completed run's native prediction hash and 66 training epochs. Applying
the historical and current prediction functions to that same trained model gives
identical outputs (maximum absolute difference 0), both with Pearson 0.423602319.
The winning MLP uses dropout=0 and no batch normalization. This rules out that
inference-code change for this diagnostic; it does not establish the cause of the
published mean discrepancy. No hyperparameters or seed schedules were changed.

Local evidence: `artifacts/gate1-source-history-20261114.json` and
`artifacts/gate1-ichihara-inference-diagnostic-20261114.json`. Original per-run split
IDs/RNG states remain unavailable. Variation across new cluster holdouts and
selection of the best published configuration are possible contributors, not
demonstrated explanations. Do not label a numerical mismatch as a software failure
or resolve it by choosing favorable test splits.

## Results

All **35 full-data fits** completed: seven published winning configurations,
five declared repeats each. The audit confirms complete row coverage and unique,
disjoint train/test IDs in every repeat, matching frozen configs, and identical
local source hashes and installed package inventories across datasets.

| Dataset | Model | Published r | Local mean r | Local sample SD | Difference | Within 0.03? |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| ASOptimizer | CNN | 0.479175 | 0.435097 | 0.050884 | -0.044078 | No |
| Huesken | CNN | 0.630914 | 0.609600 | 0.044330 | -0.021314 | Yes |
| Ichihara | MLP | 0.570440 | 0.422582 | 0.071828 | -0.147858 | No |
| OpenASO | LinearModel | 0.290633 | 0.246086 | 0.099553 | -0.044547 | No |
| Sherwood | XGBoostModel | 0.900831 | 0.903768 | 0.012934 | 0.002937 | Yes |
| Shmushkovich | RandomForestModel | 0.422405 | 0.394235 | 0.109041 | -0.028170 | Yes |
| siRNAmod | RandomForestModel | 0.528565 | 0.508360 | 0.102802 | -0.020205 | Yes |

**Four of seven datasets meet the unchanged 0.03 numerical tolerance.** Huesken's
winning CNN now agrees within that criterion; the three unresolved comparisons
are Ichihara (gap -0.147858), OpenASO (-0.044547), and ASOptimizer (-0.044078).
Do not describe the seven-dataset study as fully numerically reproduced.
These are per-dataset comparisons, not a pooled performance or significance test.
Original test folds are unknown, so the local/published scores are not paired.

Execution artifacts: `artifacts/gate1-efficacy-20261114-fixed-env/`. Validated report:
`artifacts/gate1-efficacy-report-20261114/`. Exact source/config snapshot:
`artifacts/gate1-efficacy-source-20261114/`; every source hash matches the executed
runs. Generated artifacts remain ignored; the method, configs and results summary
are repository documentation.

The initial `artifacts/gate1-efficacy-20261114/` launch failed before any training:
resolving the virtualenv interpreter symlink invoked the base Python without
OligoGym. That launcher bug was corrected, regression-tested, and all seven jobs
were restarted with unchanged scientific configurations in the preserved output
folder above. No metrics from the failed launch enter this comparison.

Regenerate the final report after a fresh full run:

```sh
poetry run python scripts/report_efficacy_reproduction.py \
  --suite artifacts/gate1-efficacy-new \
  --configs configs/gate1-efficacy \
  --output artifacts/gate1-efficacy-new-report
```

The remaining evidence needed for historical reconciliation is the original
per-run split indices/RNG state, effective runtime settings and hardware/environment.
The source/data checks and fixed-seed inference diagnostic above have not explained
the three numerical discrepancies. No seed search, tolerance change or model tuning
was used to turn them into matches.

Final verification: **88 tests pass**, including frozen selection, full-row/seed
auditing, parameter traces, cache isolation and interpreter-path regression checks.
Ruff lint/format and Git whitespace checks pass. The final clean pinned-upstream
audit passes; source files match all seven completed run artifacts and the archived
implementation. These study updates and generated reports are local changes.

## Bounded follow-up: basic discrepancy analysis

The subsequent quick analysis supports split difficulty and published winner
selection as the strongest working explanation, without establishing the exact
historical cause or changing the numerical acceptance criterion.

- Released metrics confirm that nominal folds are not common held-out sets across
  configurations. Under the released metric definitions,
  `SD(y_test) = RMSE / sqrt(1 - R2)`. For Ichihara's nominal fold 0, inferred target
  SD ranges from 26.104 to 36.607 across configurations, far beyond rounding error.
  This agrees with the training script's unseeded per-configuration resplitting.
  Published configuration selection therefore mixes model and holdout variation.
- A fixed Ichihara outer split (the existing seed 0, unchanged encoder and inner
  validation) with predeclared training seeds 0, 1, 2 gives test r=0.423602,
  0.424437, 0.426753. Full outer-training r is 0.652736, 0.654110, 0.644737 versus
  the published configuration's mean training r=0.625524. The original seed-0
  prediction hash repeats exactly. These observations argue against inadequate
  fitting or initialization being the main explanation on this particular split;
  they do not identify the unknown historical split or exclude all runtime effects.
- OpenASO's mean RMSE is 0.264164 versus 0.257574 published (2.56% higher), and
  ASOptimizer's is 26.320935 versus 25.789260 (2.06% higher). Their Pearson gaps
  (~0.044) are smaller than their observed per-repeat SDs. This describes variation,
  not a significance or equivalence test.
- The published winning Ichihara score is the maximum of 64 complete MLP
  configurations; ASOptimizer's is the maximum of 40 CNN configurations. Selecting
  maxima on varying test splits can produce optimistic reference scores. The size
  of that contribution is not determined here.

Evidence is preserved in `artifacts/gate1-basic-cause-analysis-20261114.json` and
`artifacts/gate1-ichihara-fixed-split-training-analysis-20261114.json`. All three
diagnostic training seeds are reported; none replaces a frozen benchmark repeat.
No core code, winning configuration, seed schedule or tolerance changed. Huesken
remains a numerically reproduced primary benchmark; the three other discrepancies
remain explicitly unresolved rather than being promoted to reproduction passes.
