# Project context

November 14, 20:29 EST clarification: the robustness CLI fit fresh RF/Ridge audit
models, not the existing GP/LoRA/Atlas checkpoints. Its exact fitting-context gate
excluded all four final DGAT2 assay tuples (2,536 records), so the split and gate
were incompatible. This should have been a metadata preflight stop, not a measured
robustness conclusion. See the [diagnosis and corrective plan](updates/2026-11-14-2029-est-robustness-zero-coverage-correction.md).
No replacement experiment or gate change is implemented by that update.

Local predictor robustness implementation (November 14): after syncing main at
`6b6838b`, added four-way grouped audits, frozen RF/Ridge adapters, perturbations,
domain/uncertainty diagnostics, calibration/abstention and sealed pool search.
The known synthetic exploitation fixture works. The frozen ASOptimizer held-out
target has zero admitted assay-context coverage; accuracy and a real guardrail
remain undefined. Checks pass 212 core tests and 3 optional robustness science
tests. See [implementation and scope](predictor-robustness-implementation.md).
No augmentation, new biological validation or Gate 1 closure is claimed.

Latest ASO checkpoint (November 14, 19:10 EST): the ordered supported-profile study
is complete. A separate exact 20-mer MOE efficacy bundle is integrated, with
source-only fitting and positive recorded-assay top-20 ranking on two development
targets. Three real-surrogate PPO runs showed no final-window advantage; the
validation gate prevented larger runs. Safety and generated-molecule efficacy
remain unvalidated. See [the full result](supported-aso-results-2026-11-14.md).
The entries below preserve earlier project decisions and historical checkpoints.

Current direction: November 13, 2026 revised implementation handoff, which supersedes
conflicting claims in the November 11 v5 plan. Canonical specification:
[SPEC.md](SPEC.md), [EVALUATION.md](EVALUATION.md), [interfaces.md](interfaces.md).

Question: can sequential acquisition improve out-of-sample siRNA efficacy prediction
using fewer measured labels than random acquisition? The scientific thesis is not
established under a benchmark-comparable protocol here.
The core is a reproducible select/reveal/retrain/evaluate loop with matched budgets,
fixed evaluation rows and a full-training-pool reference. Negative results count.
Full-data diagnostic comparisons are now complete; see full-experiment-protocol.md.

Default: independent Huesken siRNA efficacy benchmark. ASO activity/safety models,
biological design, RL and a product surface are separate optional workstreams.
The accepted November 14 reporting focus is efficacy: Huesken first, other siRNA
efficacy datasets as replications, and ASO efficacy as separate extensions. Existing
toxicity and immunomodulation diagnostics remain auxiliary. The immediate priority
is trustworthy baseline reproduction before further acquisition-method expansion.
Incompatible siRNA and ASO datasets must not form a shared safety/efficacy claim.
This project neither reproduces Creyon's engine nor establishes proprietary data
unnecessary. Novelty remains provisional. Proposed molecules are hypotheses.

Implemented: typed contracts, protected training oracle, synthetic replay, source audit,
and dataset-specific baseline reruns. The November 14 user instruction additionally
authorizes all 12 released datasets in the repository and measured diagnostic replay
across them. Catalog integrity, duplicate-aware local splits, adaptive budgets,
random/uncertainty policies and isolated artifacts now support every dataset. Full
source rows are validated; sample-capped diagnostic runs are engineering evidence,
not scientific generalization. Full-data five-seed matrices now total 180 campaigns
with mixed acquisition effects; the benchmark reproduction gate remains open. No app
or design agent is implemented. See dataset-pipelines.md for current commands/limits.
See [upstream verification](upstream-verification.md) for actual checks and blockers.
The new [Gate 1 study](gate1-reproducibility-study.md) corrects an RF argument-filter
mismatch and establishes exact local repeatability of the native-helper protocol.
Its mean r=0.559769 still misses the published 0.591037 reference by 0.031268;
historical reproduction is unresolved. The acquisition pipeline is unchanged.
The subsequent user-confirmed scope is published best models on all seven efficacy
datasets, evaluated on the official nucleobase split. All 35 full-data fits complete;
four of seven meet the unchanged 0.03 tolerance, including the Huesken CNN
(0.609600 vs 0.630914). Ichihara, OpenASO and ASOptimizer remain discrepant. See
[efficacy reproduction](gate1-efficacy-reproduction.md). No full numerical or exact
historical reproduction is claimed.

The user now explicitly authorizes a delegated Huesken CNN random/diversity
label-efficiency pilot. See huesken-learning-protocol.md and
configs/huesken-learning.toml for settings frozen before outcomes. A subagent owns
only new implementation/test files; the integrator owns shared metadata/contracts.
This advances the core sequential efficacy benchmark with scoped diagnostic
provenance. Expanded Gate 1 is not silently closed; no new acquisition finding is
claimed while the study is in progress.

Subsequent status: the five-seed CNN pilot completed with no consistent diversity
advantage (paired AULC -0.0150 +/-0.0398 sample SD). The user has now authorized
development of the four-policy GP study in active-learning-development.md. Its
initial-only kernel selection, hybrid acquisition, explicit budget schedule and
paired reporting are implemented; the smoke check passed. The five-seed development
matrix completed: hybrid minus random AULC +0.00535 +/-0.02079 SD; mean
first-threshold label savings22.7% +/-28.0 percentage points across five seeds.
These variable development results require further evaluation. The incoming two-baseline
30-seed Gate 1 reassessment does not resolve the expanded seven-dataset requirement.

RNA-FM branch integrated: verified frozen embeddings, random-encoder control,
five-seed Ridge prediction and fixed-predictor geometry studies. Frozen features
underperformed one-hot; geometry showed no consistent advantage. A bounded real
LoRA proof completed; the multi-seed LoRA/classical comparison is still running
in its isolated checkout. See rnafm-study.md and rnafm-lora-comparison.md.

Subsequent user-authorized ASO environment execution is documented in
[aso-rl-execution.md](aso-rl-execution.md). The existing reward-adapter branch now
has offline MOE target-site search, a real-candidate frozen inference boundary,
budgeted Gymnasium transitions, conventional search and optional MaskablePPO. The
synthetic fixture reaches its known optimum and reloads deterministically; a tighter
budget comparison is unfavorable to PPO. Final local checks pass 186 core tests and
5 separate optional RL tests on Python 3.11. These are engineering results. Real
Atlas artifact parity, assay/transcript profiles, screening validation and the
locked real benchmark remain pending; expanded Gate 1 and endpoint separation are
unchanged. No source datasets, model weights or generated artifacts were modified
or published by this implementation.
