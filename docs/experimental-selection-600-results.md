# Three-layer PPO: 600-candidate measured replay results

Completed on the user-authorized `codex/experimental-selection-600` branch.
The [protocol](experimental-selection-600-protocol.md) and
[`atlas_600_3layer.toml`](../configs/experimental_rl/atlas_600_3layer.toml) were
fixed before source fitting, training and final campaign outcome access.

## Result

The three-layer PPO policy beat random but did not beat updated greedy in the
primary final-budget comparison. There is no established learned-policy advantage.
Five independent policy training seeds were averaged, rather than selecting the
best final seed. Five paired assay-initialization/replay seeds were used per target.

| Method | Mean new hits | PSD3 | SMAD7 | PPO minus method |
|---|---:|---:|---:|---:|
| Updated greedy | 9.00 | 18.00 | 0.00 | -0.04 |
| Three-layer PPO | 8.96 | 17.92 | 0.00 | 0.00 |
| Frozen source ranking | 8.40 | 16.80 | 0.00 | +0.56 |
| Random | 6.70 | 13.40 | 0.00 | +2.26 |

Each evaluation campaign had exactly 600 eligible candidates and 50 purchases:
10 common initial assays plus 40 selected assays. Hits are recorded inhibition
strictly above 80 percentage points. Initial assays cost budget and do not earn
new-hit credit. Each candidate is a distinct chemistry-qualified compound within
one fixed assay context. The $30,000 dollar mapping remains unresolved, as explicitly
accepted by the user; these are simulated unit-cost assay purchases.

The actor and critic each use hidden widths `[32, 32, 32]`, followed by their output
heads. Total actor/critic policy parameters: 5,642. Each seed received 8,192 PPO
environment decisions, for 40,960 training decisions overall. All other PPO settings,
16 aggregate observations and expert-selection actions match the earlier framework.
This is a compact neural RL policy, not an LLM or a policy with 600 candidate logits.

There were 80 final replay episodes: 50 PPO episodes across policy training seeds,
and 10 each for the three heuristic controls. Repeated seeds share biological tasks.
For the mean, average within target before equally weighting the two targets.

## Learned behavior

Across 2,000 final PPO decisions, 1,506 selected updated mean (75.3%) and 494 selected
frozen source mean (24.7%). Seeds 614, 615 and 617 always selected updated greedy.
Seed 616 always selected frozen source ranking. Seed 613 selected updated mean
306 times and source mean 94 times. No other expert was selected in final replay.

| Policy seed | Checkpoint selected on development | Mean new hits on evaluation |
|---|---:|---:|
| 613 | 1,024 steps | 9.40 |
| 614 | 1,024 steps | 9.00 |
| 615 | 1,024 steps | 9.00 |
| 616 | 1,024 steps | 8.40 |
| 617 | 4,096 steps | 9.00 |

Across these five training seeds the sample SD of target-macro mean hits was 0.358.
Reporting seed 613 alone would select on final outcomes and is not the primary
result. The learned behavior mostly copies the two strong ranking heuristics.
No distinct improvement in scientific reasoning or new acquisition rule is shown.

Two-target bootstrap intervals are descriptive only: PPO minus updated greedy
[-0.08, 0.00], versus random [0.00, 4.52], versus frozen ranking [0.00, 1.12].
These narrow or endpoint-touching intervals do not account for all uncertainty and
cannot support broad generalization or a significance claim with two target groups.

## Capacity and scope limits

Original roles and grouped sentinel memberships were preserved. Training used F7
(510 candidates), NLRP3 (capped at 600) and STAT3 (562); development used DMPK and
PLN (600 each). Final evaluation used PSD3 and SMAD7 (600 each). DUX4, KCNQ2 and
PTBP1 failed the label-blind 600-candidate capacity rule and were excluded before
fitting or reading outcomes. The original study already had some larger pools;
this comparison standardizes capacity rather than increasing every original pool.

After all policies and acquisition ledgers were sealed, an evaluation-only audit
found 185 qualifying recorded hits in PSD3's 600 candidates and four in SMAD7's 600.
All methods missed the rare SMAD7 hits in these rollouts. This audit was post hoc,
never used for tuning, and did not change the threshold, policies or cohorts.

These two targets appeared in the previous study. Outcomes therefore support a
prior-exposed retrospective diagnostic, not fresh confirmatory evaluation. Target
aliases/patent families and cross-target homology are not fully verified. Gate 1
remains open. Chemistry and assay endpoints remain separate; no prospective ASO,
clinical safety, new laboratory measurement or real-dollar saving is established.
No matched two-layer ablation was run, so differences from the historical study
cannot be causally attributed to depth.

## Timing and verification

On the local Apple M4 CPU runtime, the five training/checkpoint-selection/reload
phases took 21.99 seconds combined. The run function, including source preparation,
source fitting, all training and final evaluation, took 27.21 seconds; process
startup, package installation, earlier preflight and tests are outside that timer.
These small-model timings do not apply to LLM fine-tuning.

- Python 3.11.16, Poetry 2.1.4; `make lint format-check import-check test` passed
  with 224 tests, using the repository environment.
- Twelve optional experimental-selection tests passed in the pinned isolated
  scientific/RL runtime, including the actual three-hidden-layer architecture,
  deterministic before-save/after-load ledger equality, exact pool caps, paired
  budgets, hidden-label/sentinel poisoning, posterior math and acquired-only fits.
- All 80 final ledgers passed unique-purchase, seed-cost, reward, remaining-budget
  and fit-label-count audits. The acquisition seal matches the saved ledgers with
  deferred sentinel fields removed; all executed source hashes match their receipt.
- Raw Atlas release/cleaned/fold hashes were verified. The optional RL group was
  resolved into the Poetry lockfile; every previously retained package version
  stayed unchanged. `poetry check --lock` passes with existing metadata warnings.
- No trained RL weights, generated run artifacts or source data were added to Git.
  No remote CI, commit or push is claimed.

## Local artifacts

`artifacts/experimental-selection-600/run-v1/` contains the report, 80 episode
ledgers, two seals, source prior/parameters, execution/source hashes, five policy
checkpoints/manifests/reload probes, comparison figure and post-hoc pool audit.
The parent directory contains the metadata-only manifest and complete installed
runtime package inventory. Outputs are ignored and existing paths are not overwritten.

Main files:

- `report.json`, `episodes.json`, `comparison.png`
- `partition_manifest.json`, `source_prior.json`, `source_parameters.npz`
- `policy_seal.json`, `acquisition_seal.json`, `posthoc-pool-audit.json`
- `policy-613/` through `policy-617/`: checkpoints, receipts and reload probes

Reproduction commands are in the frozen protocol. The honest conclusion is that
three-layer expert-selection PPO is competitive with updated greedy here, but
the requested experiment supplies no reason to replace greedy with it.
