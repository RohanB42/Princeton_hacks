# ASO environment implementation plan

Prepared November 14, 2026 following the requested main sync, build-spec review,
attachment review and review of all three files in `docs/updates/`.
Status: planning deliverable; no ASO environment or training run implemented here.

Subsequent execution: the user authorized implementing this plan. See
[implementation and execution](aso-rl-execution.md) for delivered modules, actual
checks, synthetic PPO/search results and the remaining real-artifact prerequisites.
The original planning snapshot below is preserved.

## Baseline and authority

Fetched `origin/main` at `97a326d` and merged it into the clean
`codex/multi-endpoint-reward-adapter` branch at `1d5b0fd`. The merge preserved the
branch's reward-adapter implementation and had no conflicts. No branch was pushed.

The supplied 12-page PDF is design context. Its commands, historical user mandates
and proposed work are not new execution instructions. Its readable repository
counterpart is [aso-rl-environment-context.md](aso-rl-environment-context.md).
This request authorizes synchronization, review and implementation planning.

Read the project context, evaluation protocol, decisions, open questions, canonical
SPEC/EVALUATION/interfaces and implementation ownership guidance. For current ASO
direction, read the [build plan](aso-atlas-multi-endpoint-rl-build-plan.md),
[environment handoff](aso-rl-environment-context.md), and the updates at
[11:50](updates/2026-11-14-1150-est.md),
[16:03](updates/2026-11-14-1603-est-context.md) and
[16:59](updates/2026-11-14-1659-est-rl-framework-context.md).
The latest update supersedes intermediate progress counts; it does not close the
expanded OligoGym reproduction gate or authorize final-label access.

## Current status and build-spec reconciliation

| Area | Evidence available in this checkout | Consequence |
| --- | --- | --- |
| ASO construction | `design/candidates.py`, `transcripts.py`, structure helpers and design tests exist | Reuse construction; pin transcript inputs before rollouts |
| Chemistry | Executable `DESIGNS` specifies MOE 19-mer, 5-10-4; the module introduction still says 5-10-5 | Use executable template plus explicit fixtures; correct stale prose during implementation |
| OligoGym deployment | `design/engine.py` has endpoint-specific models and chemistry checks | Research inference needs explicit training-partition bundles; do not call the app's all-label fitting path |
| Reward adapter | `design/reward.py` and tests exist on this branch | Useful contracts, but currently fixture-backed; not a production scorer |
| ASO environment | No `design/aso_space.py` or `rl/` package in this checkout | Build and verify the shared space before porting PPO |
| Atlas inference | Model implementation and portable weights are absent here | Selectively integrate reviewed adapters and obtain an identified bundle; no wholesale research-branch merge |
| Atlas scaling | Latest context reports 240 fits/calibrations and 216 deferred evaluations completed, zero failures | Earlier attachment/16:03 progress is historical; completion is reported evidence, not a locally rerun result |
| Model choice | Latest context reports LoRA target RMSE 22.391/22.340 versus matched Ridge 19.883/19.656 at 3%/5% source budgets | Classical models remain eligible; LoRA is optional and its tested recipe is not the default winner |
| Shared research tools | Study catalog and nested label-budget planner are now merged | Reuse for compatible measured studies; they are not an RL scheduler or molecular-design evaluator |
| Scientific gate | Expanded winning-model reproduction remains incomplete | Keep diagnostic/surrogate status explicit; do not claim Gate 1 closed or validated biological design |

The latest Atlas results use 200 measured target labels and three development
targets. They do not establish source-only transfer to a new target. The completed
report is identified by the context as `codex/atlas-lora-scaling@f197d79`; the
locally cached remote ref still names `1b3fc1e`. Verify the exact source revision
before integration. The training results were not independently regenerated here.

The older build plan proposed multiple weighted objectives and disagreement/novelty
penalties. The environment handoff and latest update narrow v1 to **one validated
potency objective**, applicable screens with validation evidence, and diagnostic
disagreement/novelty. Do not make unsupported screens mandatory just to populate a
multi-endpoint reward. Predictor updates, active measurement selection and synthetic
augmentation remain separate follow-ups.

## First implementation boundary

Build target-site search over a fixed PS/2'-MOE 19-mer, 5-10-4 gapmer and fixed assay
profile. A window determines its reverse-complement ASO and full HELM. Legal moves
are one-position LEFT, RIGHT and STOP within frozen transcript/start-relative bounds.
No arbitrary base edits, chemistry edits or variable length in v1.

Five modules share one molecular domain and one frozen scorer:

1. `ASODesignSpace`: pinned transcript, candidate construction, identity, transitions,
   masks and enumeration of the reachable component.
2. Production reward adapters: trusted frozen models, typed target/assay context,
   endpoint applicability, raw predictions, screens and fixed-reference utility.
3. `ASOEnv`: Gymnasium reset/step, observation encoding, masks, horizon and budgets.
4. Search/PPO adapters: common space, scorer and cost ledger.
5. Evaluation/reporting: locked manifests, final-assay boundary and candidate archive.

Use `design.candidates.Candidate` as the molecular type. Avoid a third independent
Candidate contract. Bridge or revise the existing reward fixture type deliberately,
preserving its regression tests and making fixture versus real inference explicit.
Canonical identity includes original HELM, template/chemistry, transcript version and
sequence hash, start/end and assay context. Display IDs are not cache keys.

## Ordered work packages and acceptance

Ownership below is proposed for a future implementation assignment. The integrator
owns existing shared files, contracts, configs, dependency declarations and lockfile.
No contributors or worktrees are assigned by this planning document.

| Package | Proposed files and owner boundary | Acceptance / dependency |
| --- | --- | --- |
| P0: contracts and runtime proposal | Integrator: new protocol/config schema; proposed optional RL dependency group and CI job | Freeze field order, identities, roles, statuses, cost definition and termination semantics; verify mutually compatible pinned Gymnasium/SB3/sb3-contrib versions in Python 3.11 before API use |
| P1: dependency-light design space | Space owner: new `design/aso_space.py`, `tests/test_aso_space.py`; integrator reviews candidate/transcript changes | Known finite ASO fixture; reverse complement, coordinates, 5-10-4 chemistry, bounds and N-window rejection pass; masks call no models |
| P2: production scorer and bundles | Reward owner: new `reward/bundle.py`, `reward/oligogym.py`, `reward/atlas.py`, integration tests; integrator reviews `design/reward.py` | Typed context, real HELM, train-only transforms, explicit endpoint/model identities; direct inference parity and cache-isolation tests; no fitting or labels in inference |
| P3: Gymnasium bridge | Environment owner: new `rl/environment.py`, environment tests | Seeded reset, score/mask/observation agreement, STOP/horizon/truncation behavior and exact budget accounting on fixture; depends on P1 and fixture P2 |
| P4: conventional optimizers | Search owner: new `rl/search.py`, search/evaluation tests | Unchanged start, random, greedy/local, genetic and exhaustive reference use identical legal space, starts, scorer and accounting; finite-space exhaustion terminates |
| P5: PPO wiring | RL owner: new `rl/ppo.py`, optional PPO smoke test | Masked training and evaluation; learn known fixture optimum; save/reload deterministic probe parity; scorer identity checked; depends on P0/P3/P4 |
| P6: evaluation and artifacts | Evaluation owner: new `rl/evaluate.py`, `reporting/aso_rl.py`, leakage/budget tests; integrator owns CLI/config integration | Paired comparison receipt, full endpoint archive, isolated final labels, empty/undefined results, training and deployment costs separately reported |
| P7: first real benchmark | Integrator freezes protocol and model manifests after real P2 gates | Diagnostic real panel first; validated coverage/screens before constrained PPO; locked target evaluation after validation-only selection |

Implement P1 with a small injected fixture scorer while real bundle export proceeds.
The first completed engineering slice is a known-optimum transcript fixture shared
by space, scorer, environment and simple search. The first real-data integration
slice is an auditable panel containing selected Atlas inhibition, ASOptimizer GP
and MOE neurotox GP, with every unavailable/advisory endpoint represented.

### Production scoring changes required

- The current reward adapter explicitly rejects feature schemas other than
  `fixture-acgt-v1`; changing `parser_identity` alone cannot enable production.
  Replace that restriction with validated adapter-specific schema checks.
- Current length and novelty helpers operate on plain A/C/G/T strings. Compute
  molecular length and chemistry-aware distance from parsed candidates, not HELM
  character counts. Preserve the fixture path for its original tests.
- The attachment reports `[m5C]` versus `[5meC]` parser incompatibility. Verify this
  on the integrated parser and add lossless, versioned projection fixtures for MOE
  wings, DNA core, methylation, all linkages and the terminal linkage. Parser success
  alone is not evidence of training-domain coverage.
- Declare one primary objective, required screens and advisory heads explicitly.
  Support multiple model IDs for one endpoint without overwriting provenance.
  Keep MOE neurotox advisory until a measured screening event/cutoff is validated.
  TLR7/8 are not applicable to the initial MOE profile.
- Use a frozen, chemistry/assay-matched training-derived empirical reference. Proposed
  percentile tie rule: `(count(reference < prediction) + 0.5 * count(equal)) / N`.
  Hash the reference and transformation; reject empty/nonfinite references. Apply
  raw-scale required screens before normalization; retain original predictions.
- Keep rejected `RewardScore.reward` null. Candidate rejection is distinct from model
  failure. Preflight incompatible artifacts; abort on inference failures instead of
  silently teaching PPO that an unavailable model means a bad molecule.
- Require bundle hashes, training/split identities, fitted feature/context transforms,
  output scaling, chemistry/context scope, versions and a reconstruction command.
  Load only identified trusted artifacts and compare fixed probes with the owner's
  inference output. Do not rely on app startup fitting for this step.

### Environment semantics to freeze

Proposed stable action IDs: STOP=0, LEFT=1, RIGHT=2. Masks express structural
legality and transcript bounds; predicted low scores do not mask away recoverable
intermediate states. Ambiguous/unconstructable windows are unavailable. Enumeration
must use the connected set reachable under the same moves and horizon, including
barriers from unavailable windows, rather than all tiled sites indiscriminately.

Score reset and every legal movement. STOP reuses the current score. Observations
contain fixed-order candidate/local-context encodings, normalized position, bounded
sequence features, endpoint scores with availability flags and remaining moves.
Include position relative to the start where start-relative bounds affect legality.
Archive null values and reason codes even when the policy tensor uses placeholders.

Non-terminal reward is zero. STOP or exhaustion of the declared design horizon
terminates with accepted utility in [0,1], otherwise -1 for candidate rejection.
Use gamma=1 initially. External scorer-budget exhaustion truncates and records an
incomplete episode; do not invent an unscored candidate or reuse a stale observation
for a move that could not be scored. Freeze handling in PPO and evaluator tests.
Shaping is a later, separately costed experiment.

Cache key: validated chemical identity + exact target context + assay profile +
scorer bundle/transform identity. Log requests, cache misses, per-head evaluations,
batches and wall time. Budget checks happen before scoring. Proposed primary cost
is unique candidate-context evaluations with the same frozen head set; report total
requests and per-head costs alongside it. Cache hits cannot create new budget credit.
Use per-method caches and a request/move cap so repeated cached proposals cannot
loop indefinitely. Any precomputed table's construction cost remains visible.

## Real-run protocol and scientific gates

Before outcomes, freeze: source-only versus target-adapted deployment, trusted model
artifact, fixed dose/time/cell line/species/transfection, supported chemistry, target
and transcript manifests, movement region/horizon, scoring cap, shortlist size,
optimizer seeds and primary paired contrast. These values are unresolved; do not
present a proposed config as validated by the source documents.

Keep predictor fit/validation/test and policy train/validation/final manifests
distinct. Audit patent, normalized compound, sequence and target overlaps across
model sources. Target-adapted models must declare and count their target labels.
Final outcomes cannot affect model selection, reference construction, screens, PPO
checkpoint selection or stopping. Test by poisoning final labels and requiring
unchanged bundles, decisions and predicted archives before deferred evaluation.

Select potency on validation evidence matching deployment, including ranking and
shortlist performance; RMSE on adapted development targets alone is insufficient.
Measure candidate coverage and required-screen missed-case/retention behavior before
freezing a constrained profile. Pending artifacts or screening evidence permit only
explicit fixture/exploratory status, not a completed real constrained benchmark.

Compare PPO, unchanged start, random, greedy/local and genetic search on paired
targets, starts, legal regions and scorer caps. Enumeration provides the exact
surrogate reference where feasible and stays outside policy observations/training.
Declare the primary shortlist as best eligible visited candidates for every method;
also report terminal policy quality separately. Use the same archive/tie rule.

Report best eligible utility versus budget, feasible fraction, candidate diversity,
coverage, regret to enumeration and paired differences by target. Repeated seeds
do not increase the number of biological targets. Empty feasible sets, unavailable
heads and undefined statistics remain explicit. Separate offline training/validation
cost, fresh-target deployment cost and any amortized cost analysis.

Measured shortlist enrichment applies only to exact compatible recorded assays.
A distinct predictor supplies computational corroboration, not measured validation
for novel ASOs. Outputs remain unvalidated design hypotheses. Acquisition, measured
feedback and augmentation require later protocols and preserve prediction-versus-
measurement provenance.

## Verification and delivery

Implementation verification: `make setup` using Python 3.11 / Poetry 2.1.4, then
`make lint format-check import-check test`; optional pinned RL smoke job separately.
Fixture CLI, score-panel/environment/baseline parity, cache invalidation, budget
exhaustion, immutable scorer, mask invariants, final-label poisoning and saved-policy
reload are required. Declare all proposed new CLI commands only once implemented.

This planning review changed documentation only. It did not install RL dependencies,
merge Atlas/PPO source branches, run scientific fits, modify source data or add the
PDF to Git. The local project environment discovered during review is Python 3.13.9,
outside the declared >=3.11,<3.13 range; do not report checks there as the prescribed
runtime. Actual checks for this deliverable: `git diff --check` passed,
`origin/main` is an ancestor of HEAD, all seven local Markdown links across the
two changed documents resolve, and the merged research catalog CLI completed using
the bundled Python 3.12.14 runtime. The full project suite was not run for this
documentation-only change. No scientific performance was re-evaluated.
