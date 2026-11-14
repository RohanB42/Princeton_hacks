# Dependency-ordered implementation tasks

Local issue/worktree plan; no remote issues or worktree branches have been created.
Integrator owns shared contracts/configs and existing source. On November 14 the
user explicitly requested a subagent for the Huesken CNN learning-curve pilot.
`huesken_active_learning` is assigned the seven new adapter/policy/CLI/report/test
files listed in docs/huesken-learning-protocol.md and its task handoff. It shares
the workspace with disjoint file ownership; all earlier pending work is preserved.

Current status: I0 is implemented and locally checked. I1 source/install/alias checks
and the frozen five-seed linear rerun are implemented; numerical reproduction is
unresolved (gap 0.031032 vs 0.03 tolerance, severe ill-conditioning, historical seeds
unknown). An RF cross-check also missed (gap 0.031941). I2–I8 remain future tasks
under the original cut policy at that point. The later authorized implementation
scope is recorded immediately below.

November 14 update: the user explicitly authorizes the entire released collection
and cross-dataset pipeline implementation. The catalog, local group diagnostic
splits, measured diagnostic runner, generic HELM-hash RF and uncertainty policy are
implemented, with real end-to-end coverage on all 12 datasets. This completes the
engineering slice of I2/I3/I4 without marking Gate 1 reproduced or I4 scientific
comparisons complete. There is still no design agent/app or research result claiming
generalization. See dataset-pipelines.md for current commands and scope.

| ID / priority | Depends on | Proposed worktree / owner / exclusive files | Acceptance |
| --- | --- | --- | --- |
| I0 P0 contracts + fixture | handoff | integrator: AGENTS.md, docs, contracts.py, configs, metadata/lockfiles | executable typed contracts, adversarial fixture tests, command runs; synthetic status explicit |
| I1 P0 upstream reproduction | I0 | `../oligoal-infra`, A: data/upstream.py, audit_upstream.py, source verification tests, docs/upstream-verification.md | clean exact revision; supported Python 3.11 environment; verified keys, splitter and historical alias; source hashes; frozen baseline rerun and discrepancy log; Gate 1 decision |
| I2 P0 measured vertical slice | I1 | same infrastructure owner: evaluation/, measured configs submitted via integrator | official split manifests, measured oracle, random-only replay; deterministic IDs/budgets; separate full-pool reference; leakage tests |
| I3 P0 predictor + uncertainty | I1, frozen Predictor | `../oligoal-models`, B: models/baseline.py, features/upstream.py, tests/test_models.py | baseline config reproduced; transform fits revealed IDs only; explicit uncertainty semantics; calibration diagnostic; runtime recorded |
| I4 P0 policy comparisons | I2, I3 | `../oligoal-acquisition`, C: acquisition/policies.py, tests/test_policies.py, proposed policy configs | random + simple uncertainty/diversity; unique eligible choices; five paired seeds; random baseline preserved; no test feedback |
| I5 P0 results | I4 | A: reporting/, tests/test_reporting.py, methods/results docs | normalized AULC and threshold fixed first; paired differences; actual curves/error bands, full-pool reference, honest null findings; one-command reproduction |
| I6 P1 demo | I0 fixture schema; I5 for real results | `../oligoal-surface`, E: app/, app-specific tests, slides source | starts with visibly synthetic fixture; reads artifacts only; real run provenance, curves and next measured experiments; static fallback |
| I7 P2 biological design | I0; independent; Gate 2 before integration | `../oligoal-design`, D: design/, tests/test_design.py, docs/design.md | explicit modality/chemistry validity, target sequence context, untested panel; no combined siRNA/ASO safety score; no core protocol edits |
| I8 P3 RL | validated I4/I5; separate task authorization | independent research branch | training-only rewards and held-out tasks; credible heuristics; reward-hacking checks; no surrogate claim of wet-lab efficacy |

Integrator creates worktrees with `git worktree add ../oligoal-N -b feature/N` when
contributors are assigned and sibling paths are writable. Do not create unused
worktrees or pretend parallel work has happened. Owners propose shared-file changes
to the integrator; no concurrent lockfile/config/interface edits. Each experiment
issue closes with tested code, reproducible config, artifacts and interpretation.
Infrastructure issues may close with an explicit verified blocker rather than a
fabricated result; Gate 1 itself remains open until reproduction is justified.

Active scoped assignment: implement and execute configs/huesken-learning.toml
under docs/huesken-learning-protocol.md. This advances I2–I5 on the numerically
reproduced Huesken CNN, with explicit diagnostic status while the expanded
seven-dataset/historical Gate 1 remains unresolved. The integrator owns the frozen
protocol/config and reviews any shared-file change. No label-efficiency result is
claimed before the paired five-seed runs and reporting finish.

Cut lines: debug Gate 1 before novel modeling; cut generation/RL before acquisition;
cut UI to static figures if it threatens evaluation; freeze before submission.
