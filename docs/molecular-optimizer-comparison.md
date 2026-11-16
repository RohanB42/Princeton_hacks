# Corrected PPO versus random and greedy

The five-seed development comparison finds no consistent PPO advantage. The
construction repair works: all 45 PPO evaluations use their requested scoring
budget, with no repeated design queries, edit/cancel loops or early stopping.
Random has the highest mean utility on DGAT2; PPO on CFB; greedy on FGFR4.

## Protocol and controls

Local sealed artifacts are in `artifacts/molecular-optimizer-comparison-v2/`.
`protocol.json` was frozen before the two additional policies were trained and
before the comparison was evaluated. The protocol records campaign, predictor,
configuration and relevant source identities. Seeds 700–702 reuse policies already
examined during the repair; seeds 703–704 use the identical training configuration.
This is an extension of a development experiment, not a fresh confirmatory test.

Each policy trains for 2,048 construction actions, with 256-action rollouts,
minibatches of 64, four PPO epochs, learning rate 0.0003 and entropy coefficient
0.01. Checkpoints are selected using CFB at 1,024-action intervals. All five
selected checkpoints are at 1,024 actions. Evaluation uses deterministic inference
with the corrected `transactional-v2` decoder.

The matrix is five paired seeds × three targets × three scoring-request caps
(2, 4, 8) × three optimizers: **135 runs**. Eight requests is the primary cap.
Every cap includes the starting design. Each target has the same start, frozen
predictors, eligibility screens and legal candidate space for all three methods.
The construction allowance remains 160 actions. Budget settings are separate
episodes; PPO observes its remaining budget, so curves need not be prefixes of
one eight-request trajectory. No test labels or final outcomes were accessed.

The controls now use `queried-history-v2`. Random uniformly permutes unqueried
complete designs. Greedy evaluates local neighbors in seeded random order,
moves on strict improvement and restarts at an unqueried design when no neighbor
improves. Known neighbor scores come from its archive without another request.
Neither control receives unqueried scores. This corrects wasted duplicate requests
in the previous controls; historical results remain separate. The original
algorithms remain available through `search(..., avoid_repeats=False)` for replay.

## Primary results

Best eligible archive utility, normalized to 0–1, mean ± sample SD over five seeds:

| Target / role | PPO | Random | Greedy |
| --- | ---: | ---: | ---: |
| DGAT2 / training | 0.7102 ± 0.0859 | 0.7570 ± 0.0509 | 0.1849 ± 0.3128 |
| CFB / checkpoint validation | 0.2221 ± 0.3176 | 0.0851 ± 0.1903 | 0.0876 ± 0.1958 |
| FGFR4 / previously used development | 0.1328 ± 0.2970 | 0.1328 ± 0.2970 | 0.1479 ± 0.3307 |

These are surrogate utility values, not measured efficacy percentages. A zero
means no positive eligible archive utility; every run still completed its queries.
SD describes seed variation, not uncertainty across independent biological targets.

| Target | PPO minus random | PPO minus greedy | Paired W/T/L vs random | Paired W/T/L vs greedy |
| --- | ---: | ---: | ---: | ---: |
| DGAT2 | −0.0468 | +0.5254 | 1/1/3 | 5/0/0 |
| CFB | +0.1370 | +0.1345 | 2/2/1 | 1/3/1 |
| FGFR4 | 0.0000 | −0.0151 | 1/3/1 | 0/4/1 |

The CFB mean advantage is unstable: PPO finds eligible designs in only two of five
runs, versus one of five for each control. On FGFR4 each method succeeds in only
one of five runs. Equality of PPO and random means there does not imply identical
behavior: their successful seeds differ. The data establish reliable construction,
but do not establish reliable generalization or superiority of PPO.

All methods use exactly their caps, with unique-design count equal to request
count in every run. At the primary cap this is one starting design and seven new
proposals. PPO's five training runs cost **1,692 scoring requests / 3,384 head
calls**, plus **80 checkpoint-validation requests**. Those costs are excluded
from the matched deployment caps and reported separately; the controls have no
policy-training cost. This is not a total-cost or cold-start advantage claim.

The plot and complete outputs are local:

- [Budget curves](../artifacts/molecular-optimizer-comparison-v2/comparison.png)
- [PDF plot](../artifacts/molecular-optimizer-comparison-v2/comparison.pdf)
- [Generated report](../artifacts/molecular-optimizer-comparison-v2/report.md)
- [All run metrics](../artifacts/molecular-optimizer-comparison-v2/results.csv)
- [Sealed summary](../artifacts/molecular-optimizer-comparison-v2/summary.json)

Expanded efficacy applicability and independent-evaluator gates remain open.
DGAT2 trained the policy, CFB selected checkpoints, and FGFR4 was used previously
in development. There are no independent final target groups here, so no
cross-target confidence interval or biological efficacy/safety claim is supported.

## Reproduction and verification

After installing the pinned molecular runtime, use a fresh output directory:

```sh
PYTHONPATH=src poetry run python scripts/evaluate_molecular_optimizers.py prepare \
  --config artifacts/molecular-decoder-fix-v2/config.json \
  --existing artifacts/molecular-decoder-fix-v2 \
  --output artifacts/molecular-optimizer-comparison-replay
PYTHONPATH=src poetry run python scripts/evaluate_molecular_optimizers.py train \
  --output artifacts/molecular-optimizer-comparison-replay --seed 703
PYTHONPATH=src poetry run python scripts/evaluate_molecular_optimizers.py train \
  --output artifacts/molecular-optimizer-comparison-replay --seed 704
PYTHONPATH=src poetry run python scripts/evaluate_molecular_optimizers.py evaluate \
  --output artifacts/molecular-optimizer-comparison-replay
PYTHONPATH=src poetry run python scripts/evaluate_molecular_optimizers.py report \
  --output artifacts/molecular-optimizer-comparison-replay
```

This replay requires the local scientific predictor/configuration artifacts and
the three earlier policy directories. The runner verifies frozen identities and
policy receipts, and refuses to overwrite run records. Policy weights and generated
artifacts remain ignored local files.

Validation: `make lint format-check import-check test` passes with **230 tests**;
the molecular RL runtime passes **six optional Gym/PPO integration tests**.
New invariant tests cover no duplicate control requests, consistent random/greedy
budget prefixes and natural completion when the legal design space is exhausted.
All 135 run seals were verified against the result index, and the plot was visually
inspected. No commit or push was performed.
