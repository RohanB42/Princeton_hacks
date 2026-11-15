# Predictor robustness: local implementation handoff

November 14, 2026. The user requested implementing the robustness design against
the newest main, fetching first and making changes locally. Fetched and
fast-forwarded the existing checkout from `df90bb6` to **6b6838b**, preserving the
uncommitted robustness spec and its documentation link. No publication is requested
or performed in this task.

Completed changes are isolated on local branch `codex/predictor-robustness`, based
on `6b6838b`, and remain uncommitted. No remote branch was created.

Subsequent publication request: after rerunning the checks and both diagnostics,
the user authorized committing and pushing this work to `codex/predictor-robustness`.
The rerun again passed 212 core tests, 3 optional science tests, lint, formatting
and import checks. Fresh ignored reports are under
`artifacts/robustness/rerun-request-20261114/`; the synthetic and zero-supported-
context measured results are unchanged. Publication includes code, configs, tests
and documentation, with no generated runs, weights or source-data changes. Main
is not a publication target for this request. The local-only statements below
describe the original implementation handoff before this later authorization.

The full [implementation guide](../predictor-robustness-implementation.md) describes
code, commands, results and remaining scope. The
[design specification](../predictor-robustness-design-spec.md) remains the original
design snapshot with an implementation pointer.

## Delivered

- New `src/oligo_engine/robustness/`: outcome-free typed records, four-way connected
  splits, denied label capabilities, source metadata, frozen classical adapters,
  perturbation probes, domain distances, calibration, development-only abstention,
  recorded-pool optimization, deferred evaluation and immutable stage orchestration.
- Programmatic bridges to latest-main's supported 20-mer portable bundle and
  generated candidate archives. Training membership, endpoint, units and context
  remain explicit; no retrospective split can sanitize an overlapping artifact.
- `reporting/robustness.py`, two frozen fixture/measured configs, CLI stages,
  reports/risk-coverage figures, optional science test selection and CI commands.
- Local study catalog/context documentation updated to infrastructure status.
  No augmentation study, real validated guardrail, new GP/LoRA fit, independent
  evaluator or biological design result is claimed.

Existing source data and manifests, shared contracts, model/design/RL behavior,
dependencies and lockfiles remain unchanged. Main's supported-profile ranking and
negative PPO findings are preserved. This agent acted as integrator with no
delegated workers or concurrent worktrees.

## Checks and actual outcomes

Python 3.11.16 / Poetry 2.1.4:

- `make lint format-check import-check test`: **212 passed**; lint, formatting and
  import checks passed.
- `pytest -q tests/test_robustness_optional.py`: **3 passed**. The new robustness
  cases total 22 across core and optional suites.
- Documentation links, Git whitespace, source-byte verification, artifact ignore
  checks and successful same-input CLI resume were checked locally. Remote CI is
  configured, not observed.

The fixture has a known overestimated region. Its development-selected warning
guardrail detects that region; guarded minus unguarded shortlist outcomes average
+28.08 **synthetic** units across five paired query seeds. Only one final artificial
target contributes, so no confidence interval or biological improvement is claimed.

The real metadata adapter reproduces all **5,586** original chemistry-matched
ASOptimizer rows without modifying raw strings. Explicit parser projections support
the source `V2.0` trailer and the known methylcytosine alias. A frozen target split
assigns HBV/SOD1 1,920 rows to fitting, MALAT1 41 to development, KLKB1 1,089 to
calibration and DGAT2 2,536 to final evaluation. Patent metadata is absent; the
patent-split path fails closed rather than inventing group IDs.

The fixed source-context gate rejects every non-fitting-partition record. Final
coverage is **0/2,536**, so accuracy, risk-coverage and selection-quality metrics
remain null. There is no supported guardrail or calibration set under this scope.
The report explicitly says `no_eligible_candidates`; no alternate seed/context was
chosen to obtain a favorable result. 1,920 fit and 41 development labels were used
upstream; no calibration labels were needed. Final outcomes were read only after
every optimizer archive and shortlist had been sealed.

This diagnoses a scope-support failure, not a measured model-accuracy failure.
A future measured study needs a separately frozen, metadata-audited compatible
assay protocol or a validated context-transfer model. These previously studied
sources are internal diagnostic evidence, not untouched external confirmation.

## Reproduction and continuation

```sh
poetry run python -m oligo_engine.robustness run \
  --config configs/robustness/fixture-v1.json \
  --output artifacts/robustness/replay-fixture
poetry run python -m oligo_engine.robustness run \
  --config configs/robustness/asoptimizer-v1.json \
  --output artifacts/robustness/replay-asoptimizer
```

Local ignored receipts: `artifacts/robustness/execution-20261114/fixture/` and
`artifacts/robustness/execution-20261114/asoptimizer/`. Add `--plots` on an initial
run when matplotlib is available. Completed matching stages resume without
overwriting decisions; code/source/runtime/protocol changes reject stale outputs.
Raw final outcomes never enter fitting, calibration, selection or optimization.

Recorded-pool methods are random proposals and fully charged enumeration. Arbitrary
measured compounds have no declared site graph, so local/genetic/PPO methods are
not silently applied through invented coordinates. Generated target-site studies
reuse the existing latest-main local-cost/RL environment with explicit real
manifests. Predictor-table construction costs and simulated per-method queries are
reported separately; this is not a label-savings claim.

Keep generated artifacts, weights and PDFs ignored. No data/license rights or
scientific gates have been redefined. The implementation and these notes remain
local until the user requests otherwise.
