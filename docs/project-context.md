# Project context

November 15 final adaptive-dose extension: the user-authorized
[per-concentration experiment](adaptive-dose-response-experiment.md) ran on 93
development and 240 experiment-held-out assessment panels, with settings sealed
before assessment access. At apparent absolute IC50 <=500 nM, fixed early stopping
used 1.592 measurements/ASO, decision-aware Bayesian selection 1.683 and
information gain 2.817, versus 4.400 for the full grid. Decision-aware selection
made one false positive and two false negatives; fixed and information gain made
none against resolved references. All early-stop methods classified the sole
reference-unresolved panel, failing the prespecified unresolved-assertion check.
TMPRSS6 showed a descriptive target-specific reduction, not a general advantage.
No PPO or further tuning ran. The integrated suite passed 330 tests. See Section 9
of the [consolidated results](ASO_EXPERIMENTS_CONSOLIDATED_RESULTS.md).

November 15 completed follow-ups and later handoff: the
[new recorded-panel IC50 pilot](ic50-qwen-from-scratch.md) executed 72 arms and
108 actual local Qwen2.5-3B choices. At its frozen 100 nM threshold, bound credit
raised F7 new-hit means from 1.667 to 2.000 for Qwen, random and GC-bin greedy;
Qwen's acquisition gain under a common evaluator was zero. STAT3/NLRP3 had no
qualifying panels at that cutoff. A separate
[planning study](value-of-planning-experiment.md) solved 162 four-candidate model
settings exactly: greedy was optimal in 108, one-step rollout in 150. Three PPO
training seeds did not beat greedy. These are model-based diagnostic results.
The [evaluation-data audit](molecular-evaluation-data-expansion.md) preserves all
304 reserved risk records, with 226 surviving a stricter full-release linkage
sensitivity; it also identifies 1,008 KCNQ2 and 463 PTBP1 records for retrospective
transfer evaluation, plus eight external records with incomplete assay metadata.
Those leads are not newly certified independent validation cohorts.

The subsequently supplied [Harrison handoff](experimental-selection-handoff-assessment.md)
explains that original experimental-selection V3/Qwen3 runs exist in an unpushed
local checkout unavailable here. Its 500 nM endpoint, mandatory screen gate,
costs and source Ridge priors differ from the new pilot and planning model.
Its NLRP3 split and KCNQ2 training exposure also limit independent-cohort claims;
exact historical membership remains unavailable. Preserve earlier results and
the new pilot's frozen protocol. Integrated lint, format, import and 318 core
tests passed; generated data, model weights and run artifacts remain ignored.
Earlier follow-up entries below describe the evidence available at their time.

November 15 compatible-data and IC50 follow-ups: two user-requested agents checked
additional compatible measured data and prepared a censored-potency comparison.
The [corrected compatible-data audit](molecular-compatible-data-experiment.md)
recovers 427 additional protected IDs from 244 provenance receipts and the newly
published experimental-selection manifest. Near-sequence/patent links plus a
conservative cross-source quarantine leave 298 rows for one active pattern at
HepG2/4,000 nM/24 h, all in one MECP2 component; no independent fitting/assessment
cohort is certified and no new fit ran. The current 4,500 nM context still has no
verified exact pattern matches. The [IC50 work](censored-ic50-policy-experiment.md)
implements and tests point/bound/unknown adjudication, but runs only synthetic
checks: the accessible experimental-selection branches use single-dose inhibition
and do not contain the claimed completed potency V3/Qwen runs. The user does not
know their location and authorized another remote check; fetching all remote
branches found no newer implementation. Origin/main is 046ef5f; no merge
or active-model/profile change occurred. Earlier Atlas reserved targets have
documented later experimental-selection exposure; preserve their existing roles
without describing them as globally untouched.
Integrated follow-up checks passed lint, formatting, imports and all 282 core tests.

November 15 scientific experiments: the requested eight-target table now includes
new APOC3/ANGPTL3 evaluations under frozen v3 policies (60 runs, 480 requests,
960 endpoint-head calls; all budgets filled without duplicate queries). Three
agents executed full-release metadata applicability, original-360-run attribution
and exposure/generalization audits. See the [integrated results and experiment
sequence](molecular-scientific-experiments.md). Other assay contexts contain exact
chemistry support, but preserved data roles prevent pooling it into a qualified
full-profile cohort. PPO's incremental benefit remains mixed and no independent
final groups are certified. No new fitting or measured-outcome access occurred;
new targets are explicitly development-exposed, not final confirmation.

November 15 data-scaling investigation: two user-requested agents audited measured
predictor data and policy pretraining/PPO experience. The [integrated plan](molecular-data-scaling-plan.md)
records that policy pretraining already covers 36% of its small training catalog,
while the active efficacy development cohort uses about 2% of broadly eligible
Atlas rows. A metadata-only full-release check found no verified exact matches to
the current efficacy chemistry/context among parsable rows. Existing larger
classical checkpoints and a completed prior negative neural scaling study were
located; historical split overlap prevents a clean size-curve interpretation.
No new fitting or outcome reads occurred. The requested Git fetch and pull of
origin/main found HEAD already current at 62f68d9; local changes were preserved.

November 15 policy revision: the user authorized addressing the corrected PPO's
weak optimizer performance. The optional `candidate-v3` policy shares sequence/
chemistry scoring across absolute sites, supports return-preserving forced-step
collapse and costed training-only surrogate pretraining. The broader fixed study
uses six training genes, two validation genes and four development evaluation
genes. See [implementation and protocol](molecular-policy-repair.md). These changes
do not qualify the scientific predictors or establish optimizer superiority.
The completed 360-run diagnostic has higher full-pipeline means than random and
greedy on DGAT2, CFB, FGFR4 and TTR; F9 slightly favors greedy, and every legal F12
candidate fails the unchanged diagnostic risk screen. Pretrained no-PPO controls
show that PPO's incremental benefit is not established. Tests pass 230 core and
ten optional RL checks. See the same report for costs, roles and paired results.

Latest correction: the user requested diagnosis and repair of PPO's no-COMMIT
failure. The default complete-proposal decoder now prevents editor cycles and
cached-parent recommits, and requires one new proposal before campaign STOP.
The three-seed matched rerun completes seven new designs per eight-request
evaluation; the molecular reward and screening bounds are unchanged. See
[molecular-construction-fix.md](molecular-construction-fix.md). Legacy artifacts
remain replayable explicitly. Full scientific applicability/independent evaluation
remain unqualified; historical entries below retain their original scope.

November 14, 21:00 EST: the consolidated replacement design is
[FINAL_MOLECULAR_DESIGN_RL_SPEC.md](FINAL_MOLECULAR_DESIGN_RL_SPEC.md). It defines
chemistry-aware construction, real checkpoint integration, context/history-aware
observations, archive-aligned rewards, matched-query optimizer evaluation and
independent evidence gates. It supersedes conflicting old RL implementation
choices; the replacement is a specification, not implemented functionality.

November 14, 20:38 EST: the user retired the original target-window RL scaffold.
Its environment, policy training, action space, fixture/search runners, configs,
RL dependencies and CI job are removed. Shared inference/chemistry and the
independent prediction, acquisition and robustness work remain. There is no
replacement RL environment yet. See [removal details](updates/2026-11-14-2038-est-rl-scaffold-retirement.md).
Earlier implementation statements below are historical, not current capabilities.

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

Latest user-authorized replacement: the retired RL scaffold is replaced by the
molecular construction package documented in
[molecular-design-implementation.md](molecular-design-implementation.md), following
FINAL_MOLECULAR_DESIGN_RL_SPEC.md. Grammar, frozen scoring, PPO and controls,
resume, panels and local UI run end to end. A separate development mouse-risk head
is available; expanded efficacy support and independent final evidence remain
blocked. Earlier statements that no app/design agent exists are historical.
Synthetic and bounded real diagnostics are unfavorable to PPO; the full scientific
system remains unqualified. Gate 1 is unchanged. No new data, weights or run
artifacts were published.
