# Original target-window RL scaffold retired

November 14, 2026, 20:38 EST / November 15, 01:38 UTC.
The user explicitly requested removal of the original molecular-design scaffold
experiment. The last published pre-removal checkpoint is `f26922f`.
This is removal and dependency cleanup, not implementation of a replacement.

## Removed from the active checkout

- The entire `src/oligo_engine/rl/` package: Gymnasium environment, MaskablePPO
  training/reload, synthetic reward landscape, local movement accounting,
  conventional target-window search, paired evaluation and CLI.
- The `Action` enum and `ASODesignSpace`, including STOP/LEFT/RIGHT, radius,
  movement horizon, reachability and action masks. The old `design/aso_space.py`
  module is gone, with no compatibility shim that could keep the scaffold running.
- `configs/rl/`, the environment assessment/comparison scripts, and the mixed
  measured-ranking/PPO plot runner. The supported measured-study runner retains
  prepare/fit/evaluate only; its generated-panel phase and optimizer-only config
  fields were removed.
- Scaffold-specific environment/search/action-space tests and optional RL test
  collection. Shared inference tests use static constant model doubles, without
  recreating an optimizer environment or a synthetic optimization landscape.
- The robustness site-action perturbation bridge and the terminal RL penalty
  conversion on shared candidate scores. Inapplicable scores remain missing.
- The optional RL dependency group, `make setup-rl`, and the PPO CI job. Poetry
  2.1.4 regenerated the lockfile; Gymnasium, SB3, sb3-contrib, torch and transitive
  RL-only dependencies are removed. Every retained package version is unchanged.

The study catalog marks `aso-design-optimizer-v1` as **retired**. Historical
results/plans are retained with retirement notices; their former scaffold commands
refer to the pre-removal commit and are not current entry points.

## Preserved and decoupled

Independent work remains available: OligoGym/Atlas source data, endpoint predictors,
RNA-FM/LoRA research, active acquisition, the measured supported-profile ranking
study, predictor robustness, shared frozen inference and the candidate application.
The application had no PPO integration to remove. No replacement molecular-design
or experimental-selection RL implementation is introduced.

Only reusable non-optimizer utilities were extracted from the old action-space
module: pinned transcript and candidate-identity checks now live in
[`design/context.py`](../../src/oligo_engine/design/context.py), and deterministic
content hashing in [`provenance.py`](../../src/oligo_engine/provenance.py).
Robustness and inference import these directly and no longer depend on an RL
module. Candidate complementarity/chemistry checks, model hashes, assay gates,
missing safety values and measured-label boundaries remain intact.

The robustness fixture remains because it tests a separate predictor-auditing
workflow. Its previously identified zero-coverage measured experiment is not
corrected or rerun by this removal. That still needs the separately frozen
[corrective evaluation plan](2026-11-14-2029-est-robustness-zero-coverage-correction.md).

## Local artifact retirement

Ignored scaffold checkpoints, archived source, side-experiment scripts and outputs
were moved outside the repository to:

`/private/tmp/oligoal-retired-rl-scaffold-20261114/`

This includes the original environment review, supported-ASO optimizer run,
matched-window PPO study, reward ablation, observation/context audit, and generated
panel/combined figure. They are local historical artifacts, not distributed assets
or active experiment code. The measured efficacy bundle, split, predictions and
assessment remain under `artifacts/supported-aso-v1/` for independent prediction
work. Old documentation artifact links may refer to the retired locations.

Removing optimizer fields changes the preserved runner's config hash. Historical
phases remain sealed: do not edit old receipts or bypass input-integrity checks to
resume them. Reproduce the original combined experiment from `f26922f`; use a new
output directory for the retained prediction-only runner.

## Verification

- **200 core tests** and **3 optional robustness science tests** passed.
- A fresh synthetic robustness CLI run completed with the unchanged fixture RMSE
  77.78174593052023; this is plumbing evidence, not a biological result.
- Before moving the generated panel, all **64 real-bundle candidate scores** and
  the scorer identity matched the saved pre-removal outputs exactly. The shared
  model and scoring behavior were preserved by the module extraction.
- Ruff lint/format, import, Git whitespace and Poetry lock consistency checks pass.
- No active source, script, test, app, build or CI imports the removed RL package
  or action-space module. No source datasets or weights were modified.

The existing program still needs a new, explicitly scoped molecular-design
implementation if that research direction is pursued. Historical scaffold results
must not be presented as evidence that such a replacement already exists.
