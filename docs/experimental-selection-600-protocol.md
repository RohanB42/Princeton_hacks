# Three-layer PPO on 600-candidate assay campaigns

Protocol frozen before new outcome reads and policy fitting on November 14, 2026.
The user explicitly authorized this measured diagnostic and confirmed 600 candidates
per assay campaign, 50 assays total, and an unresolved $30,000 dollar mapping.
This supersedes the LLM-only plan for the present experiment. No LLM is trained.

## Scope and source

Selectively port experimental-selection code from branch commit 1b92731. Do not
restore the retired molecular-design scaffold. Preserve the verified Atlas release,
prepared bytes and all original provenance. Gate 1 remains open. The replay spends
simulated assay counts, not physical dollars; no new laboratory tests are performed.

Retain original source-fit/calibration counts (12,000/2,500), original target/patent/
exact-compound/sequence exclusion rules and original grouped pool/sentinel split.
Keep policy target roles unchanged. Uniformly subsample candidate IDs, without
outcomes, to 600 for each development/evaluation campaign. Exclude an undersized
development/evaluation campaign before fitting. Cap training pools at 600, retaining
smaller original training pools. Never add sentinels to meet capacity.

Metadata-only preflight found these usable pools:

| Role | Target | Original pool | Study pool |
|---|---|---:|---:|
| Train | F7 | 510 | 510 |
| Train | NLRP3 | 2,125 | 600 |
| Train | STAT3 | 562 | 562 |
| Development | DMPK | 994 | 600 |
| Development | PLN | 936 | 600 |
| Evaluation | PSD3 | 1,759 | 600 |
| Evaluation | SMAD7 | 603 | 600 |

DUX4 (372), KCNQ2 (375) and PTBP1 (367) fail the 600-candidate capacity rule.
These exclusions use metadata only. There are only two final target groups; replay
seeds and repeated policy fits are not independent biological replications. These
targets also appeared in the previously reported study, so this is prior-exposed
retrospective diagnostic evidence, not fresh confirmatory evaluation. Patent-family
and cross-target homology independence are not established. The old study already
had some larger pools; this standardizes capacity, rather than claiming every pool
is larger than before.

## Algorithm and fixed comparison

Use V2 online Bayesian linear residual updates around the source-only Ridge prior,
with the original 32-dimensional fixed chemistry features and noise assumptions.
Policy observations remain the original 16 aggregate values. Actions still choose
an acquisition expert; the policy does not directly select from 600 action logits.
The environment resolves that expert to one remaining candidate.

MaskablePPO has three hidden layers of 32 units in both the actor and critic;
output heads are additional. Match the original gamma=1, learning rate 3e-4,
rollout length 256, batch size 64, five optimization epochs and 8,192 environment
steps per training seed. Train all five seeds 613–617. Select checkpoints every
1,024 steps using only DMPK/PLN and replay seeds 71–73; ties keep the earliest.
Do not choose a winning policy seed using final evaluation outcomes.

Compare all policies with random, updated greedy (highest current posterior mean),
and frozen source ranking. The last control explains whether PPO still copies the
source expert. All arms have the same candidates, ten uniformly sampled initial
measurements and total budget of fifty, paired over replay seeds 71–75. Initial
measurements spend budget but do not earn new-hit credit. A hit is a newly purchased
distinct compound with recorded inhibition strictly above 80 percentage points.
No efficacy threshold or assay-context mapping is retuned from final results.

Primary contrast: three-layer PPO minus updated greedy in new-hit count at 50
assays. Secondary: random contrast, fixed-source contrast, new hits versus assay
count, expert frequencies, per-target results, training-seed variation, and deferred
sentinel prediction metrics. Average replay seeds and policy training seeds within
target, then equally weight targets. Paired target bootstrap intervals are
descriptive with only two groups and cannot establish generalization. No assertion
that depth alone caused a difference: a matched two-layer ablation is not run.

## Integrity, artifacts and reproduction

Pin optional packages in an isolated runtime and record package versions, source
file hashes, code-file hashes, dirty code status, seeds, configuration, partition,
prior and policy identities. Save each policy, development history, deterministic
reload probe and complete measured purchase ledger under ignored artifacts.
Freeze all policy checkpoints before constructing any final acquisition environment.
Final campaign pool labels may be revealed for that episode's purchases and online
belief update only; they never train/select the PPO policy. Sentinel labels are
loaded only after every acquisition decision has completed and never become reward.

Test environment budgets, seed accounting, exact caps, target exclusion, atomic
oracle access, duplicate acquisitions, hidden-label poisoning, reset isolation,
posterior math, paired comparisons, the actual three-layer architecture and
deterministic checkpoint reload. Run core repository checks and optional science/
RL tests. Report actual results including negative results and execution failures.

Install using Poetry 2.1.4 with `science,reporting,experimental-rl` optional groups.
The executed isolated runtime may be created using uv with the same pinned versions;
its complete installed-package inventory is saved with the result.

```sh
PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  MPLCONFIGDIR=/private/tmp/oligo-mpl-cache \
  .venv-experimental-rl/bin/python -m oligo_engine.experimental_rl prepare \
  --output artifacts/experimental-selection-600/manifest.json
PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  MPLCONFIGDIR=/private/tmp/oligo-mpl-cache \
  .venv-experimental-rl/bin/python -m oligo_engine.experimental_rl run \
  --output artifacts/experimental-selection-600/run-v1
```

The pinned implementation uses the verified [MaskablePPO 2.6 interface](https://sb3-contrib.readthedocs.io/en/v2.6.0/modules/ppo_mask.html).
