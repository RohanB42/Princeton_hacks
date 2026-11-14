# RL training-budget analysis — 2026-11-14

We tested one predeclared change: 32 PPO updates (4,096 steps) instead of four (512). Reward, frozen Ridge bundle, start manifests, seeds, architecture and optimizer settings stayed fixed. Checkpoints were selected on validation reward. Final starts were already examined in the prior pilot, so this remains exploratory evaluation, not a fresh confirmatory test.

## Results

| Metric | Original pilot | Longer training |
| --- | ---: | ---: |
| PPO best search reward | 0.7663 ± 0.0918 | 0.9260 ± 0.0182 |
| Random best search reward | 0.8397 ± 0.0436 | 0.9135 ± 0.0191 |
| Evolutionary best search reward | 0.8734 ± 0.0543 | 0.9298 ± 0.0113 |
| PPO validation mean reward | 0.3740 ± 0.1881 | 0.8078 ± 0.0094 |
| PPO final-start mean reward | 0.4613 ± 0.1075 | 0.8288 ± 0.0119 |
| Unique training scores per seed | 68.8 ± 0.8 | 560.6 ± 23.9 |

Values are mean ± sample SD over seeds 11, 23, 37, 53, 71. Each baseline receives the exact PPO unique training-score budget for its seed. The increase over the original experiment uses more compute and scores; it is not a claim of better sample efficiency.

| Seed | Scores | PPO best | Random best | Evolutionary best | PPO final mean |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 11 | 586 | 0.9103 | 0.8853 | 0.9403 | 0.8129 |
| 23 | 548 | 0.9560 | 0.9241 | 0.9227 | 0.8391 |
| 37 | 543 | 0.9135 | 0.9059 | 0.9335 | 0.8420 |
| 53 | 587 | 0.9286 | 0.9354 | 0.9138 | 0.8230 |
| 71 | 539 | 0.9214 | 0.9168 | 0.9386 | 0.8271 |

Paired differences across the five optimization seeds (approximate 95% Student-t intervals, df=4):

- ppo_minus_random: 0.0125, interval [-0.0071, 0.0320].
- ppo_minus_evolutionary: -0.0038, interval [-0.0370, 0.0294].

Both intervals include zero. Longer training substantially improves PPO, but superiority over either search comparator is not established. These intervals describe optimizer randomness on one fixed predictor and fixed start pool, not biological uncertainty.

## Diagnosis

1. The original run was an engineering smoke-scale budget: only four updates and about 69 terminal scores. Increasing duration alone markedly improved learned policy performance and reduced between-seed spread. This supports insufficient training as one contributor.
2. Ridge uses positional additive features. It cannot model interactions between positions; a simple mutation optimizer can efficiently exploit the same reward. PPO should be justified by broader sequential/context tasks, not merely by its availability.
3. Reward arrives only at STOP or eight edits. At the original final evaluation some seeds averaged nearly eight actions, despite much smaller net sequence distance. Revisiting positions and sparse credit assignment warrant a measured ablation; do not silently forbid revisits because that changes the domain.
4. The tanh reward compresses high predictions, and the distance penalty is an engineering preference. Higher reward does not demonstrate better measured potency. Neither term was tuned in this experiment.
5. Validation scoring is separately accounted for: 16 starts initially and after each of 32 updates, plus 16 final evaluations and reload probes. The main search comparison matches training/search unique scores, not total validation-inclusive compute. Final policy scores still lack a matched final-start baseline experiment.
6. We have only one fixed model, a small fixed start pool, and no independent predictor or assay validation. Improvements may exploit model errors. Uncertainty and target binding remain unsupported.

## Recommended continuation

Keep the 4,096-step run as the improved engineering reference, not a newly proven scientific model. Before further hyperparameter tuning, add an unchanged-start reference and matched final-start search baselines with explicit offline-training versus inference costs; reserve fresh starting sequences for a locked final evaluation. Then test one objective-preserving dense-reward shaping ablation against the same terminal objective and budgets. Log entropy, approximate KL, value fit, action reuse and effective edit counts to distinguish exploration failure from credit-assignment failure. Add a direct coordinate-search comparator appropriate to the additive Ridge reward. Avoid changing the reward to make PPO win.

## Artifacts and verification

Protocol and five complete reports: `artifacts/rl_design/improvement_4096/`. Summary: `summary.json`; mean/SD curve: `curve.png`; each seed directory contains best/last/update checkpoints, candidates, start manifests, histories and reports. The existing summarizer verified identical scorer/bundle/settings and exact matched unique-score budgets; all runs updated parameters and passed checkpoint inference equality. No implementation code or dataset was changed for this duration ablation. Prior runs remain available.
