# Predictor robustness: implementation design specification

Version 0.1, November 14, 2026. Status: proposed implementation contract.
This request defines the design; no robustness implementation, training campaign,
new experimental result or publication is implied by this document.

Subsequent user-authorized local implementation is documented in
[predictor-robustness-implementation.md](predictor-robustness-implementation.md).
It is based on main at `6b6838b`, including its supported 20-mer profile, and
distinguishes delivered components, actual diagnostics and remaining study scope.
The original design snapshot below is preserved.

## 1. Purpose and decisions the system must support

Determine where endpoint predictions lose measured accuracy, whether diagnostics
identify that loss, and whether optimization preferentially selects model errors.
Produce evidence for applicability/abstention rules and independently tested
shortlists. A negative finding, an ineffective diagnostic or insufficient data is a
valid result. Prediction robustness and resistance to optimization are distinct.

Questions:

1. How do accuracy and ranking change on excluded targets, patent/compound groups
   and supported assay-context groups?
2. Which controlled changes produce unstable predictions or representation bugs?
3. Do training-domain distance, named uncertainty or comparable-model disagreement
   predict actual held-out error and support useful abstention?
4. As search increases surrogate reward, do exact measured outcomes or an independent
   evaluator improve, stagnate or worsen?
5. Can a validation-selected guardrail reduce overestimation while retaining useful
   candidates, relative to equally budgeted unguarded search?

Applicable project contracts: [SPEC](SPEC.md), [EVALUATION](EVALUATION.md),
[interfaces](interfaces.md), [shared research infrastructure](research-infrastructure.md)
and [ASO environment execution](aso-rl-execution.md). This is a separate diagnostic
workstream while expanded Gate 1 remains open. No clinical safety, therapeutic
efficacy, calibrated uncertainty, label savings or robust-design claim follows
automatically. Keep every endpoint, modality, unit and assay contract separate.

## 2. Scope and implementation boundaries

V1 includes split/overlap audits, frozen-predictor evaluation, perturbation probes,
distance/error diagnostics, optional interval calibration, abstention assessment,
and budgeted optimizer exploitation tests. Start with classical predictors.
RNA-FM/LoRA is an interchangeable optional arm, not a prerequisite.

V1 excludes synthetic-label training, augmentation, adversarial retraining, a new
predictor architecture, an active-measurement loop and broad chemistry generation.
Those interventions require later protocols after baseline failure modes are
measured. Do not mix their tuning effort into a robustness comparison.

The first measured adapter should cover the chemistry-matched ASOptimizer ASO
efficacy subset already used by the repository. MOE neurotoxicity is a separate
replication with its own endpoint/context contract. Atlas inhibition follows when
an identified artifact, verified folds and input context are available. Huesken can
provide a separate siRNA control, never an ASO efficacy or safety reward.

This ordering is an engineering default, not a declaration that any model passes.
Historical datasets and development results have already been inspected. New
partitions from those sources are internal evaluations, not untouched external
confirmation. Record prior exposure and reserve any genuinely unscored campaigns.

### Existing-code integration

| Existing component | Reuse | Required boundary |
| --- | --- | --- |
| Source catalog/manifests, Atlas preparation audit | Source hashes, original observations, units and identity metadata | Do not overwrite raw data, joins or supplied folds |
| `research/budgets.py` | Fixed validation groups and nested measured-label allocations when training arms need matched budgets | Caller constructs connected leakage groups; planner does not prove biological isolation |
| `models/`, `features/` | Existing validated estimator/feature recipes | Fit features/scalers on declared fitting records only; tuning stays in development |
| `reward/scoring.py` | Model manifests, structured raw scores, named uncertainty and score ledger patterns | Current candidate scorer is fixed MOE/19-mer and requires an objective; it is not a generic held-out assay evaluator |
| `reward/atlas.py`, `reward/chemistry.py` | Verified representation mapping and parser | Preserve original HELM; parser support does not prove training-domain support |
| `rl/` search/environment | Design-space legality, masks, PPO rollout, cache and costs | Reuse unchanged for compatible transcript-site experiments; do not fabricate sites for source molecules |
| `rl/evaluate.py` | Partition validation and deferred exact-assay reporting patterns | Add robustness-specific metrics; final measurements never enter optimization |

Measured robustness rows may have lengths absent from the 19-mer environment and
different assay schemas. Keep them as label-free source observations. Add a small
endpoint-audit predictor protocol rather than padding/truncating molecules or
inventing cell-line, route, transcript or dose values to satisfy `AssayProfile`.

## 3. Evaluation tracks and permitted conclusions

| Track | Inputs and outcome availability | Permitted conclusion |
| --- | --- | --- |
| R1: held-out prediction | Exact source assay records with outcomes held by evaluator | Accuracy/ranking on the specified excluded groups |
| R2: perturbations | Verified original plus controlled variants; variants usually unmeasured | Representation correctness and prediction sensitivity; biological error only where exact compatible measurements exist |
| R3: diagnostic validation | Training-reference diagnostics plus held-out measured error | Whether a diagnostic predicts error and whether abstention works on those groups |
| R4a: recorded-pool optimization | Fixed label-free candidate-assay pool; exact outcomes revealed after all search is locked | Retrospective selection quality and surrogate exploitation within the recorded pool |
| R4b: generated design optimization | Existing legal ASO site space; usually no outcomes for new designs | Surrogate behavior and computational corroboration, with measured coverage explicitly reported |

Never carry a measured label from a parent onto its edited molecule. Never use a
nearby sequence as a substitute measurement. A sensitivity flag is not an error
label; disagreement is not proof of unreliability; a familiar candidate can still
be mispredicted. For R4b, absence of exact outcomes is an explicit limitation.

## 4. Data identities, splits and label capabilities

### Identity hierarchy

Retain source observation ID and original source bytes. Derive separate hashes for:
normalized chemical structure, natural-base sequence, target/transcript identity,
assay context and endpoint-specific compound-assay identity. Chemical identity must
retain base modifications, sugar pattern, linkages and terminal chemistry.
Unresolved identity is `unknown`, not a unique inferred compound. Different doses,
durations or assays are not interchangeable duplicates. Replicate handling is
predeclared; retain original rows and use compound/group weighting so repeated
records do not inflate apparent independent sample size.

### Split construction

Freeze split manifests using label-free metadata before new scoring. Preserve the
published/supplied split as a separate benchmark view. Robustness views include:

- Target-held-out: exclude the evaluation target and compound/sequence equivalents
  from fitting, model selection, calibration and domain-reference construction.
- Patent/compound-held-out: assign connected components of the required patent and
  chemical-equivalence relationships. Patent IDs are not assumed patent families.
- Sequence-family-held-out: optional secondary view using a frozen label-free
  similarity rule with documented alignment, length and chemistry treatment.
- Context-held-out: secondary view only when chemistry/endpoint remain meaningful
  and enough independent groups exist. An unsupported chemistry is a rejection
  test, not an excuse to force a predictive accuracy comparison.

Missing group IDs cannot enter a target/patent-generalization claim. Quarantine or
report them separately. Resolve multi-target compounds and connected components
before allocating rows. If enforcing the required relationships creates one giant
component or infeasible splits, return `infeasible_split`; do not relax leakage
rules or retry seeds after outcomes.

### Separate capabilities

| Capability | Allowed information | Forbidden information |
| --- | --- | --- |
| Split planner | IDs, structure, metadata/groups and exclusions | Endpoint values |
| Fitter | Fitting rows/labels; development labels for declared selection | Calibration/final labels and reserved campaigns |
| Calibrator | Frozen predictor and separate calibration rows/labels | Updating predictor/features or reading final labels |
| Guardrail selector | Frozen model/calibrator, development diagnostics and outcomes | Final outcomes and policy-final evaluator feedback |
| Diagnostic/scorer | Label-free records, frozen artifacts and fitting-only reference | Fit methods, label oracle or evaluation metrics |
| Optimizer | Eligible metadata, frozen score capability, budgets and legal moves | Any held-out outcomes, calibration labels or independent final scores |
| Final evaluator | Locked predictions, policies, archives and exact measured outcomes | Calling back into fitting, guardrail or checkpoint selection |

Use fitting/development/calibration/final partitions with disjoint required groups.
Calibration is optional when no intervals are produced; do not silently borrow it
for fitting. All labels used for fitting, selection, calibration or guardrails count
in separate and total real-label budgets. Model/policy evaluation targets must also
be excluded from their respective training and validation tasks. Public pretrained
weights with unresolved assay overlap cannot be called a clean final baseline.

Retrofitting a split manifest onto an all-label artifact cannot make it held out.
Audit artifact training IDs first; refit on valid partitions or mark
`blocked_artifact_overlap`. Final results are scored once after configurations,
guardrails, policy selection and candidate archives are sealed with hashes.

## 5. Proposed typed contracts

New schema: `predictor-robustness-v1`, independent of the core replay schema 0.2.
Use frozen dataclasses and explicit enums; do not modify shared contracts without
an integrator-reviewed compatibility change.

| Contract | Minimum fields |
| --- | --- |
| `AuditObservation` | Source ID, original HELM, normalized structure ID, endpoint/modality, target/group IDs, full context with missingness, source hash; no outcome |
| `RobustnessSplit` | Fit/development/calibration/final IDs, grouping/exclusions, achieved counts, prior-exposure status, source/split hashes and overlap audit |
| `AuditPrediction` | Model/endpoint IDs, raw mean/units/direction, named uncertainty or null, applicability/status/reasons, diagnostics, artifact/feature/context identities |
| `ReferenceManifest` | Fitting IDs/hash, representation/scaling, neighbor-exclusion rule, training-only reference values/hash and supported scope |
| `PerturbationCase` | Parent/variant IDs, edit family/parameters/seed, original/projected structure, legality, assay-context change, measurement status and provenance |
| `GuardrailPolicy` | Chosen diagnostic/threshold, development-only selection receipt, minimum retention/error target, applicability, frozen policy hash |
| `OptimizationReceipt` | Space/pool/start/model/guardrail hashes, method/seed, budget caps, complete query trace, accepted/rejected proposals, sealed shortlist, stage costs |
| `RobustnessReport` | Schema/status, source/code/environment identity, split/config/selection hashes, metric denominators, per-group results, missingness, failures and non-claims |

Proposed predictor interface:

```python
class AuditPredictor(Protocol):
    manifest: AuditModelManifest

    def predict(
        self, observations: Sequence[AuditObservation]
    ) -> tuple[AuditPrediction, ...]: ...
```

Its caller supplies only label-free records. Fitting belongs in a different adapter
with explicit permitted IDs. The protocol is proposed, not an existing import.
Preserve raw predictions even outside measured ranges. Scoring transformations and
range-excursion diagnostics must not alter recorded source outcomes.

## 6. R1: held-out predictive performance

Before new outcomes, freeze endpoint adapters, group definitions, model/feature
recipes, real-label budgets, development search space and seeds. Reuse GP and RF
as initial independent classical arms where their input contracts match. Training
budgets/selection effort must be equal when comparing architectures. A training-
mean predictor supplies a simple reference on every measured evaluation view.

Report per-group and equal-group macro RMSE/MAE in original endpoint units; retain
pooled row-weighted results as secondary. Report Pearson and Spearman with reasons
for constant vectors or insufficient rows. Primary v1 prediction metric is macro
RMSE; ranking metrics answer a separate question and cannot replace it after a
negative result. Log exact eligible, scored, excluded and undefined group counts.

Report all groups, including negative-correlation targets. Use paired differences
on common rows/groups; a model that scores fewer records needs a coverage report
and a common-support comparison. No opaque composite across endpoints or scales.

## 7. R2: controlled perturbation families

| Family | Construction | Expected assertion |
| --- | --- | --- |
| Verified representation equivalence | Source-approved HELM aliases, canonical serialization and batch/row permutations | Same parsed molecular tracks; prediction parity within declared numerical tolerance |
| Legal target-site shift | Existing fixed-template LEFT/RIGHT transition; regenerate complement and HELM | Complementarity/coordinates/chemistry remain valid; prediction change is diagnostic, with no assumed sign or biological label |
| Chemistry/length/context change | One declared change within a predictor's verified scope; fixed remaining context | Separate variant identity, complete provenance and explicit availability of measurements |
| Unsupported or malformed input | Unknown tokens, broken annotation, invalid bounds/chemistry, missing required context | Explicit rejection before model inference; never silently repair or extrapolate |
| Assay-context probe | Change supported dose/time/category with unchanged molecule | New compound-assay identity; response sensitivity reported, no universal monotonicity assumption |

V1 molecular-design edits remain limited to legal site shifts. Broader source-model
probes do not expand the RL action space. Representation parity is a software
invariant; biological perturbations are not required to preserve the original score.

Use a frozen label-blind sample of fitting/development parents to develop probes;
apply the locked generator once to final parents. Record attempted/valid/rejected
variants and generation/inference cost. Report absolute raw prediction change,
rank change against the unchanged training reference, and change per normalized
edit distance where defined. Flag large changes using development-selected limits,
not final quantiles. A large change without exact outcomes remains `unverified`.

## 8. R3: domain distance, uncertainty and abstention

### Training-domain distance

V1 primary structural distance: for equal-length compatible ASOs of length L >= 2,
compute mismatch fractions `d_base` over L parsed base tokens, `d_sugar` over L
sugar tokens and `d_link` over L-1 internal linkages. Set
`d_structure = (d_base + d_sugar + d_link) / 3`. Modified and natural bases are
distinct tokens. Record terminal-chemistry mismatch separately; different terminal
scope is `not_comparable` until the model's contract explicitly supports it.
Name this representation `aso-track-hamming-v1`.
Unequal length or incompatible chemistry returns `not_comparable` under
this metric; do not pad/truncate or encode it as zero. A separate sequence-only
edit distance may be reported as secondary, with its chemistry limitation stated.

Reference candidates come only from fitting rows. For reference-distance
percentiles, exclude the query's full normalized compound group when scoring a
fitting example; otherwise a self-match creates misleading zero-distance values.
Persist the exclusion rule and failures where no other comparable group exists.
For final rows, query the frozen fitting reference only. Dose/time distance uses
fitting-derived transformations; unsupported categories are categorical scope
failures, not numeric distances. Keep structural and context distances separate.

### Diagnostic validation

Evaluate GP latent SD, RF tree spread, each distance and comparable-model raw
disagreement separately. Document which uncertainty is epistemic/model spread
versus predictive noise. Compare disagreement only for the same endpoint, units,
direction, chemistry and assay. Do not mix percent inhibition with FOB or TLR scales.

Primary diagnostic metric: group-balanced area under the risk-coverage curve
(AURC), using MAE risk and ascending diagnostic value to retain lower-risk records.
Within each group g at coverage c, retain `ceil(c * n_g)` eligible records ordered
by diagnostic, compute their mean absolute error, then average group risks equally.
Integrate trapezoidally over c=0.1, 0.2, ..., 1.0 and divide by 0.9; use actual
achieved per-group retention in the accompanying table. This primary curve measures
within-group diagnostic ordering without silently dropping difficult groups.
A secondary global-threshold curve evaluates deployment-style abstention and
reports changing group composition. Report the full curves; no integration across
undefined points. Lower area is better. Constant/tied diagnostics use a frozen
seeded tie policy and are marked non-informative rather
than treated as calibrated. Add a matched random-abstention reference and error-
oracle ordering as a post-hoc bound; the oracle is never a deployable policy.

Secondary diagnostics: Spearman association with absolute error, raw-range
excursions, error by development-defined distance/uncertainty bins, tail-error rates
and scored coverage. Define any large-error event from assay relevance before
outcomes; if unavailable, report descriptive errors without inventing a risk label.

### Guardrail selection

On development groups only, choose thresholds from a frozen grid to minimize
group-balanced MAE subject to predeclared overall and per-group minimum retention
and, if justified, an assay-specific error target. Tie-break toward greater retention, then simpler
policy. Freeze before final scoring. If no threshold meets the target, return
`no_supported_guardrail`; do not deploy a threshold that rejects everything or
substitute a final-set optimum. Report both accepted-set error and retention by
group, including excluded groups and rejected-candidate outcomes in deferred audit.

### Optional intervals

Only claim interval calibration after fitting a separate calibration layer and
testing its coverage. A first optional method is split-conformal absolute residual
intervals: sort calibration absolute residuals and take the one-indexed element
`k = ceil((n_cal + 1) * (1 - alpha))` as q, producing `[mean - q, mean + q]`.
If k exceeds n_cal, return `insufficient_calibration`, not a fabricated finite
interval. Never use final residuals to set widths. Report empirical coverage
and mean width at nominal 90% and 95%, with per-group breakdowns. Standard
exchangeability assumptions do not establish coverage under unseen-target/domain
shift; these views are explicitly empirical shift diagnostics. Any group-aware
calibration alternative needs its own declared method and eligibility counts.

## 9. R4: optimizer exploitation and guarded-search comparisons

### Recorded measured-pool test first

Build one fixed unlabeled, endpoint/assay-compatible candidate pool from a sealed
held-out partition. Search receives structures/context and frozen predictions,
never outcomes. Do not refit predictors during this test. This is selection against
a fixed surrogate, not active learning or experimental label savings.

V1 methods: uniform random proposals and greedy/local or genetic search where the
pool has a well-defined legal neighborhood. Add score-all ranking as a fully costed
reference. If a molecular neighbor is absent from the recorded pool, it is not an
eligible measured candidate. Existing site-space optimizers cannot be applied to
arbitrary records by inventing transcript coordinates. A generic pool adapter must
state its proposal graph; unsupported methods return `not_applicable`.

Run unguarded ranking and one validation-selected diagnostic guardrail with the
same raw candidate domain, starts, scoring/request caps and real-data access. Charge
scoring calls for rejected proposals and mask computations requiring inference.
Share no caches across arms. Freeze independent RNG streams and multiple optimizer
seeds. Keep unguarded archives as a control and report lost candidate coverage.

Seal all trajectories and top-k lists before accessing final outcomes. Proposed
development shortlist size is k=5; insufficient eligible candidates returns an
explicit shorter list and a separate coverage denominator. Freeze final k and
endpoint high-activity cutoff before new final results.

Primary optimization metric: equal-group mean measured outcome of the frozen
shortlist, oriented to the endpoint direction. For partial lists, report performance
and retention separately; add a matched-cardinality comparison and never fill
missing measurements with predictions. Secondary metrics: measured top-k enrichment
when a meaningful event is predefined, best measured value, selection regret to
the exact measured-pool oracle, diversity and overestimation on selected candidates.
The measured oracle is computed only by the deferred evaluator and never returned
to search. Exact-measurement coverage must accompany every metric.

Plot surrogate utility and deferred measured quality against actual scorer budget.
Compare against matched random selection and the non-selected evaluation population.
Raw prediction minus outcome is meaningful only in matching original units; a
percentile reward cannot be subtracted from a measured percentage. Report whether
optimization concentrates positive residuals and high-distance candidates. This
can support a narrow retrospective exploitation result, not general biological proof.

### Generated target-site test second

Use the existing 19-mer MOE space, fixed transcript/assay profile and frozen bundles.
Compare random/greedy/genetic with PPO only after fixture and real-profile gates
pass. Keep policy training, validation and final targets separate. Account for
offline training, guardrail-validation, fresh inference and diagnostic-reference
construction costs. Enumeration defines the surrogate optimum, not the biological
optimum, and stays outside policy observations.

An independent computational evaluator must have an identified training history
and remain hidden until archives are sealed. Audit shared training biases/overlap;
different model classes alone do not guarantee independence. Report evaluator
agreement separately from measured outcomes. With no exact measurements, label the
result `computational_only`; do not report measured potency, error or biological
exploitation detection for novel candidates.

## 10. Statistics, decisions and failure behavior

Average optimizer seeds within each target/group before group-level comparisons.
Seeds do not create independent targets. Report paired group-level differences
and a frozen grouped-bootstrap 95% interval, resampling independent groups rather
than assay rows (proposed 2,000 replicates, seed 1729). With fewer than five groups,
show individual groups and mark inference `limited_groups`; do not headline a
bootstrap interval as strong population evidence. Overlapping split repetitions
must be identified; do not count them as independent biological replicates.

Primary contrasts are declared per track/endpoint: R1 macro RMSE against its fixed
baseline; R3 AURC versus random abstention; R4 guarded versus unguarded measured
shortlist quality at matched caps. Freeze one primary contrast per track and label
the rest secondary; use a declared multiplicity correction if formally testing
several contrasts. An absence of measurable improvement is a valid conclusion.

Explicit report statuses include `fixture_only`, `complete_measured_diagnostic`,
`computational_only`, `infeasible_split`, `blocked_artifact_overlap`,
`blocked_missing_artifact`, `insufficient_calibration`, `no_supported_guardrail`,
`limited_groups`, `no_eligible_candidates`, `incomplete_budget` and `model_error`.
Include nonfinite/undefined metrics as null plus reason and contributing counts.
Model failures stop the affected run; never silently skip groups/seeds or turn
errors into candidate rejection rewards. Preserve completed cells and run receipts.

## 11. Proposed repository layout and CLI

All paths/commands below are proposed additions, not current executable APIs.

```text
src/oligo_engine/robustness/
  contracts.py       # New audit-only schemas and outcome-free predictor protocol
  splits.py          # Metadata-only leakage graph, partitions and overlap receipt
  adapters.py        # Source observations, frozen model parity and fit capabilities
  perturbations.py  # Typed families, legality and parent/variant provenance
  diagnostics.py    # Fitting-only distance, uncertainty/disagreement extraction
  calibration.py    # Separate calibration partition, optional interval method
  guardrails.py     # Development-only selection, frozen abstention policies
  optimization.py   # Recorded-pool bridge; compatible existing site-space reuse
  evaluate.py       # Deferred outcomes, group metrics, paired summaries
  __main__.py       # Explicit stage orchestration with preflight and resume checks
src/oligo_engine/reporting/robustness.py
configs/robustness/  # Frozen fixture and endpoint-specific diagnostic protocols
tests/test_robustness_*.py
tests/test_robustness_optional.py  # Explicit opt-in upstream/Atlas/RL integration
```

Proposed CLI stages: `plan`, `audit`, `predict`, `perturb`, `diagnose`,
`select-guardrail`, `optimize`, `evaluate`, `report`. `evaluate` alone accepts final
outcome access and requires sealed optimizer/prediction manifests. Stage outputs
are immutable; resume requires matching source/config/artifact/split hashes and
continues missing work without overwriting old receipts. Preflight rejects unset
required values and unsupported endpoint/context combinations before fitting.

No change to core replay contracts, app fitting behavior or shared dependencies
is assumed. Integrator reviews shared changes and assigns disjoint ownership when
implementation starts. No workers/worktrees are assigned by this specification.

## 12. Artifact contract

Store generated output under ignored `artifacts/robustness/<study-id>/`:

- Resolved protocol, source/endpoint/license references, code commit/dirty state,
  environment receipt and schema versions.
- Source-observation/compound/assay identity mappings, immutable split/exclusion
  manifests and overlap/unresolved-identity audit.
- Model/feature/calibration/domain-reference/guardrail manifests with hashes,
  allowed label IDs and budgets; no weight files in Git.
- Outcome-free prediction, perturbation and diagnostic records; locked optimizer
  trajectories, rejected proposals and candidate shortlists.
- Evaluator-only measured metrics, exact-join audit, group tables, denominators,
  uncertainty intervals, failure receipts and report provenance.

Plots: error by group; error versus domain distance; uncertainty versus absolute
error; risk-coverage; interval coverage/width when available; perturbation sensitivity;
surrogate versus measured shortlist quality by scoring budget; candidate coverage
and domain drift. A standalone Markdown report states which claims each figure
supports and whether outcomes are measured, synthetic or computational only.

Endpoint labels remain in their authorized source/evaluator boundary. Do not emit
labels into optimizer-readable stage directories. If private final prediction
buffers are needed, keep them inaccessible to fit/selection orchestration until
decision sealing. Paths alone do not provide security; capability APIs, process
boundaries and dependency review enforce accidental-leak prevention.

## 13. Delivery sequence and acceptance tests

| Milestone | Deliverable | Required evidence |
| --- | --- | --- |
| M0: protocol and metadata | Audit schemas, identity mapping, one endpoint and split manifests | Complete disjoint partitions or explicit infeasibility; original data hashes unchanged; artifact training IDs audited |
| M1: deterministic fixture | Predictor with known shift failure, known exploitable region and separate final outcomes | Recover the deliberately injected failure; no advantage claimed as biology; final-label poisoning cannot alter upstream outputs |
| M2: measured R1 | One classical endpoint adapter and grouped held-out report | Fit/feature spies receive allowed IDs only; all groups/seeds reported; prior exposure and scope explicit |
| M3: R2/R3 | Legal perturbations, diagnostics and guardrail report | Alias parity, preserved chemistry/context, no copied labels, self-neighbor exclusion and validation-only thresholds; uninformative diagnostics reported honestly |
| M4: recorded-pool R4a | Budgeted unguarded/guarded/random comparison | Same pool/caps/access; sealed top-k before exact outcomes; no outcome in query trace; measured-oracle isolation and finite exhaustion |
| M5: generated R4b | Real-profile candidate archive and independent audit | Trusted artifacts/parity, valid transcript/assay support, frozen policy partitions, all costs and explicit measured coverage |
| M6: reproducibility | CLI, fixture CI and regeneration guide | Fresh Python 3.11 / Poetry 2.1.4 install, core checks, optional runtime job, immutable resume and machine-readable failure receipts |

Specific invariant tests:

1. Poison final outcomes: splits, fitted transforms/weights, calibration, thresholds,
   perturbations, optimizer trajectories and sealed predictions stay identical.
2. Poison calibration outcomes: predictor weights stay fixed; only calibration
   outputs can change. Poison development outcomes: final outcomes remain unread.
3. Reject cross-partition compound/patent links, duplicated IDs, unresolved required
   context, overlap-bearing artifacts and invalid supplied-fold joins.
4. Equivalent HELM projections and batch reorderings preserve predictions within
   a fixed tolerance; unsupported chemistry triggers no inference call.
5. Perturbed candidates never acquire parent labels; out-of-scope edits are counted
   and rejected; biological sensitivity is not forced to be invariant.
6. Exclude all same-compound self-neighbors; final rows never fit domain/scaling
   transforms. Unequal-length noncomparability stays explicit.
7. Undefined correlation, empty feasible set, constant diagnostic, tied scores,
   no-support guardrail and insufficient calibration all serialize with reasons.
8. Every reset, rejected proposal, mask inference and reference-table construction
   is charged where applicable; budgets stop before inference; method caches do
   not leak free scores or external evaluator outputs.
9. Known synthetic exploitation produces increasing surrogate utility without
   improving the deliberately separate outcome; guarded behavior is checked
   against the known fixture, not hard-coded measured-world success expectations.
10. Checkpoint/artifact/config changes invalidate caches/resume. Repeated seeded
    runs reproduce identities/decisions; wall-clock differences remain expected.

Run `make lint format-check import-check test`; use an explicit optional integration
job for upstream/Atlas/RL runtimes. A scientific milestone passes with an honest
negative result when its protocol/invariants and reporting are correct.

## 14. Decisions to freeze before measured execution

The implementation may start with fixtures and metadata audits without these final
scientific choices. Measured scoring must fail preflight until its protocol names:

- Exact source revision, endpoint, source eligibility and group/equivalence rules.
- Verified model artifacts or fixed refit recipe; source-only versus target-adapted
  access; fitting/development/calibration label budgets and all exclusions.
- Prior-exposure status and any genuinely reserved final targets/campaigns.
- Assay-specific units/direction, compatible context/chemistry and missingness rules.
- Perturbation counts/edit families, diagnostic definitions, reference construction,
  tolerance for representation parity and guardrail minimum retention/error target.
- Independent groups, seeds, scoring caps, shortlist k, optimizer proposal graph,
  primary contrasts and confidence/multiplicity method.
- Exact measured-evaluation joins, independent evaluator provenance and what
  result would permit advisory versus required screening use.

Do not choose a clinical safety cutoff from this document. No universal minimum
correlation, domain-distance cutoff or uncertainty threshold is validated here.
The deliverable is a reproducible evidence map and a frozen, tested applicability
policy where supported; otherwise the correct output is abstention or insufficient
evidence.

## 15. Method references and local evidence

- Optimizers can exploit prediction overestimation under distribution shift:
  [Conservative Objective Models, ICML 2021](https://proceedings.mlr.press/v139/trabucco21a.html).
  This motivates the exploitation tests, not a decision to implement COM training.
- Ensemble uncertainty is a candidate diagnostic:
  [Deep Ensembles, NeurIPS 2017](https://proceedings.neurips.cc/paper/2017/hash/9ef2ed4b7fd2c810847ffa5fa85bce38-Abstract.html).
  Results on those benchmarks do not establish ASO calibration.
- Optional split-conformal interval construction and its assumptions:
  [Angelopoulos and Bates, conformal prediction introduction](https://arxiv.org/abs/2107.07511).
  Calibration on related rows does not establish coverage on shifted target groups.
- The repository's [reward-readiness check](reward-model-readiness.md) motivates
  held-out target and distance/error tests. Preserve its exploratory numbers, but
  do not repeat its stronger language that positive correlations establish biology,
  that correlation ratios measure retained validity, or that squared correlation
  automatically gives predictive variance explained for uncalibrated predictions.
- [The latest ASO handoff](updates/2026-11-14-1734-est-aso-rl-implementation.md)
  records working engineering code and remaining real-artifact prerequisites.

Document-only verification for this specification: validate local links, proposed
layout against existing namespaces and Git whitespace. No robustness runs or new
predictor performance are claimed.
