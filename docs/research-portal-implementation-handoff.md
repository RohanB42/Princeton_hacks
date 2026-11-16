# Research portal: design and NN/RL implementation handoff

Prepared November 15, 2026. This is the handoff for implementing the agreed concept
on the real website. Read this alongside the destination website's own instructions.
The existing website already generates ASO candidate batches using other models.
Preserve that generator and integrate a sequential research workspace around it.

## Product objective

Researchers open generated batches, run experiments, enter measurements as results
arrive, and receive new batch recommendations informed by accumulated evidence.
Optimize discovery of distinct strong ASO candidates within a declared measurement
budget. Prediction accuracy and information gain are secondary diagnostics unless
a separate objective is explicitly selected.

This is a persistent project workflow, not a one-shot prediction form. New batches
use relevant recorded information from all earlier batches, including unsuccessful
experiments, corrections, project notes and constraints. Preserve endpoint-specific
units and biological conditions; context retention does not mean averaging
incompatible measurements.

## Agreed interface

1. Open the current batch by default. Batch tabs are the primary navigation; the
   newest/current batch appears first, with older named batches accessible beside it.
2. Each batch shows its candidates, model predictions, recorded-data counts and
   testing status. Predictions and measurements must be visually distinct.
3. Clicking an ASO opens candidate details and its recorded measurements. Researchers
   can log another measurement or edit a previous one directly from this view.
4. Show the data-type selector only after clicking **Log a result** or editing a
   measurement. Do not organize the main workspace into assay/data-type tabs.
5. Provide **Generate new batch** prominently. It creates and opens a new named
   batch tab; allow renaming. Preserve the batch's candidate membership and the
   evidence/model versions used when it was generated.
6. Keep project context, research notes, measurement budget and recent activity
   visible alongside the batch. Generating predictions does not spend an assay.
7. New results and corrections inform future recommendations. Never silently
   rewrite historical batch proposals after their generation.

The interactive concept supports batch creation, renaming, candidate selection,
measurement entry, versioned corrections, context snapshots and return-state
restoration. These interactions were exercised in a local browser. Its generation
and numerical values are illustrative; no production inference or database is wired.

### Reference rendering

Editable inline source on the originating machine:

`/Users/rohanbadal/.codex/visualizations/2026/11/15/01a1dd6a-faea-7260-b1a3-36408c4ee90e/aso-research-portal.html`

This machine-local file is not automatically available to another computer/chat.
Copy or attach it as an optional visual reference. This Markdown contains the
essential design requirements without that file.

Visual direction: OligoAL brand; restrained research workspace; compact neutral
surfaces, muted teal accent, clear tables and status labels; persistent project
context sidebar; current-first named batch tabs; inline candidate details and
result editor. Support dark/light appearance and mobile reflow. Avoid a decorative
dashboard or unsupported model-confidence/safety scores.

## Data-type organization

Use measurement types as the result-entry taxonomy, while retaining experimental
conditions on each record. Do not expose assay segmentation as the main navigation.

| Type | Existing source variables | Implementation requirement |
|---|---|---|
| Inhibition | `Inhibition_pct`, `dosage_nm`, `treatment_period_hrs`, cell line/species/transfection | Preserve original values and units; do not clip values outside 0–100 silently |
| Dose response | Concentration and inhibition measurements in the dose-response table | Store points linked to compound/context/curve; do not treat doses as independent molecules |
| IC50 | Not a ready-made column in the inspected Atlas tables | Derived from a checked dose-response fit, or researcher-provided with curve/method provenance; retain censoring and fit failure |
| Hepatotoxicity | `ALB`, `ALT`, `AST`, `BUN`, `CREA`, `TBIL`, `PC_ratio` | Separate biomarker channels; preserve units, species, route and exposure |
| Neurotoxicity | `FOB_score`, score type, dose, latency, species and route | Preserve score definition; do not interpret as general human safety |

Keep missing endpoints missing. Do not produce a combined clinical safe/effective
flag. A candidate can have multiple measurements of multiple types; retain every
replicate and its relationship to an experiment. Repeated measurements do not earn
duplicate distinct-candidate hit credit.

## Current research implementation

Repository: `RohanB42/Princeton_hacks`. The experimental-selection implementation, configs, tests and selected 3x32 PPO
model package are now published with this handoff. The package is under
`model_checkpoints/experimental-selection-ppo-3x32-v1/`. Seed 613 was selected by
its highest recorded development score, not final-target outcomes. Unrelated
robustness work and the editable portal rendering remain local.

Relevant code:

- `src/oligo_engine/experimental_rl/environment.py`: Gymnasium expert-selection
  environment, candidate state, acquired-only feedback, observation schema.
- `belief.py`: source-only Ridge encoding and online Bayesian residual updates.
- `run.py`: policy training, checkpoint selection/reload and rollout helpers.
- `cohort.py`: Atlas verification, context/chemistry grouping, partitions and capacity
  preflight; metadata selection is outcome-blind.
- `study.py`: matched policy-seed comparison, sealed acquisition and deferred scoring.
- `runtime.py`: verified optional scientific/RL package versions.
- `report.py` and `__main__.py`: artifacts, figures and CLI.
- `tests/test_experimental_selection*.py`: environment, posterior, pairing, capacity,
  acquired-label, architecture and serialization invariants.

Configurations are under `configs/experimental_rl/`. Start by inspecting
`atlas_600_3layer.toml` and `atlas_available_3layer.toml`.

### What the NN actually is

MaskablePPO with `MlpPolicy`; actor and critic each have three hidden layers of
32 units, plus output heads. Total policy parameters: 5,642. It is not an LLM.
It chooses acquisition experts, which select candidates; it does not emit one
action logit per ASO or generate molecular sequences itself.

Inputs are 16 aggregate campaign statistics: budget/pool fractions; observed best,
hit fraction and latest result; prediction quantiles/max; uncertainty summaries;
chemistry coverage; updated-label fraction; dose and treatment time.

Experts include random, updated predicted mean, source predicted mean, sequence/
chemistry diversity, latent/total uncertainty, a hybrid and STOP where permitted.
The original training recipe uses gamma=1, learning rate 3e-4, rollout length 256,
batch size 64, five optimization epochs and 8,192 environment decisions per seed.
Five policy seeds are 613–617; checkpoint selection uses development campaigns
only. Production policy selection remains to be frozen; do not choose a winner
using already examined final-target outcomes.

### Evidence and limits

- 600 candidates per evaluation campaign, 50 purchases (10 initial + 40 selected):
  width-32 PPO 8.96 mean new hits; updated mean 9.00; random 6.70.
- Widening to 64 units gave 8.86 hits, with no demonstrated benefit.
- Full available evaluation pools, PSD3 1,759 and SMAD7 603: PPO 11.98; random
  5.10; updated mean 11.90; source ranking 12.00.
- The larger-pool run reproduced all five narrower-run policy parameter tensors
  exactly because training/development were held fixed. Different evaluation
  outcomes do not establish improved learned weights.
- PPO mostly selected existing ranking experts. No advantage over the strongest
  simple adaptive method is established.
- Requested PPO/random target-level exact permutation test: p=1.00 two-sided,
  p=0.50 one-sided. There are only two repeatedly examined target groups. A large
  descriptive gain on PSD3 does not establish generalization across targets.
- No compatible campaign had 6,000 distinct recorded candidates. The request failed
  before fitting; the user chose the available pools instead.
- The latest completed implementation checks passed 227 repository tests and
  15 optional experimental-selection tests. Subsequent portal rendering changes
  are separate; re-run checks for production integration.

See `docs/experimental-selection-*-protocol.md`, corresponding results documents,
and `docs/experimental-selection-target-availability.md` for qualifications.

## Required architecture for the real website

### Separate research replay from live operation

The current environment constructor requires a dictionary of every historical pool
label, and `step()` immediately reveals an outcome. That interface cannot be the
live website's state machine: future researcher measurements do not exist yet.

Extract a label-free recommendation core used by two adapters:

- **Replay adapter:** private historical oracle supplies only purchased outcomes;
  retain the scientific training/evaluation harness.
- **Live adapter:** recommendations become proposed/pending experiments. Only an
  explicit researcher measurement submission can supply an observed outcome.

Share encoding, inference, acquired-only belief updates, candidate validity,
budget semantics and policy feature construction. Do not give the production
recommendation service a hidden-label lookup or route predictions into observations.

### Backend boundaries

1. Existing candidate generator returns immutable chemistry-qualified candidates
   and generation provenance.
2. Workspace service stores projects, batches, experiments, observations, notes
   and immutable revisions.
3. Endpoint inference service loads verified, versioned predictors. It returns
   endpoint estimates, applicability, missingness and named uncertainty.
4. Project belief service updates appropriate endpoint beliefs using compatible
   recorded measurements only.
5. Recommendation service consumes a versioned context snapshot, remaining budget
   and eligible candidates; the NN chooses acquisition decisions or a batch policy.
6. Background worker handles generation/retraining jobs. The browser shows job
   status and prevents accidental duplicate submissions.

Use the destination website's existing framework and authentication. A Python
model service can run separately if the frontend host cannot support the pinned
PyTorch runtime. GitHub stores source and deployment configuration; production
researcher data belong in a database, and model artifacts in controlled storage.
Pushing the repository alone does not create this service.

### Minimal persistent records

| Record | Important fields |
|---|---|
| Project | owner/team, target/transcript identity, chemistry scope, objective, budget, notes revisions |
| Candidate | immutable molecular identity, original HELM, sequence/chemical tracks, generator version |
| Batch | ID/name, candidate IDs, status, generation context ID, policy/predictor versions |
| Experiment | candidate, measurement type, conditions, planned/actual cost, status, replicate/control links |
| Observation revision | experiment ID, raw value/unit, censoring/missingness, source, author, superseded revision |
| Prediction | candidate/context, endpoint, mean, named uncertainty, applicability, model version |
| Context snapshot | included observation revisions and notes, eligible candidates, constraints, budget and model hashes |
| Recommendation job | idempotency key, input snapshot, output batch, status/error and timestamps |

Never overwrite a molecule when editing measurements. Correct observations through
append-only revisions. The latest valid revisions feed future updates; historical
batch snapshots still identify exactly the information available at generation.
Budget accounting distinguishes actual purchases from corrections, failed/paid
experiments, planned reservations and unpaid proposals.

### Suggested API contract

Adapt naming to the real website:

```text
POST  /projects
GET   /projects/{id}/workspace
POST  /projects/{id}/batch-jobs        # snapshot + generate/recommend
GET   /batch-jobs/{id}
PATCH /batches/{id}                   # rename; preserve candidate membership
GET   /candidates/{id}/observations
POST  /experiments
POST  /experiments/{id}/observations
POST  /observations/{id}/revisions    # correction, not replacement
POST  /projects/{id}/notes/revisions
```

Enforce project ownership on every endpoint. Validate type, units, molecular
identity and conditions server-side. Use transactions, concurrency/version checks
and idempotency keys so retries cannot create duplicate measurements or spend a
budget twice. Define upload/export/deletion and retention behavior before inviting
external researchers. Do not silently use one team's private data to train a
shared model; require an explicit data-use choice.

## NN/RL development roadmap

### Phase 1 — Persistent sequential workflow

Implement batch tabs, candidate details, entry/edit forms and all-batch history
using the actual candidate generator. Integrate a simple existing acquisition
method first to verify the workflow. Maintain a visible research/experimental
status for any NN policy. Load frozen source models rather than fitting on all
available labels at web-server startup.

Acceptance: log a result in an old batch, generate a new batch, and demonstrate
that the new context includes the correction and all relevant historical records.
Earlier batch snapshots stay unchanged. Reloading or opening a second session
restores the same project. New predictions never become measured values.

### Phase 2 — Live compatible belief updates

Implement ingestion-to-belief updates with endpoint/context compatibility gates.
Provide cold-start behavior and supported-domain checks. The replay's exact ten
initial labels and fifty-assay horizon are experimental settings, not mandatory
product requirements; train/validate any policy used with different budgets or
input availability. Handle partial batches, pending results, new candidate arrivals,
replicates and missing outcomes.

Acceptance: only submitted observations can alter the posterior. Changing a pending
or absent outcome cannot change recommendations. Updates do not cross incompatible
endpoint/context boundaries. Deterministic reconstruction from the event history
matches the saved inference state.

### Phase 3 — NN policy integration

Package one development-selected 3×32 policy with source predictor, encoder,
observation/action schema, chemistry/context scope and calibration receipts.
Verify direct-versus-service inference and deterministic reload. Initially keep
policy weights frozen within a project while measurements update its belief.
Record the selected expert and recommendation provenance for audit.

Do not present this as a proven superior optimizer. Keep simple adaptive controls
in internal evaluation even if the researcher UI exposes only recommendations.
The 16-feature expert selector is a baseline; more NN capacity alone did not help.

Acceptance: identical context produces identical deterministic recommendations;
unsupported contexts have explicit missing/unsupported behavior; no data leakage
between projects; policy and predictor versions are pinned per recommendation.

### Phase 4 — Genuine batch-aware decisions

The current RL harness selects one candidate at a time and receives an immediate
result. Do not fake sequential feedback inside a proposed batch. Select the group
jointly, or sequentially without revealing unobserved outcomes, accounting for
redundancy and family coverage. Pending candidates are not automatically repurchased.
Explicit replicate requests have separate costs and purposes.

Compare an NN batch selector with credible matched-cost batch acquisition methods.
A candidate-set/history encoder or attention-based policy may be appropriate;
this is a new architecture requiring a frozen experiment, not established capability.
Keep the existing molecular generator separate from experiment selection.

Acceptance: selected candidates are eligible and unique unless replication is
explicit; partial batches obey remaining budget; no prediction is used as a reward
or observation; delayed and out-of-order result arrival is handled correctly.

### Phase 5 — Broader training and long-horizon evaluation

The metadata audit found 28 target identifiers with an individual compatible
campaign supporting fifty pool purchases plus twenty grouped sentinel records.
These are feasibility candidates, not 28 untouched independent test genes.
Eighteen contributed to previous source fitting/calibration. Audit aliases,
patents, exact compounds, sequence families and prior study exposure; freeze new
source, policy-training, development and evaluation roles before fitting.

Expand training campaign diversity, observed-history variety, horizons and budget
schedules. Evaluate sequential hit discovery at matched real-label budgets across
more target groups. More repeated seeds on the same two genes do not fix the
statistical limitation. Treat ongoing architecture exploration on already examined
targets as development evidence.

Acceptance: acquired-only fitting/rewards; poisoned hidden/sentinel labels cannot
alter forbidden decisions; paired per-target effects and uncertainty; invalid,
undefined and negative results reported; separate deployment and training costs.

### Phase 6 — Learning across researchers/projects

Within a project, measurements update beliefs and the NN's input state. Across
projects, a separate, versioned training pipeline can improve policy weights.
Do not automatically gradient-update a shared policy on every submitted assay.

Researcher-chosen measurements are observational and selectively collected.
Log recommended candidates, what was actually tested and available action context;
do not invent counterfactual outcomes for untested ASOs. Establish a justified
offline/off-policy or prospective evaluation protocol before training from those
histories. Training data-use permissions, project isolation and new-version
validation are prerequisites to shared learning.

## Integration and release sequence

1. Inspect the real website's routes, generator and deployment constraints.
2. Transfer/review the local research implementation and dependencies on an isolated
   branch. Preserve unrelated work. Read AGENTS.md and scientific contracts first.
3. Implement the workflow and live adapter with database migrations and versioned
   API/schema contracts. Do not expose the replay CLI as a web API.
4. Run repository checks, scientific invariants, API/data-isolation tests and a
   browser test of generation → entry → correction → next generation → reload.
5. Prepare a concrete reviewable commit/PR and private staging deployment. Publish
   to researchers only under the user's explicit release scope.

Python research runtime: 3.11; Poetry 2.1.4. The optional experimental runtime pins
Gymnasium 1.1.1, stable-baselines3/sb3-contrib 2.6.0, torch 2.3.1, NumPy 1.26.4,
SciPy 1.15.3, sklearn 1.4.0, pandas 2.2.3 and PyArrow 21.0.0. Check destination
platform compatibility. Run `make lint format-check import-check test` plus
optional RL/science checks in their pinned environment.

Do not commit researcher data, credentials or generated outcome ledgers. The
user explicitly authorized this selected PPO policy, matching source predictor
and provenance package after reviewing the publication scope. This exception
does not authorize other policies or future weights. Verify package hashes
before loading approved artifacts. No project license
or dataset redistribution rights should be newly assumed by this handoff.

## Initial instruction for the implementation chat

> Implement the batch-based research workspace described in this handoff around
> our existing website's candidate generator. Inspect the website and repository
> instructions first. Start with persistent projects, named batch tabs, candidate
> result entry/corrections and versioned whole-project context snapshots. Keep
> measurement types in the result-entry flow. Extract a live recommendation adapter
> from the existing experimental-selection harness without requiring hidden future
> outcomes. Preserve model/data provenance and report which parts are implemented,
> tested, illustrative or still scientifically unvalidated. Do not replace our
> candidate generator or claim the NN has demonstrated superiority.
