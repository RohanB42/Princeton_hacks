# Model-informed active-learning development

Authorized by the user's instruction to proceed with development, November 14,
2026. This is a new Huesken GP study; the completed CNN pilot is preserved.

## Status and interpretation

The expanded published-best-model reproduction remains 4/7 within the original
0.03 tolerance. The incoming 30-seed linear/RF reassessment does not close this
seven-dataset requirement; its direct RF depth setting also differs from the
benchmark factory's effective arguments. The new runner preserves measured
**diagnostic** provenance. Huesken has informed prior development, so a new seed
set is not fresh biological confirmation. Target-held-out and cross-dataset
replications remain subsequent studies, not implemented claims.

## Frozen development protocol

- Dataset: all 2,431 released Huesken rows, unchanged labels, source-verified bytes.
- Official nucleobase splitter at pinned revision 97f5b9f; original executable
  global NumPy seeding convention. Complete splits persisted before acquisition.
- Five development seeds: 200–204. Smoke uses seed 200 and checkpoints 50/100.
- Initial 50 uniformly acquired rows; RNG separate from acquisition.
- Predictor: stateless 42-position, five-base one-hot GP. Select among the existing
  six kernel candidates using only the initial 50 labels, sorted by immutable ID.
  Three-fold GroupKFold by target; if fewer than three populated groups exist,
  shuffled three-fold KFold with the campaign seed. Mean RMSE selects the winner;
  grid order breaks ties. Numerical failure fails the run rather than silently
  selecting a different candidate. Selected family/initial scale shared by all
  policies within a seed; marginal-likelihood parameters refit on acquired labels
  at every checkpoint. No prior full-pool kernel-selection result is consumed.
- Random, diversity, latent-GP-uncertainty and hybrid, all with the same predictor.
  Diversity uses L2-normalized fixed one-hot features. Hybrid first chooses floor
  (batch/2) highest-uncertainty records, then greedy max-min coverage using labeled
  records plus that selected subset as centers. Odd extra slot goes to diversity.
- Checkpoints: 50-step increments through 1,000; then 1,250, 1,500 and full pool,
  retaining only eligible tail budgets. Pools below 1,000 fail before acquisition.
  Tail batch sizes are deliberately larger and saved explicitly. Smoke stops at100.
- Fresh estimator per checkpoint, canonical fitting order, deferred test scoring.
  Independent full-pool reference shared only across matching policy/seed pairs.
  GP latent uncertainty remains uncalibrated; its usefulness is an empirical question.

## Analysis

Primary: paired normalized Pearson AULC, hybrid minus random, over 50–1,000 labels.
Smoke AULC spans 50–100 and must never be presented as the primary study result.
Secondary policies are explanatory, not a post-hoc winner-selection opportunity.
Report Pearson, RMSE and MAE curves, means and sample SD with contributing n.

Near-full threshold is each reference r minus0.03, provided reference r>0.03.
Use the first observed checkpoint crossing; no interpolation. Otherwise record
not_reached, or undefined_or_uninformative_reference. Paired savings are
1 - hybrid_labels/random_labels only when both cross. Show all threshold-status
counts alongside contributing-pair counts; do not summarize a censored subset as
an unconditional saving. Proposed practical target:20% savings. No automatic
success verdict or significance claim is emitted by this development report.
Overlapping test sets are not independent biological replications. References are
comparators, not guaranteed upper bounds.

## Commands

Run these with the pinned upstream scientific Python, including matplotlib:

```sh
PYTHONPATH=src python -m oligo_engine.active_learning \
  --checkout /path/to/pinned/OligoGym \
  --output artifacts/active-learning-smoke --smoke

PYTHONPATH=src python -m oligo_engine.active_learning \
  --checkout /path/to/pinned/OligoGym \
  --output artifacts/active-learning-development
```

Both commands generate a suite ledger, archived source, copied config, individual
run JSONs, audited report.json and learning-curves.png. Existing outputs are refused.
The suite records failure status and preserves completed campaigns. Resume is not
implemented: diagnose failure and start a separately named attempt.

Tests: core `python -m pytest`; pinned environment `python -m pytest tests/upstream`.
The latter is explicitly excluded from ordinary core collection. Freeze source
before a measured suite; changes during execution fail the final source check.

## Next gates

1. Pass core, pinned-predictor, and measured smoke checks; inspect actual plots.
2. Execute the five-seed development matrix and independently audit its artifacts.
3. Freeze a separate 20-seed evaluation declaration after development; record any
   changes and keep development outcomes separate. No evaluation config exists yet.
4. Extend target-held-out and compatible efficacy datasets with separate contracts.

Never select or change a policy using the fixed evaluation set. Never use
unrevealed training labels for model selection, calibration or stopping. Kernel
selection has its own oracle limited to the same initial50 records; repeated
internal use does not consume additional unique labels.

## Completed five-seed development result

All20campaigns completed. Hybrid-minus-random normalized Pearson AULC over
50–1000labels: +0.005352 +/-0.020786 sample SD. First-threshold savings average
22.737% +/-28.008percentage points; three seeds improve, one ties, one worsens.
Seed202 has unstable low-budget prediction and reaches the reference threshold
only at full pool. This remains an unresolved model-selection/optimization
diagnostic, not grounds to discard a seed. No robust20% savings claim is made.
The separately planned20-seed evaluation has not been run by this study.

Integration names the cached-pool diversity implementation pool_diversity.py to
preserve its normalization and tie behavior alongside the separately developed
featurizer-based diversity.py. Archived execution sources retain the old path.
