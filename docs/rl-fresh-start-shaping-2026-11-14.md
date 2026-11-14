# Fresh-start comparison and reward shaping — 2026-11-14

## Protocol

The manifest was fixed before these evaluations. Thirty-two sequences were sampled with seed 8142026 from the frozen predictor training sequences after excluding all 96 previously used RL training, validation, and final starts. These are fresh RL starts, not unseen molecules for the predictor, biological targets, or experimental labels. Five optimization seeds are 11, 23, 37, 53, 71. No settings were selected using these fresh outcomes.

The terminal policies reuse the 4,096-step experiment. Shaped policies use identical training starts, architecture, optimizer settings, 32 updates and 4,096 steps, with checkpoint selection on the original 16 validation starts. No subsequent tuning was performed. Each policy proposes 16 stochastic rollouts per fresh start; random search proposes 16 candidates, and evolutionary search scores its initial sequence plus 15 mutation proposals. The evolutionary incumbent stays within Hamming distance eight of the start and accepts non-worsening proposals. All use the same frozen reward. The unchanged reference gets one score. This matches **scoring requests at inference**, not cache misses or total offline training costs.

## Shaping correctness

With gamma=1, the wrapper uses r_shaped = r + Phi(next) - Phi(current). Phi is the frozen reward at intermediate states, with zero potential at reset and termination. Summing the shaping terms telescopes to zero, so the complete episode return equals the original terminal reward exactly. The time/remaining-budget observation distinguishes initial and intermediate states. Tests cover immediate STOP, early STOP, the edit horizon and undoing edits. Evaluation always uses the original terminal reward. Shaping calls are charged to the training scorer; the method does not get free intermediate labels.

## Results

Metric: mean across 32 starts of the best reward among 16 scored proposals, then mean ± sample SD across five seeds. These scores differ from the earlier global best-search reward and deterministic one-rollout evaluation.

| Method | Mean | Sample SD |
| --- | ---: | ---: |
| terminal | 0.7161 | 0.0623 |
| shaped | 0.7326 | 0.0224 |
| random | 0.4760 | 0.0341 |
| evolutionary | 0.5331 | 0.0453 |
| unchanged | 0.0039 | 0.0000 |

Shaped minus terminal: +0.0165, approximate paired 95% Student-t interval [−0.0499, +0.0828] across the five seed means. This does not establish a shaping benefit. Both learned policies outperform these search baselines at this small inference request budget; they also consume substantial offline training and validation work. The seeds share one fixed predictor and one fixed set of starts, so the interval measures optimization variability rather than biological generalization.

| Training cost, mean per seed | Terminal | Shaped |
| --- | ---: | ---: |
| training_score_requests | 562.0 | 4096.0 |
| training_unique_scores | 560.6 | 3852.8 |

Both variants additionally evaluate 16 validation starts before training and after every update, 16 original final starts, and checkpoint reload probes. The fresh evaluation consumes 512 scoring requests per trained policy per seed. Unique scoring counts are recorded in every row. This is an equal-environment-step shaping ablation, not an equal-oracle-cost advantage. Retain terminal reward as the default: shaping has no established improvement and costs more predictor evaluations.

## Verification and artifacts

Nine relevant tests passed, including four return-invariance tests and the existing bundle/environment/PPO/reload tests. Ruff check and format check passed. Artifact verification confirmed all 800 evaluation rows, exactly 16 scoring requests per optimizer/start (one for unchanged), no overlap with old start lists, and valid cache counters. Protocol, individual outcomes, summary, five shaped training runs and checkpoints are under `artifacts/rl_design/fresh_shaping_v1/`. Reproduction script: `scripts/compare_rl_shaping.py`; it refuses to overwrite that output directory. No assay labels or datasets were changed. Candidates remain unvalidated sequence proposals with no verified target binding.
