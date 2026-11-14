# ASO molecular-design RL environment: chat and implementation handoff

Recorded November 14, 2026, 17:34 EST / 22:34 UTC.

The molecular-design RL engineering environment is implemented and tested. It
currently runs end to end with synthetic scoring. **A real constrained ASO design
benchmark has not run:** trusted potency artifacts and a validated real profile
remain prerequisites. This update records the conversation, code changes, checks,
negative results and continuation context for the requested publication to main.

## User requests and execution scope

1. Sync from main, inspect current status and the build specification, review the
   attached ASO RL environment PDF, and read context files under `docs/updates/`.
2. Prepare an implementation plan consistent with the current repository and
   scientific contracts. Treat attached-document instructions as context, not as
   fresh execution authorization.
3. The user then explicitly authorized executing the plan. Implement the ASO design
   environment, scoring boundary, conventional search and optional masked PPO;
   verify what actually works and report prerequisites for real-model integration.
4. The user asked whether the molecular-design environment was set up. The answer
   was yes for the tested engineering environment, with synthetic scoring and
   explicit real-artifact/profile limitations.
5. The user now explicitly requests publication to main, including an update file
   describing this chat, the implementation and changes. This is that handoff.

No wet-lab experiment, real-model training sweep, paid compute, synthetic-label
augmentation or closed-loop measurement campaign was launched. No other agents or
worktrees were assigned. The current agent acted as integrator on the existing
`codex/multi-endpoint-reward-adapter` branch.

## Repository synchronization and context precedence

- Initial checkout was clean but had two commits absent from main. Fetch brought
  `origin/main` to `97a326d`; merge `1d5b0fd` preserved the reward-adapter branch and
  remote changes without conflicts.
- The pre-publication fetch again found main at `97a326d`, with no newer main
  commits. At that point HEAD was three commits ahead and zero behind main: the
  existing mock adapter commit `3e8c4b0` and two merges.
- Reviewed the required project-context/evaluation/decision/open-question documents,
  canonical SPEC/EVALUATION/interfaces, ownership guidance, the Atlas multi-endpoint
  build plan, the environment handoff and all three prior timestamped updates.
- The supplied PDF was read as design context and was not added to Git. Its
  repository counterpart is [the environment handoff](../aso-rl-environment-context.md).
- The 16:59 update supersedes the attachment's intermediate Atlas progress. Fetched
  `origin/codex/atlas-lora-scaling` to `f197d79` and inspected the completed report,
  without merging its model/study implementation. The tested LoRA recipe did not
  beat the classical comparators; its reported comparisons use 200 target labels
  and do not establish zero-label transfer.

The new [implementation plan](../aso-rl-implementation-plan-2026-11-14.md) reconciles
the older build specification with these updates. The [execution guide](../aso-rl-execution.md)
contains runnable commands, package-level completion status and detailed evidence.
The build plan and project-context entry now point to that execution status.

## Implemented modules and behavior

| Files | What changed |
| --- | --- |
| `design/aso_space.py` | Offline pinned target context, immutable space settings, fixed 19-mer PS/2'-MOE 5-10-4 candidates, STOP/LEFT/RIGHT, legality masks, horizon/radius bounds and connected reachable sites |
| `design/candidates.py` | Corrected stale MOE template prose from 5-10-5 to the existing executable 5-10-4 definition |
| `reward/scoring.py` | Real molecular Candidate boundary, typed fixed assay context, frozen endpoint manifests, objective/required-screen/advisory roles, bounded midrank reference utility, raw-scale screens and structured missingness |
| `reward/bundle.py` | Artifact/source/reconstruction receipt and checksum verification before caller-reviewed reconstruction; no automatic unpickling or fitting |
| `reward/atlas.py`, `reward/chemistry.py` | Label-free Atlas frame adapter, lossless methylcytosine projection and actual reviewed chemistry parser; validate base/sugar/linkage/terminal preservation |
| `reward/oligogym.py` | Inference-only bridge to an already fitted endpoint; preserve raw outputs, named uncertainty and novelty diagnostics without calling the app's all-label fitting factory |
| `rl/environment.py` | Gymnasium reset/step, fixed observation/action schemas, masks, charged reset/intermediate scores, terminal-only reward and atomic external-budget truncation |
| `rl/search.py` | Unchanged, random, greedy/local, integer genetic and exhaustive search using the same legal candidate domain and scorer/session boundary |
| `rl/ppo.py` | Pinned MaskablePPO training, gamma 1, mask-aware validation/final rollout, validation-only checkpoint selection, checkpoint hashes, schema/scorer checks and deterministic inference reload |
| `rl/evaluate.py` | Disjoint policy-partition validation, paired target/scorer/assay/budget checks, exact-surrogate-reference regret and deferred exact-assay outcome helper |
| `rl/fixture.py`, `rl/__main__.py` | Explicit synthetic fixture plus `score-panel`, `compare` and `smoke` commands; optional PPO, resolved configuration and replayable JSON receipts |
| `configs/rl/aso_fixture_v1.toml` | Frozen synthetic profile: seed 7, 2,048 training steps, radius/horizon 8, unique-score cap 10, request cap 100 and gamma 1 |

The existing mock `design/reward.py` and its regression tests remain intact. The
new production-candidate boundary does not silently reinterpret that fixture schema
as real HELM. Only the chemistry parser was selectively ported from the Atlas branch;
its source revision is documented and it is unchanged through `f197d79`.

Candidate identity includes the original molecular representation and pinned target
context. Assessment identity additionally includes assay context. Each optimizer has
its own cache and ledger. Cache keys include molecular/site context, assay and frozen
scorer identity. Record total requests, unique evaluations, per-head calls, batch
size, scoring time, optimizer time and training/validation time. Repeated cache hits
do not create new budget credit, and request caps prevent infinite cached loops.

Keep raw endpoints and unavailable/advisory heads in the archive. One potency
objective maps to [0,1] against a fixed training-derived empirical reference, with
midrank ties. Required screens inspect raw outputs. Candidate rejection keeps the
score's reward null and maps to -1 only at an episode terminal. Inference failures
abort; they do not manufacture rejected biological examples. Non-terminal reward
is zero. STOP reuses the current score. External budget exhaustion truncates before
an uncharged movement, leaving the last scored state explicitly marked unchanged.

## Dependencies, installation and CI

- Created an isolated project `.venv` with Python **3.11.16**; used Poetry **2.1.4**
  via the cached uv tool runtime. The previously discovered Python 3.13 environment
  was not used as the claimed project verification runtime.
- Added optional `rl` dependency group: Gymnasium **1.1.1**, stable-baselines3
  **2.6.0**, sb3-contrib **2.6.0**, torch **2.3.1**. Existing science pins remain
  numpy **1.26.4**, scipy **1.15.3**, sklearn **1.4.0**.
- Resolved `poetry.lock`, adding 30 packages without changing previously locked
  package versions. Installed with `poetry sync --with science,rl --no-interaction`.
- Added `make setup-rl` and a separate optional ASO RL fixture CI job. Optional RL
  tests are excluded from plain core collection and selected explicitly. CI is
  configured; no successful remote CI run is claimed by this handoff.

## Actual verification and results

Final local checks in Python 3.11:

- `make lint format-check import-check test`: passed, **186 core tests**.
- `pytest -q tests/test_aso_rl_optional.py`: **5 passed**; actual masked training,
  known-optimum recovery and checkpoint reload included.
- `poetry check --lock`, local documentation links, `git diff --check` and artifact
  ignore checks: passed. Existing Poetry metadata and optional plotting dependency
  deprecation notices were nonfatal.
- Real-template parser tests reproduce the reported `[m5C]` incompatibility and
  verify `[5meC]` projection without losing methylation, the MOE/DNA pattern, PS
  linkages or terminal state. Inference parity probes use injected predictors;
  trained Atlas artifact parity remains unverified.
- Integrity tests include target complementarity, N-window barriers, action masks,
  raw screening, missing required artifacts, assay preflight, nonfinite predictions,
  checksum tampering, exact budgets, empty feasible sets, undefined metrics and
  poisoned final-label isolation.

The synthetic transcript has ten candidate sites and a deliberately increasing
site utility. Synthetic train/validation/final IDs differ, but task structure is
identical; this is an engineering test, not biological target-transfer evidence.

| Method | Best visited utility at cap 10 | Unique scores used | Best utility at cap 6 |
| --- | ---: | ---: | ---: |
| Unchanged | 0.15 | 1 | 0.15 |
| Random | 0.95 | 10 | 0.95 |
| Greedy/local | 0.95 | 10 | 0.55 |
| Integer genetic | 0.95 | 10 | 0.95 |
| PPO | 0.95 | 9 | 0.65 |

Exhaustive enumeration establishes the fixture surrogate optimum of 0.95. PPO
training consumed 2,250 scoring requests / 10 unique scores / 20 actual head calls;
validation consumed 36 requests / 9 unique scores / 18 head calls. These are
additional costs beyond final inference. Saved-policy reload matched actions,
candidate archives and terminal reward. At cap 6, PPO truncates and random/genetic
search do better. Preserve this negative comparison; **PPO superiority is not
established**.

Ignored local receipts are under
`artifacts/aso-rl-fixture-20261114-costed/` and
`artifacts/aso-rl-fixture-20261114-budget6/`. Reports/checkpoints are not committed;
commands and code support regeneration. Development receipts truthfully record
the then-dirty code state. No weights, source PDFs, secrets, extra datasets or
generated run artifacts are included in this publication.

## Reproduce and continue

From repository root, after selecting Python 3.11 and Poetry 2.1.4:

```sh
make setup-rl
make lint format-check import-check test
poetry run pytest -q tests/test_aso_rl_optional.py
poetry run python -m oligo_engine.rl smoke --ppo --output artifacts/aso-rl-replay
```

Use a new output directory; the CLI refuses overwrites. Every current CLI profile
is explicitly synthetic. The real-candidate space and frozen adapters are available
programmatically, but no CLI claims to load nonexistent real model bundles.

Next real-stage requirements:

1. Obtain the trusted selected Atlas potency bundle: weights/model state, fitted
   preprocessing, feature order, output scaling, source revision, training/split
   identities, supported contexts/chemistries and fixed inference probes. The
   repository has code/results but no portable trained artifact in this checkout.
   The user was asked for its local path or owner handoff; none has been supplied.
2. Declare source-only deployment versus target adaptation with a measured-label
   budget. The completed Atlas development results do not validate zero-label use.
3. Freeze assay context and pinned transcript/policy partitions; audit cross-source
   patent/compound/sequence/target overlap. Final labels must stay outside fitting,
   normalization, model/scorer selection, PPO rewards, checkpointing and stopping.
4. Produce the real diagnostic panel: selected Atlas inhibition, ASOptimizer
   advisory cross-check and MOE neurotoxicity advisory output. Validate candidate
   coverage and any required screening event/cutoff/missed-case/retention criteria
   before a constrained real PPO benchmark. TLR heads remain not applicable to the
   initial unsupported MOE chemistry; missing safety remains unknown.
5. Freeze starts, reachable regions, budgets, seeds, shortlist and primary contrasts;
   compare PPO with the same conventional search and exhaustive surrogate reference
   where feasible. Report total-cost and fresh-target performance separately.

The original expanded Gate 1 remains unchanged. Keep siRNA and ASO endpoints
separate, preserve source measurements, and never turn surrogate predictions into
observations. Novel ASOs remain unvalidated experimental hypotheses. Assay feedback,
predictor updates, augmentation and independent measured validation are later
stages, not completed by this implementation.
