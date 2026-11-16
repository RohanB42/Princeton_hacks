# OligoAL: finalized molecular-design RL environment specification

Version 1.0 — November 14, 2026, 21:00 EST / November 15, 02:00 UTC.
Repository checkpoint reviewed: `47b7c1d`.

**Status: consolidated design specification, not an implemented environment.**
The user removed the original target-window scaffold. This document defines its
intended replacement and supersedes conflicting implementation choices in the
earlier RL handoffs. Historical results remain historical. Writing this document
does not launch training, select model checkpoints, or complete any acceptance gate.

“Finalized” fixes the architecture, scientific boundaries and completion criteria.
Data-dependent chemistry scopes, assay mappings, screening thresholds and numeric
study budgets must be filled in a versioned run profile before execution. An
unresolved field is a blocked gate, never permission to invent a value or quietly
reduce the deliverable to another fixed-chemistry window-search demonstration.

## 1. Purpose and primary research claim

Build a scientist-facing system that constructs and optimizes target-complementary
ASOs across **supported binding sites, lengths and chemical designs**, using frozen,
versioned efficacy and applicable risk predictors. A policy learns how to spend a
bounded computational scoring budget to discover useful candidates. It receives
predictions, not simulated experimental truth.

Primary question: **does learned molecular design produce better eligible designs
than credible conventional search at matched scoring budgets, and do any gains
survive separate evaluation?** A second question concerns robustness: do safeguards
or synthetic augmentation reduce exploitation of imperfect reward models?

The intended deliverable includes meaningful chemical design choices and a
compatible multi-endpoint profile. A single 20-mer template, one efficacy head and
only left/right movement does not meet that definition. Such a restricted profile
may remain an explicitly named diagnostic ablation, not the completed system.

Evidence has three separate levels:

1. **Engineering:** legal construction, correct scoring, accounting and reload.
2. **Computational design:** better optimization and/or corroboration by a
   separately audited evaluator on unseen policy campaigns.
3. **Biological evidence:** exact held-out measured compound–assay outcomes, or
   prospective measurements of generated candidates. Surrogate rewards alone do
   not reach this level.

Neither a positive RL result nor a robust predictor establishes therapeutic safety,
clinical efficacy or measured-label savings. A well-controlled negative result is
a valid research outcome; the task must not be enlarged to manufacture a PPO win.

## 2. Place in the broader system

The full workflow is **design → prioritize → select experiments → measure → update
predictors → redesign**. Responsibilities remain distinct:

| Component | Responsibility | Initial method |
|---|---|---|
| Molecular design | Construct and optimize new, valid ASO designs | MaskablePPO compared with conventional optimizers |
| Prioritization | Produce a constrained, diverse shortlist from evaluated designs | Deterministic Pareto/ranking/diversity logic; no separate candidate-selection RL agent |
| Experimental selection | Choose candidate–assay pairs to acquire under a real measurement budget | Existing active-learning methods first; selection RL is a separate future experiment |
| Property modeling | Train and calibrate endpoint-specific predictors | Classical models or RNA-FM/LoRA, selected by matched evidence |
| Robustness | Diagnose errors, domain shift and optimization-induced failures | Independent prediction and selection audits |

PPO changes policy parameters during training. Endpoint predictors and reward
transforms remain frozen throughout that run. New measurements may update models
only between versioned discovery rounds. There is no online reward-model learning,
pseudo-label feedback or assay acquisition hidden inside the first RL experiment.

## 3. Verified starting point and lessons that constrain the replacement

- The old scaffold is removed, including its environment, PPO runner, local-search
  experiment scripts and optional runtime. Shared chemistry, candidate identity,
  frozen scoring, prediction and robustness utilities remain.
- `model_checkpoints/manifest.json` preserves **287 prediction checkpoint files**.
  Checkpoints exist; that does not establish complete integration, applicability,
  independent evaluation or safety. Atlas loaders still require their pinned
  research code/runtime. The pretrained RNA-FM backbone is an external dependency.
- The exact 20-mer MOE Ridge bundle is a verified inference anchor for human HepG2,
  electroporation, 4,500 nM, 24-hour inhibition. It was fitted on 2,000 source
  measurements. It does not validate alternate lengths or chemical patterns.
- Its preselected top-20 panels improved measured inhibition over random
  expectation on two development targets. PPO did not produce that ranking result.
  No newly generated molecule was experimentally validated.
- Atlas LoRA adaptation has not established superiority over the matched classical
  controls. Model architecture is a replaceable component, not a novelty claim or
  a reason to force an inferior head into the reward.
- The original environment omitted flanking context and search history. A recorded
  counterexample showed identical observations with opposite optimal first actions.
  Later aligned-reward policies often learned a fixed sweep direction. Context
  sufficiency and training-campaign diversity therefore require explicit tests.
- Comparing PPO's terminal-position reward with another optimizer's best visited
  candidate mismatched the objectives. Granting free long-distance proposals only
  to some methods also confounded the initial comparison. Both are prohibited here.
- The robustness CLI fit fresh RF/Ridge audit models, not the intended existing
  checkpoint set. Its exact-context gate rejected all 2,536 final DGAT2 records.
  This was a protocol/preflight failure, not a measured predictor-accuracy result.

Historical evidence and qualifications are linked in section 20. No earlier claim
that the full molecular-design environment was complete should be carried forward.

## 4. Architecture and authority boundaries

The implementation has six independently testable components:

1. **Campaign/profile compiler:** validates transcript, chemistry grammar,
   endpoint contexts, model provenance, coverage and run budget.
2. **ASO construction grammar:** produces immutable, structurally valid candidates
   and legal construction/edit operations without consulting predictor scores.
3. **Frozen endpoint registry and scorer:** returns raw endpoint vectors,
   applicability, calibrated or explicitly uncalibrated diagnostics, and qualified
   utility. It has no fitting method or measurement-reader capability.
4. **Design environment and policy:** proposes designs, receives charged scoring
   responses, maintains its archive and learns the declared archive objective.
5. **Common optimizer harness:** gives PPO and conventional methods the same
   profile, candidate validator, scorer and evaluation budgets.
6. **Independent evaluator and product:** assesses sealed archives, generates
   qualified panels and presents evidence without modifying the search objective.

The environment never imports the final-outcome reader. The evaluation owner
holds those outcomes until configurations, policy checkpoints and candidate
archives are fixed. The application's all-label fitting path must not be used as
an experimental reward artifact and then described as held out.

## 5. Campaign and candidate contracts

Every campaign pins a gene, species, transcript identifier/version and sequence
hash; cDNA versus pre-mRNA; permitted target intervals; coordinate convention;
mechanism/profile; endpoint-specific assay contexts; starting designs; grammar
version; and budget. A gene name alone is insufficient. Transcript retrieval is
completed and cached before training, not performed in the environment's step.

Candidate identity includes:

- Modality and mechanism declaration; transcript identity and start/end coordinates.
- Natural ASO sequence, original HELM and canonical full molecular structure.
- Ordered base, sugar and linkage tracks, terminal groups and supported
  stereochemical specification where actually represented.
- Length, gap/wing layout, construction provenance and parent/edit history.

Keep molecule identity distinct from compound–assay identity and source-row
identity. Two doses of one compound are not two independent molecular designs.
Canonicalization may normalize verified aliases but must not discard chemistry.
Changing length, linkages, terminal groups or transcript content changes identity.

For the first mechanism family, use an explicitly supported ASO gapmer profile;
do not silently mix it with siRNA, splice-switching or unrelated modalities.
Sequence follows the approved target-recognition rule. Exact reverse complement
is the initial rule. Deliberate mismatches require a separate validated grammar
and model scope; arbitrary base mutations are not admitted by default.

## 6. Molecular construction and action design

The logical search operation is **propose a complete ASO design and request its
scores**. The policy constructs that proposal through a constrained grammar:

| Decision | Required semantics |
|---|---|
| Length | Choose from the profile's supported lengths; do not truncate an encoder or pad away a biological difference |
| Binding site | Choose any approved interval compatible with length and transcript; local shifts may be convenience edits, not the only access mechanism |
| Gap and wings | Choose supported gap length and wing arrangement consistent with the mechanism and total length |
| Chemical pattern | Choose approved sugar, base-modification and linkage templates; enable position-specific changes only where supported |
| Termini | Choose only explicitly represented and supported terminal states |
| Edit/restart | Start a fresh proposal or edit a copy of an archived design; rescoring follows the same rules |
| Commit | Validate the complete molecule and submit one charged candidate-scoring request |
| Stop | Finish the campaign and return the archive/shortlist, not necessarily the current construction state |

Length, gap size, wing size and positional chemistry are jointly constrained.
The parser accepting a HELM string is not evidence that a predictor supports it.
Do not invent a universal 16–25-mer range, arbitrary PS/PO mixing or unrestricted
modification vocabulary from general biological intuition. The profile lists the
actual admitted combinations and evidence. Unsupported choices are absent from
the production grammar and may appear only in a declared stress test.

**Reference policy interface:** a stage-aware construction state with a versioned
discrete token vocabulary and conditional masks. The policy selects length/site/
template/edit parameters in the required order, then commits. This avoids assuming
that independent masks on a MultiDiscrete vector can enforce coupled constraints.
No intermediate partial construction receives a predictor score. Partial states
are grammar states, not purported valid molecules. Alternative autoregressive or
hierarchical policies must preserve the same complete-proposal semantics.

Masks use structural rules, declared scope metadata and remaining budgets. They
must not inspect unqueried scores, measured outcomes, or an independent evaluator.
Predicted toxicity failure is not structural illegality: a complete scored design
may fail screening yet remain editable. Distinguish that state from malformed HELM.

All methods can propose the same complete designs. Conventional search is not
forced to simulate physical nucleotide-by-nucleotide travel, and PPO is not given
a smaller reachable region. Construction-token counts are bounded and reported,
but are not substituted for predictor-query budgets.

## 7. Observations, memory and campaign diversity

Observations must include the information needed for the declared choices:

- The permitted target sequence or an auditable encoding covering all selectable
  intervals, including relevant flanks and boundary/ambiguity masks.
- Current partial or complete design, chemical tracks, grammar stage, selected
  parameters, and conditional action masks.
- Fixed campaign/profile context and endpoint-specific assay metadata.
- Results for **queried** candidates: raw and normalized endpoint values,
  applicability, named uncertainty, domain diagnostics and screening outcomes.
- Visited compound–assay IDs, their returned scores, incumbent/Pareto archive,
  duplicate flags, remaining query and construction budgets, and missingness masks.

Do not encode an unavailable safety score as numerical zero without a separate
availability indicator. Do not preload neighboring candidates' predictions as
“context.” Predicted accessibility, off-target calculations and learned features
have declared sources and compute costs; cached transcript sequence itself does
not consume a biological assay.

Use a sequence/chemistry encoder plus an archive/history encoder. A recurrent or
attention-based policy is acceptable; a feed-forward policy is acceptable only
with an explicit sufficient history representation. A compressed observation can
still be partially observed: document that rather than claiming a Markov state
solely because the environment stores a complete archive internally.

Regression tests must reproduce the old hidden-flank counterexample and show
that the replacement exposes the distinguishing information. Truncating transcript
or archive inputs requires a declared information-loss analysis. Baselines receive
the same permitted features, not a poorer information interface.

Training uses multiple genes/regions, starts and supported chemical patterns with
controlled sampling. Hold out policy-validation and final campaigns. Randomize
irrelevant coordinate offsets and audit direction/template shortcuts; preserve
strand and biological coordinate semantics. Merely adding random seeds to one
landscape is not diverse training or independent evaluation.

## 8. Actual predictors and endpoint registry

Load **the intended existing trained artifacts**, not silently substituted fresh
audit models. Every entry declares checkpoint/hash, compatible code/runtime,
feature order and transforms, train/validation/calibration IDs, source provenance,
target-label adaptation budget, endpoint/units/direction, assay schema, chemistry
scope, normalization reference, uncertainty type and calibration evidence.

Before admission, compare direct owner-model inference with the packaged adapter
on fixed inputs. Require equal means and any uncertainty outputs within a declared
numeric tolerance; check ordering, batch invariance, missingness and serialization.
Inference must not refit featurizers, normalize using the candidate pool, or read
outcomes. Preserve model inputs and hash them for reproducible scoring.

| Model family | Intended role and qualification |
|---|---|
| Atlas classical, frozen RNA-FM or chemistry-aware LoRA | Competing ASO inhibition heads; choose by matched development evidence and declared source-only/target-adapted access |
| Verified 20-mer portable Ridge | Exact-profile inference anchor and regression control; not evidence for arbitrary chemical edits |
| ASOptimizer endpoint model | Separate activity endpoint or compatible comparison; do not rename activity as IC50 or average it with Atlas without assay alignment |
| MOE neurotoxicity model | Acute mouse neurobehavioral endpoint under its documented chemistry/dose/route; not general human safety |
| TLR7/TLR8 models | Separate chemistry-specific immunomodulation assays, controls and directions; not generic MOE toxicity heads |
| Atlas neurotoxicity/hepatic models | Admit only after actual checkpoint, endpoint and scope verification; availability is not assumed |
| Huesken siRNA models | Engineering/prediction research only; excluded from ASO reward composition |

The old 19-mer full-PS template lacked exact Atlas efficacy support; the 20-mer
profile solved a narrow efficacy case, not general chemistry coverage. Each newly
admitted length/template needs a metadata audit and measured prediction evidence.

Two models can disagree on the same endpoint only after units, direction and assay
context are aligned. Different biological endpoints are not an uncertainty ensemble.
Shared training data or pretrained encoders weaken claims of evaluator independence.

## 9. Assay compatibility and preflight coverage

Maintain a **context per endpoint**, not one fictitious universal assay. A cell-based
efficacy assay and mouse neurobehavioral assay can describe different desired
properties of the same chemical design, but their species, route, dose and time
remain separate, explicit conditions. Combining them is a qualified multi-endpoint
decision, not evidence of joint outcomes on that molecule.

Normalize metadata only with verified unit and category mappings; preserve original
values. Distinguish missing values from unsupported values and extrapolation.
The scientist fixes the contexts before search. Dose, assay type, cell line and
species are not optimizer actions for gaming efficacy or risk predictions.

Every profile declares one mode:

1. **Supported-context benchmark:** predeclared applicability rules backed by
   training/development evidence. Exact-match gating may be used where justified,
   but it is a policy decision, not proof that all other contexts are invalid.
2. **Validated interpolation/transfer:** an explicit context-aware representation
   and separately measured evidence support the admitted changes.
3. **Extrapolation stress test:** predictions may be produced outside the primary
   scope under a separately frozen experiment. Flag them and report separately.

Before fitting, tuning or final-outcome access, emit per-partition/per-target counts
for each head and the joint required-head intersection, valid chemistry options,
missing contexts, admitted fraction, candidate capacity and near-duplicate overlap.
Predeclare minimum coverage and independent group counts appropriate to the study.
**Zero final coverage is a preflight failure, not a completed measured experiment.**
Record the block and keep outcomes sealed. Do not change the seed or weaken the
gate after seeing results to obtain an evaluable or favorable cohort.

## 10. Multi-endpoint utility and robustness

Profiles distinguish **objective heads**, **required model-based screens**, and
**advisory heads**. Full scope requires real efficacy plus at least one applicable,
evaluated risk endpoint, and meaningful supported chemical choices. Missing a
required head blocks that profile. An efficacy-only ablation reports risk as unknown
and cannot be promoted to the full multi-endpoint result.

Candidate eligibility requires structural validity, required-head applicability and
the profile's declared screening criteria. A chemistry change cannot improve utility
by making a required risk head disappear. Do not renormalize weights across whatever
heads happen to be available. Different applicability profiles are reported separately
unless a scientifically justified common comparison has been declared.

Retain the raw endpoint vector. For optimization, map each objective to a bounded,
direction-corrected utility using fixed training-only references. Rank/percentile
utilities are not probabilities. Saturation or clipping used for reward must preserve
the original out-of-range value and frequency in diagnostics. It does not repair
the predictor. Immunomodulation criteria require an explicit assay control and desired
response; “more inhibition” is not automatically the correct risk direction.

Two supported objective modes:

- **Primary, constrained efficacy:** maximize normalized efficacy among candidates
  passing declared applicable risk screens. Retain the entire risk vector and
  report trade-offs/coverage. Call this constrained efficacy optimization.
- **Declared multi-objective study:** optimize a bounded monotone archive measure,
  such as Pareto hypervolume on applicable efficacy/risk utilities with fixed
  reference point, or a prespecified scalar utility. Report the Pareto front and
  sensitivity to preferences. Do not present arbitrary weights as validated biology.

Domain distance, disagreement and uncertainty may become guardrails or penalties
only under a declared development/calibration procedure. Record unsupported
diagnostics as unknown. Compare safeguards with unguarded ranking and simple
regularization. Uncalibrated GP/RF spread, a motif violation, or model disagreement
is not by itself proof of reward hacking. Target accessibility, oligo self-folding
and off-target complementarity are distinct diagnostics; none substitutes for another.

## 11. Reward aligned with returned designs

The output is an archive/shortlist, so the policy must optimize the quality of
designs it discovered rather than the physical position where an episode ends.
Let `A_t` be the deduplicated evaluated archive and `Q(A_t)` its declared quality.
For constrained efficacy, use the best eligible utility, with zero for an archive
containing no eligible candidate. For the multi-objective study, use the frozen
monotone Pareto archive measure instead. Utilities and `Q` are bounded by contract.

The reference reward is:

```text
r_t = Q(A_{t+1}) - Q(A_t)    on a completed scoring request
r_t = 0                    on construction-only actions and STOP
gamma = 1                  finite episodes with explicit budgets
```

Thus total return is `Q(A_final) - Q(A_initial)`. Do not add the final quality again
on STOP. Duplicate requests and rejected candidates cannot earn repeated gain.
The common initial archive is recorded and its evaluations are charged. The best
candidate remains returnable even if the last proposal was worse.

An end-only archive reward is the matched control; final-position reward is a
diagnostic ablation, not the primary objective. Query/time penalties, discounting
below one or shortlist-diversity rewards change the objective and require separate
profiles. Do not introduce arbitrary step bonuses that reward longer episodes.

Budget truncation seals and evaluates the existing archive. It must not erase
the incumbent or manufacture a zero-quality last candidate. Model exceptions are
execution failures with receipts; they are not biological failures rewarded with
a convenient finite penalty. An action forbidden by a published mask is an API
error; all optimizers use the same validator and failure semantics.

## 12. Cost model and fair optimizer comparison

The common primary budget is **candidate scoring requests**, including the common
initial evaluations, cache hits/revisits and requests rejected by applicability.
This avoids free filtering and free repeated score queries. Also record unique
compound–assay evaluations, per-head calls, inference batches, cache hits, proposal
tokens, embedding/constraint computations, wall time and hardware.

Construction-only grammar tokens consume a separate finite step/time budget and
reveal no predicted scores. All optimizers submit complete proposals through the
same scoring boundary. No method pays extra merely because two transcript sites
are far apart; local path cost is not the primary molecular-design resource.

If head costs differ, predeclare weighted per-head or wall-time budgets as additional
comparisons. Do not report a candidate scored by four expensive heads as equal
compute to one cheap head without also publishing the actual costs. Precomputed
tables are explicitly charged; replayed queries are simulated query budgets, not
reduced physical compute or real experimental-label savings.

Final campaigns start with fresh per-arm archives and query ledgers. Any backend
memoization must not leak other arms' search history or grant free logical queries.
Report offline policy training/checkpoint selection separately from deployment
queries. A compute-efficiency claim includes training cost and its stated
amortization across campaigns.

Required comparators use identical model bundles, context, grammar, starts, budgets,
candidate validity and reporting objective:

- Unchanged initial designs.
- Random valid complete proposals with a declared sampling distribution.
- Multistart greedy/hill climbing over supported design neighbors.
- A constraint-preserving evolutionary/genetic optimizer with explicit operators.
- Exhaustive enumeration when the finite space is tractable, costed in full.
- Fixed directional/template sweeps as shortcut controls where applicable.

A credible model-based search/batch-optimization baseline is valuable when compute
permits, but does not replace the mandatory simple controls. Learned and conventional
methods receive comparable development tuning budgets. If enumeration is cheap and
better, report it as the practical solution rather than hiding it.

## 13. Learning, partitions and leakage prevention

Use two explicit split hierarchies:

| Hierarchy | Partitions and allowed use |
|---|---|
| Endpoint predictors | Fit; development/model or safeguard selection; calibration; final measured assessment |
| Molecular policy | Training campaigns; validation campaigns for policy/architecture selection; locked final campaigns |

Audit identities across OligoGym, Atlas and any other source: compound, assay,
natural sequence, close sequence families, target and patent family where available.
Connect duplicates before splitting. Do not invent absent patent-family metadata.
Repeated contexts/rows of a molecule cannot supply independent confirmation.

State whether each final policy campaign is a familiar predictor target with a new
design task or a genuinely unseen predictor target. The latter requires exclusion
from every relevant supervised reward head and adaptation procedure, not merely
from PPO training. Unsupervised sequence exposure is documented separately from
supervised efficacy-label exposure.

Target-adapted artifacts retain their real-label budgets; they are not zero-label
deployment models. Normalization, representation fitting, guardrail selection,
reward weights, early stopping and PPO checkpoints never use final measurements.
Policy validation may inspect frozen surrogate outcomes on its own campaigns;
independent final evaluators remain inaccessible to the policy and reward adapter.

MaskablePPO is the reference policy method, not a preselected winner. Pin a compatible
runtime after a dependency/profile check. Train only with valid action masks; use
the same masks at inference. Persist policy, observation/action schema, target/profile
and scorer identities. Exact training resume requires optimizer, RNG, rollout,
environment and archive state; inference-only reload must be named accordingly.

## 14. Evaluation, statistics and primary comparisons

Freeze one primary objective/contrast per experiment before final evaluation.
The core optimizer contrast is final archive quality at the declared query budget
versus the strongest conventional baseline chosen on development campaigns. Report
archive-quality AUC as a secondary measure of how quickly useful designs emerge;
the reference reward optimizes final archive quality, not AUC directly.
The strongest final-test method cannot be chosen post hoc as the only comparator.

Report:

- Structural validity, applicable coverage, screening retention, completion/errors.
- Best eligible utility versus actual request budget, AUC and final utility.
- Raw endpoint trade-offs, Pareto quality where defined, duplicate rate and
  sequence/chemistry diversity of an equally sized returned panel.
- Out-of-domain drift, out-of-range predictions, uncertainty and comparable-model
  disagreement as optimization proceeds.
- Independent-evaluator scores/rank stability and exact held-out assay results
  where available; missing measurements remain missing.
- Full training, tuning, precomputation and inference costs.

Use at least five paired policy/search seeds for the intended study. Cross-target
claims require multiple independent final target groups; plan at least five where
data permit and justify adequacy before execution. Insufficient groups constrain
the claim rather than being replaced by thousands of correlated trajectories.
Average within target appropriately and bootstrap at the target/campaign level;
report seed variability separately. Five groups alone do not guarantee a precise
estimate. Include effect sizes and uncertainty, not only p-values or the best seed.

Predeclare budgets and report all of them. Threshold-crossing or sample-efficiency
claims require prespecified thresholds. Model queries are computational evaluations;
they are not newly measured biological labels.

## 15. Independent quality and reward-exploitation assessment

The search scorer is not its own final judge. Use three complementary evaluations:

1. **Recorded measured pools:** reserve exact compound–assay observations, seal
   selections before revealing outcomes, and compare guarded/unguarded ranking at
   matched panel size and costs. This validates selection on recorded compounds.
2. **Generated candidates:** use an independently audited evaluator with documented
   endpoint alignment, chemistry/context coverage, training overlap and correlation
   with the reward model. Report agreement as computational corroboration, not
   invented experimental efficacy. A different architecture alone is not independence.
3. **Optimization stress:** inspect whether increased reward accompanies worsening
   external rankings, growing disagreement, domain drift or constraint failures.
   Controlled counterfactuals and prediction perturbations provide diagnostics.

If no compatible independent evaluator exists, mark that evidence gate blocked;
the computational optimization experiment may still be reported with that limit.
Do not reuse a pseudo-label teacher as the sole supposedly independent evaluator.
Never substitute nearest-neighbor measurements for outcomes of a newly edited ASO.

## 16. Follow-on experiments remain separate

**Synthetic augmentation:** generate training-only, biologically constrained ASO
counterfactuals; obtain qualified pseudo-labels from applicable teachers; preserve
unknown endpoints and never copy measured labels onto edited molecules. Compare
real-only R0 against real-plus-synthetic R1 at identical real-label budgets,
architecture, tuning and splits. Run R0/R1 × conventional search/PPO, plus a
regularization/uncertainty-only control. Freeze reward models before each optimizer
run and assess with independent evidence. This is not a prerequisite for the first
real frozen-model optimizer comparison.

**Representation substitution:** compare classical, frozen FM and adapted FM heads
under matched data access. Evaluate whether changing a head improves independent
design outcomes, rather than assuming lower training loss improves rewards.

**Experimental selection:** after design, select recorded candidate–assay pairs
for retrospective replay or genuinely obtain new measurements. A generated molecule
without an observed assay cannot be “revealed” from a historical oracle. Update only
the appropriate endpoint model between rounds, issue new versioned bundles and
reassess policy compatibility. Standalone candidate-selection RL remains excluded.

## 17. Scientist-facing output

The interface accepts a pinned transcript/target region, a supported chemistry
profile, fixed endpoint contexts, scientific preferences and an evaluation budget.
It presents applicability and coverage before starting. Unsupported requests return
an explicit explanation, not an empty table labelled successful.

Return a deterministic, configurable Pareto/diversity shortlist with original HELM,
sequence, length, chemical pattern, coordinates, target provenance, raw predictions
and units, missingness, screening reasons, reliability diagnostics, score/model
versions, query cost and construction provenance. Display comparisons to initial
designs and conventional optimizers. Export a machine-readable panel and run receipt.

Every generated design is labelled **unvalidated computational hypothesis**. UI
language must not turn an advisory score or absence of a risk model into “safe.”
Assay applicability is a meaningful user decision; internal implementation details
belong in the audit view. If the full profile is unavailable, clearly separate the
restricted diagnostic demo from the intended full molecular designer.

## 18. Interfaces, modules and reproducible artifacts

Proposed boundaries, to be finalized against actual APIs before implementation:

```text
CampaignSpec      immutable target, allowed regions, profile, starts and budgets
ChemistryProfile supported design grammar, evidence and endpoint applicability
DesignGrammar    legal_tokens(state), apply_token(state, token), compile(proposal)
EndpointRegistry verified frozen bundles; predict(candidate, endpoint_context)
CandidateScore   raw vector, applicability, diagnostics, eligibility, utility
DesignEnv        reset/step/masks; construction state, charged queries, archive
Optimizer        propose complete designs through the shared validator/scorer
RunArtifact      protocol + identities + costs + traces + archive + status
Evaluator        sealed archives + separate final-outcome capability
```

Reuse `design/candidates.py`, `design/context.py`, `provenance.py`, verified
`reward/` adapters, `robustness/`, and `model_checkpoints/` where their current
contracts genuinely fit. Extend candidate identity/validation for variable
chemistry and lengths; the current fixed templates do not already provide that.
The app and measured study runners remain independent consumers. Do not restore
the retired action space and silently rename it as the replacement.

A future implementation can place the new grammar, environment, optimizer wrappers,
training and evaluation in a separate `molecular_design/` package. This is a
proposed layout, not an existing CLI. Assign disjoint ownership for grammar,
predictor integration, policy/baselines, evaluation and product; one integrator
owns shared contracts, dependency locks, profiles and merges.

Every run saves configuration; code/environment versions; data/split/target/model
hashes; checkpoint-selection history; action/observation schemas; initial IDs;
all complete proposals and reasons; predictor requests and raw responses; archive
quality traces; endpoint availability; runtime/costs; final panel; and explicit
completion or block status. Public reports distinguish retained historical
artifacts from new runs. No result is fabricated to satisfy an acceptance gate.

## 19. Acceptance gates and definition of done

| Gate | Required deliverable | Evidence to pass |
|---|---|---|
| A: supported scientific task | Chemistry/assay/model/profile and split manifest | Metadata-only nonzero coverage; sufficient declared groups; exact units; real checkpoint provenance; no forbidden overlap |
| B: actual inference | Frozen registry connected to intended artifacts | Direct/package/batch/reload parity, no fitting/outcome access, explicit missing heads and diagnostics |
| C: molecular construction | Target-aware grammar with meaningful chemical decisions | Multiple supported chemical patterns plus admitted length handling; canonicalization/complementarity and joint-mask tests; no invented chemistry coverage |
| D: RL correctness | Context/history-aware policy and archive-aligned reward | Telescoping-return tests, duplicate/reset/truncation invariants, old aliasing counterexample resolved, deterministic reload, known small optima used only as engineering tests |
| E: fair real optimizer study | PPO and required controls on the same profile | Matched request budgets, independent campaign splits, declared seeds/tuning, full costs, valid negative outcomes |
| F: independent evidence | Sealed measured/computational assessment | Compatible evaluated evidence with documented provenance, grouped reporting and reward-exploitation analysis; absent evidence blocks this gate |
| G: usable research delivery | Reproducible runs and scientist-facing panel | Clean-environment replay, actual artifacts, meaningful missingness, limitations and scope visible |

The **full intended system** requires all gates and at least one qualified
multi-endpoint chemistry-design profile. An unsupported risk model or insufficient
chemistry coverage is remaining work, not an automatic scope reduction. Engineering
can proceed against fixtures while those dependencies are resolved, but fixture
success cannot pass A, B, E or F. Prospective biological validation is a distinct
additional achievement; computational F evidence must be labelled accordingly.

Implementation order: audit/restore intended models → compile a supported profile
and metadata split → grammar and shared scorer → observation/reward correctness →
conventional baselines → bounded PPO → locked comparisons → independent evaluation
and product integration. Expand training only after diagnosing a useful task and
demonstrating valid information/cost boundaries. Do not gate publication on PPO winning.

Before any real run, the profile must fill: exact artifact IDs, head roles/contexts,
allowed lengths/templates/edits, applicability mode, risk/guardrail criteria and
their evidence, reward mode/normalizers, budgets, seeds, target partitions, primary
contrast, checkpoint-selection rule and independent evaluator. Those scientific
values are deliberately not fabricated by this specification.

## 20. Source context and precedence

This document synthesizes the user-provided research direction and local project
evidence. It introduces no new external literature or biological validation claim.
Where older notes propose fixed 19-mer movement, final-position rewards, arbitrary
risk weights or automatic novelty/uncertainty guarantees, this specification wins.

- [Scaffold retirement and preserved components](updates/2026-11-14-2038-est-rl-scaffold-retirement.md)
- [Published checkpoint inventory and loader requirements](../model_checkpoints/README.md)
- [Supported-profile measured ranking and initial PPO result](supported-aso-results-2026-11-14.md)
- [Reward-objective ablation, directional shortcut and missing-context audit](updates/2026-11-14-2008-est-rl-scope-reward-and-context-audit.md)
- [Robustness zero-coverage correction and intended-model integration gap](updates/2026-11-14-2029-est-robustness-zero-coverage-correction.md)
- [Robustness implementation and its current limits](predictor-robustness-implementation.md)
- [Historical multi-endpoint reward contracts](multi-endpoint-reward-adapter.md)
- [Broader prediction/acquisition/robustness infrastructure](research-infrastructure.md)

Historical numbers above retain their original qualifications. The new environment,
expanded chemistry grammar, integrated applicable safety heads and independent
design-value result remain work to be implemented and demonstrated.

Implementation status after explicit user authorization is recorded separately in
[molecular-design-implementation.md](molecular-design-implementation.md). This
specification remains the acceptance contract; the implementation report does not
waive the scientific gates above.
