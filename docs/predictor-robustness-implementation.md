# Predictor robustness implementation and local execution

November 14, 2026. Implemented locally after fetching and fast-forwarding to
`origin/main` at **6b6838b**. The existing uncommitted design spec and infrastructure
link were preserved. No commits or pushes are part of this implementation request.

The pipeline adds all nine component boundaries from the
[design specification](predictor-robustness-design-spec.md): metadata/split auditing,
frozen predictor adapters, held-out metrics, perturbations, domain distance,
uncertainty/disagreement diagnostics, calibration/abstention, sealed search audits,
and reproducible reporting. This is diagnostic infrastructure with tested fixtures
and a bounded measured-data execution, not a validated universal ASO guardrail.

## Current-main compatibility

Main now includes a supported **20-mer** MOE efficacy bundle and real-surrogate PPO
results. The original design spec's 19-mer-only references describe its earlier
snapshot. This implementation accepts original measured ASO lengths 2-20 without
altering molecules and reuses the current 19/20-mer design-space API for legal site
probes. A dedicated bridge supports the hash-verified 20-mer portable bundle after
checking its training membership and exact endpoint/units/context. No all-label
deployment model is retroactively called held out.

Existing supported-profile predictors, design/scoring/RL modules, raw datasets and
their prior positive/negative results remain unchanged. Initial standalone audit
models are fixed-recipe chemistry-aware Ridge and RF, using the current science
group; no OligoGym import, invented API, new dependency or lockfile change is needed.
A GP can supply named uncertainty through the audit protocol, but no new GP/LoRA
adapter or fit is claimed here.

## Components delivered

| Module under `src/oligo_engine/robustness/` | Implemented behavior |
| --- | --- |
| `contracts.py` | Frozen label-free source records, predictions, four-way split and predictor protocol; distinct chemical/assay/source identities |
| `splits.py` | Deterministic connected components for target or patent plus compound/natural-sequence links; complete partitions, quarantine and artifact-overlap checks |
| `adapters.py` | Original matched ASOptimizer metadata, partition-scoped numeric outcome reads, fixed RF/Ridge fitting and frozen prediction, actual model-state hashes and portable-bundle bridge |
| `perturbations.py` | Equivalent HELM serialization, malformed-input rejection, explicit supported-context changes and valid latest-main target-site shifts; variants never inherit labels |
| `diagnostics.py` | Chemistry-track mismatch distance, full same-compound self-exclusion, explicit noncomparability and frozen fitting-reference percentiles |
| `calibration.py` | Separate absolute-residual split-conformal interval implementation, exact finite-sample index and insufficient-calibration status; no target-shift coverage guarantee |
| `guardrails.py` | Development-only fixed-grid threshold selection with overall/per-group retention and optional MAE target; explicit no-supported-policy result |
| `optimization.py` | Uniform recorded-pool search and fully costed enumeration, immutable shortlists and traces, exact query caps and no outcome capability |
| `generated.py` | Post-selection generated-archive chemistry/context audit and optional computational comparison; no invented measurements or automatic independence claim |
| `evaluate.py` | Compound/group-balanced prediction metrics, diagnostic/random/oracle risk-coverage, error association and grouped bootstrap with limited-group handling |
| `pipeline.py`, `__main__.py` | Immutable stage orchestration, sealed dependencies, final-outcome deferral, runtime/code/source/config cache invalidation and explicit diagnostic provenance |

`reporting/robustness.py` writes standalone Markdown, JSON-backed tables and an
optional risk-coverage PNG. CI now selects the optional science tests explicitly
and runs the synthetic CLI. Remote CI was not executed by this local task.

## Run locally

Use Python 3.11 and Poetry 2.1.4. The installed environment used Python 3.11.16,
NumPy 1.26.4, scipy 1.15.3 and scikit-learn 1.4.0. Existing optional RL dependencies
are unchanged. Install selected groups with `poetry sync --with science,rl` when
both the audit and ASO RL runtimes are needed; reporting plots use the existing
reporting dependency or the plotting stack already installed with RL.

```sh
make lint format-check import-check test
poetry run pytest -q tests/test_robustness_optional.py

# Known synthetic shift/exploitation fixture:
poetry run python -m oligo_engine.robustness run \
  --config configs/robustness/fixture-v1.json \
  --output artifacts/robustness/new-fixture

# Original measured ASOptimizer subset; fixed internal diagnostic protocol:
poetry run python -m oligo_engine.robustness run \
  --config configs/robustness/asoptimizer-v1.json \
  --output artifacts/robustness/new-asoptimizer
```

Add `--plots` on the first full run if matplotlib is available. Plot files are not
overwritten; omit `--plots` when resuming an already rendered run.

Individual stages are `plan`, `audit`, `predict`, `perturb`, `diagnose`,
`select-guardrail`, `optimize`, `evaluate`, `report`. Execute them in that order;
missing dependencies fail instead of implicitly reading labels or refitting.
`select-guardrail` also fits the separate calibration capability. `evaluate` is the
first stage that reads final outcomes. `run` orchestrates all stages. Completed
matching stages resume without rewriting predictions; changed source, code,
runtime, configuration or stage seals invalidate resume. Runtime receipts append
separately and do not change scientific decision hashes.

The measured CLI currently supports the original ASOptimizer adapter, not arbitrary
Atlas Parquet or an automatic toxicity endpoint. Other endpoints use their own
adapter/config and cannot be pooled through this one. The portable/generation
bridges are programmatic and require explicit real manifests.

## Actual execution evidence

Final local receipts are under ignored
`artifacts/robustness/execution-20261114/{fixture,asoptimizer}/`.
Each contains resolved config/source/code state, split/overlap manifest, frozen
model metadata, outcome-free predictions/diagnostics, calibration/guardrail receipts,
sealed optimizer traces, evaluator metrics, runtime receipts, Markdown and PNG.
They record the then-dirty source state and implementation hash. Reports/weights
are not committed. Commands above regenerate into a new output directory.

### Synthetic known-failure fixture

320 synthetic 20-mer records across eight artificial targets. Split: 200 fitting,
40 development, 40 calibration, 40 final records. The deliberate predictor assigns
large optimistic errors to a known motif region; the separate synthetic outcome
capability assigns poor outcomes there. None of these are measured biological data.

The development-selected warning threshold is 0.0, retaining the known lower-error
half of development records. The unguarded model's final RMSE is 77.7817 fixture
units. Warning-ordered risk-coverage area is 18.6001 versus 53.4298 for structural
distance in this deliberately constructed example. Five paired random-search seeds
with 20 queries and k=5 give **+28.08 synthetic outcome units** for guarded minus
unguarded shortlists. There is only one final synthetic target, so no confidence
interval is reported. These values verify failure detection and wiring, not ASO
performance or a real uncertainty threshold.

### Measured target-held-out diagnostic: no admitted final context

Verified source hash
`9508beacae39f58b33a87cec0837ef6029102b82497782b83eb734dbcf4bfc79`
and recovered exactly the existing **5,586** matched ASOptimizer records from the
32,602-row release. Original HELM strings, including the version trailer, remain
unchanged. The parser uses an explicit `V2.0` trailer projection; it does not remove
chemical modifications. Patent fields are absent from this release view, so no
patent-generalization result is claimed. Patent splitting fails closed.

Frozen seed 1729 gives five connected target components:

| Role | Targets | Rows |
| --- | --- | ---: |
| Fitting | HBV, SOD1 | 1,920 |
| Development | MALAT1 | 41 |
| Calibration | KLKB1 | 1,089 |
| Final | DGAT2 | 2,536 |

Classical models fit only the 1,920 fitting labels. Scope is explicitly restricted
to fitting-supported source cell-line/concentration tuples, while those covariates
are not predictive features. **No development, calibration or final records satisfy
that context gate.** Both models refuse those predictions. This is a missing-domain-
support result, not a numerical accuracy failure or evidence of biological
unreliability.

Final scored coverage is **0/2,536**; Pearson, RMSE, MAE, uncertainty/error curves
and selection-quality comparisons are undefined/null. Guardrail selection returns
`no_supported_guardrail`, calibration returns `no_supported_calibration_rows`, and
the report includes `no_eligible_candidates`. It does not turn missing predictions
into zero error, choose a different split after outcomes, or silently extrapolate.
1,920 fitting and 41 development labels were accessed for model/guardrail stages;
no calibration labels were needed, and final values were available only to the
deferred evaluator. All source observations and provenance are preserved.

A meaningful next measured comparison requires a separately frozen, metadata-audited
supported-context protocol or an explicitly validated context-transfer model. This
run's outcome does not authorize loosening its scope or tuning on its final labels.
Previously studied rows remain internal development data, not external confirmation.

## Costs, safety of evaluation and remaining scope

Recorded-pool optimizers receive only a scorer callback. Predictor-table construction
is fully disclosed and charged separately; per-method query ledgers are **simulated
lookups**, not claims of physical assay savings or reduced actual model calls after
free precomputation. Rejected proposals count toward each arm's budget. Pool entries
deduplicate exact recorded compound-assay identities by first immutable source ID;
all original rows remain in predictive error reporting with compound balancing.
Paired shortlist comparisons match cardinality to the smaller arm.

Only random proposals and exhaustive ranking are admitted for the arbitrary source
pool. Local/genetic/PPO methods are `not_applicable` without a declared graph; source
records are never assigned invented transcript coordinates. For real 19/20-mer site
spaces, the existing latest-main local-cost/RL implementation remains the optimizer
boundary. The generated-archive bridge reports computational-only evidence and
does not establish evaluator independence or measured efficacy.

The current report includes the primary metrics/risk-coverage plot, raw stage
records and the tables needed for additional study-specific figures. It does not
claim a completed multi-target confirmatory study, trained augmentation model,
validated neurotoxicity screen, new independent evaluator, or full figure suite for
an unexecuted real design study. Expanded Gate 1 and endpoint separation are unchanged.

## Verification

Core checks and optional science tests are recorded after implementation. Tests
cover connected leakage groups, immutable identity/source bytes, denied outcome
access, parent/variant provenance, alias parity, missing context/units, calibration
indexing, self-neighbor exclusion, undefined metrics, guardrail retention, sealed
budgets, final-label poisoning and changed-runtime cache invalidation. The focused
suite has 22 cases, including three explicit optional science checks. Final checks:
**212 core tests**, **3 optional science tests**, lint, formatting, import checks,
local documentation links, Git whitespace and immutable CLI resume all passed.
See the [continuation handoff](updates/2026-11-14-predictor-robustness-implementation.md).
