# OligoAL: RL framework decisions and parallel research context

Recorded **November 14, 2026, 16:59 EST / 21:59 UTC**.
Purpose: preserve the latest design discussion, completed fine-tuning evidence,
implementation boundaries and continuation steps. This describes the proposed
first ASO RL experiment, not an already implemented integrated system. It supplements
[the environment handoff](../aso-rl-environment-context.md) and
[shared research infrastructure](../research-infrastructure.md).

## Research question and scope

Can a learned policy improve constrained ASO search under fixed predictive models,
compared with conventional optimizers at matched computational evaluation budgets,
and do improvements survive independent evaluation?

The environment simulates predictor responses, not biological responses. The first
experiment is molecular design through target-site selection: with fixed length and
chemistry, a target window determines its complementary ASO. It is not yet a general
sequence-and-chemistry generator or an experimental-selection agent. Frozen-model
optimization precedes active-learning updates and synthetic-augmentation studies.

The user explicitly wants a broader program, with independent tracks for prediction
and target transfer, experimental selection, robustness/augmentation, and molecular
design. The eventual loop is design → select measurements → measure → update
predictors → design again. Better prediction, higher surrogate reward, more useful
measurements and better biological candidates are distinct claims. Each connection
needs evidence; the full loop has not been validated.

## Completed fine-tuning evidence

Atlas scaling completed 240 fits/calibrations and 216 deferred target evaluations,
zero failures, in 100.6 minutes. No training process remains. Source budgets were
2,869 and 4,781 labels (3% and 5% of 95,638 eligible source-training rows), including
internal validation. Three paired seeds used F7, STAT3 and NLRP3 with 200 labels per
target. Validation-selected source and fixed three-epoch target adaptation gave:

| Model | 3% source target RMSE | 5% source target RMSE |
| --- | ---: | ---: |
| LoRA RNA-FM + chemistry | 22.391 | 22.340 |
| Frozen RNA-FM + chemistry | 20.893 | 21.208 |
| Matched source Ridge + target offset | 19.883 | 19.656 |

Lower is better. LoRA lost to matched Ridge on every target-level average at both
budgets, including the separate validation-selected target-duration protocol.
Target-only XGBoost reached 19.366 and target-only Ridge 19.626 without source labels.
Extra data and epochs did not establish a LoRA advantage for this recipe. Training
loss often continued falling while validation worsened. Seven reserved targets
remain unscored.

Limits: three development targets; source-validation repartitioning changed inner
fitting composition across budgets; a small internal compound overlap was audited;
target duration selection changed gradient-row counts. This does not disprove all
FM adaptation, establish zero-label transfer, or validate molecular-design rewards.

Full report: `codex/atlas-lora-scaling@f197d79`,
`docs/research/atlas-rnafm/SCALING-RESULTS.md`. Main does not contain that model
implementation. The earlier published snapshot `1b3fc1e` records 136 completed fits;
the user's current publication request includes five subsequent study commits.

## High-level technical implementation

| Component | First design |
| --- | --- |
| Target | Versioned transcript, sequence hash, fixed coordinate conventions |
| Chemistry | Fixed 19-mer PS/2′-MOE gapmer; fixed assay conditions |
| Candidate | Complementary sequence, full HELM, coordinates, immutable identity |
| Actions | Bounded left/right target-window shifts and STOP |
| Observation | Candidate/local target context, position, scores, applicability, steps left |
| Scorer | Frozen versioned endpoint adapters shared by every optimizer |
| Objective | One selected efficacy output mapped to a fixed reference percentile |
| Screening | Applicable validated endpoint/domain constraints; unknown stays unknown |
| Policy | Small feed-forward MaskablePPO with reproducible masked evaluation |
| Baselines | Unchanged start, random, greedy, genetic, exhaustive where feasible |
| Outputs | Candidate archive, scoring ledger, optimization curves, external evaluation |

Separate five modules:

1. `ASODesignSpace`: candidate construction, legal transitions and complementarity.
2. `EndpointRegistry` / `RewardAdapter`: trusted bundles, applicability and scores.
3. `ASOEnv`: Gymnasium reset/step, masks, observations, termination and budgets.
4. Optimizer adapters: the same space and scoring rules for PPO and conventional search.
5. Evaluator/artifact writer: final measured outcomes unavailable to optimization.

Keep model fitting and label access outside the environment. Score records retain
endpoint/model IDs, raw values/units/direction, supported context, uncertainty type,
normalization identity, applicability/rejection reasons and provenance. Tensor
placeholders require availability flags; archives retain nulls and reason codes.
Chemical edits or variable length require verified predictor coverage before entry.

## Reward and endpoint roles

Use one validated efficacy objective plus applicable, validated screening rules,
instead of immediately adding every endpoint into an arbitrary weighted sum:

```text
non-terminal reward = 0
terminal reward = -1 if a required eligibility rule fails
terminal reward = fixed_reference_percentile(predicted_efficacy) otherwise
```

Accepted utility is in [0, 1]. The fixed reference is training-derived and matches
chemistry/assay context. Preserve raw predictions before transformation. Optional
missing endpoints do not automatically reject candidates; missing required ones make
them unassessable for that profile. Model-load or systematic inference failures stop
the run rather than generating thousands of artificial rejection examples.

Initial MOE endpoint roles:

- Primary efficacy: a selected Atlas predictor; classical models are currently
  stronger references than the tested LoRA recipe.
- ASOptimizer: advisory cross-check unless matched validation supports combining
  estimates. Avoid double-counting correlated efficacy outputs.
- MOE neurotoxicity: advisory until a cutoff is validated against a defined measured
  adverse outcome, missed-case rate and candidate retention.
- TLR7/8: not applicable to unsupported MOE chemistry; a separate compatible
  chemistry/assay profile needs its own validation.
- Hepatotoxicity/other heads: integrate only with an available trusted artifact and
  verified endpoint/domain contract. A dataset's existence does not imply a model.

Passing predicted screens is not proof of safety. GP latent standard deviation is
not automatically a calibrated biological error bar. Disagreement starts as a
diagnostic; penalties require comparable endpoints and validation evidence.

## Advanced methodological justifications

### 1. Distinguish optimization from independent quality

Higher optimized reward establishes better search of that surrogate. Agreement
with a separate evaluator adds computational support. Better strictly held-out
measured compound–assay outcomes provide retrospective experimental support. Novel
designs usually lack those measurements and remain hypotheses.

Do not use the final evaluator for reward tuning, PPO checkpoint choice or repeated
design revisions. Different model architectures using the same biased source data
have limited independence. A pseudo-labeling teacher cannot be the sole evaluator
of its own augmented model. Surrogate exploitation is an established problem in
offline optimization: [Conservative Objective Models, ICML 2021](https://proceedings.mlr.press/v139/trabucco21a.html).

### 2. Match model selection to deployment

Declare source-only inference on a new target versus adaptation with a target-label
budget. Our completed comparisons used 200 target labels and do not establish
zero-label deployment. Classical winners still require model-bundle and candidate-
ranking validation. LoRA remains interchangeable, not a prerequisite for the gym.

### 3. Separate legality from model judgments

Masks enforce deterministic validity: transcript bounds, constructable chemistry,
allowed templates and target recognition. Predicted low efficacy/toxicity generally
belongs in scoring, allowing movement through poor intermediate candidates. Do not
score all neighbors for action masks without counting those calls. Use mask-aware
evaluation functions and callbacks as required by the
[MaskablePPO documentation](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html).
Pin the actual runtime version; no new RL dependency was installed in this work.

### 4. Align return with the finite-horizon objective

Discounting variable-length terminal rewards can favor particular stopping times
and make delaying a negative reward attractive. For final candidate quality within
a bounded horizon, an undiscounted return (`gamma=1`) is a reasonable starting
specification to verify, not a tuned finding. Observe remaining steps and distinguish
normal termination from external truncation. Keep shaping as a separately budgeted
later ablation; account for its extra scoring costs.

### 5. Account for the full cost

Log total requests, unique candidate-context scores, per-head calls, batching,
policy training/validation costs, fresh-target inference and wall time. Charge reset
and intermediate scores despite zero intermediate reward. Cache keys include
chemistry, target context, assay profile and scorer version. Report total-cost and
deployment-after-training performance separately. Any amortized advantage across
new targets must be demonstrated; precomputed oracle tables do not erase costs.

### 6. Include enumeration

Fixed chemistry and length give a finite reachable set of transcript windows.
Enumeration defines the exact surrogate optimum where feasible, not the biological
optimum. Ask whether PPO approaches it with fewer calls and transfers that efficiency
to held-out targets. If simple search suffices, report it. Do not enlarge chemistry
space merely to manufacture a need for RL.

### 7. Freeze evaluation hierarchy and metrics

Keep predictor-development, policy-training, policy-validation and final-evaluation
manifests distinct. Predictor/policy training overlap can be intentional; final
labels must never influence either selection process. Audit cross-source patent,
compound and sequence overlap, recording unresolved identities.

Pair targets, starts, allowed design regions and budgets. Use multiple optimizer
seeds and target-level summaries: seeds are not independent biological targets.
Predeclare two result families:

- Optimization: best eligible utility versus budget, feasible-candidate rate,
  shortlist diversity and regret against enumeration.
- External quality: measured shortlist enrichment for exact recorded assays,
  separate-evaluator performance, disagreement and distribution shift.

Report empty feasible sets, undefined metrics and unavailable endpoints. Freeze
whether reporting uses terminal candidates or a best-visited archive, and apply
the same convention to every optimizer.

## Acceptance sequence and remaining choices

1. A synthetic ASO fixture with known optimum, transitions and mask tests.
2. Real HELM parsing (including methylcytosine aliases), portable model bundles and
   deterministic inference parity with the original model owner.
3. A frozen assay/scorer profile with validated coverage and required screens.
4. Identical scoring across panel CLI, environment transitions and baselines.
5. Train/save/reload a masked policy and compare optimizers at matched costs.
6. Locked independent evaluation and a replayable candidate archive.

Still to freeze: source-only versus target-adapted setting; supported assay context;
trusted artifact; screening event/cutoff/coverage; transcript/group manifests;
action/horizon bounds; model-call budget; shortlist size; seeds and primary paired
contrast. No cutoff or reward weight is validated by this document. Acquisition,
predictor updates and augmentation remain subsequent independent experiments.

## Shared non-RL infrastructure and publication

New implementation: `src/oligo_engine/research/`,
`configs/research/studies.toml`, `tests/test_research_infrastructure.py`.
The catalog distinguishes completed studies, infrastructure and plans. The planner
fixes validation groups once, preserves nested fitting and validation prefixes,
counts validation labels, rejects excluded IDs and label columns, and refuses to
overwrite plans. Dataset adapters still own valid group construction. This is not
an acquisition policy or generic training scheduler.

Verified: 158 core tests including 12 new cases; Ruff lint/format on 109 files;
synthetic CLI allocations at budgets 10/20/50/100. No new scientific training ran.
See [commands and limits](../research-infrastructure.md).

The user requests publishing all outstanding work as organized commits: historical
Atlas plan/handoff and progress context, shared infrastructure/tests, this framework
context, and five completed-study commits on `codex/atlas-lora-scaling`. Preserve
branch separation; do not merge the Atlas implementation into main automatically.
Generated plans, histories, plots, weights and PDFs stay outside Git. Earlier
timestamped snapshots remain historical records, not current status pages.
