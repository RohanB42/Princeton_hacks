# Three-layer PPO width comparison: 64 versus 32 neurons

User-authorized follow-on to the completed
[32-neuron protocol](experimental-selection-600-protocol.md). This extension is
fixed before training the wider policies. The user requested increasing each of
the three hidden layers to 64 neurons. No further search over width, depth, rewards,
seeds, step budgets, targets or thresholds is authorized by this profile.

The new configuration is `configs/experimental_rl/atlas_600_3layer_64.toml`.
Only `hidden_layers` differs from the original configuration: `[64, 64, 64]` replaces
`[32, 32, 32]`. Apply this to actor and critic. All five policy training seeds
(613–617), 8,192 steps each, checkpoint-selection rules, five replay seeds, three
training targets, two development targets and two evaluation campaigns stay fixed.
Every evaluation campaign has the same 600 candidate IDs and initial measurements,
50 assay purchases, and hit definition strictly above 80 inhibition percentage
points. Source Ridge, features and acquired-only online updates are unchanged.

Before fitting, verify candidate, sentinel and initial-ID memberships against the
saved width-32 manifest. Partition digests include the full run configuration and
will differ by design; compare the actual memberships, not just those digests.
After execution, require identical source-prior identity and identical random,
updated-greedy and frozen-ranking acquisition ledgers across width runs. Freeze
all five wider checkpoints using development outcomes before final replay.

Primary width contrast: 64-neuron PPO minus 32-neuron PPO in target-macro new hits
at fifty assays. Also retain comparisons to updated greedy, random and source
ranking. Average all policy seeds; do not choose the best seed on final outcomes.
Report per-target and per-policy-seed results, action frequencies, parameter count
and measured training time. This is a requested exploratory follow-on after seeing
the narrower model's results, using two previously exposed evaluation targets.
It is not a fresh confirmatory test or a significance/generalization claim.

The previous source code and generated artifacts remain preserved through their
existing receipts. Wider policies and their artifacts use a new ignored directory:
`artifacts/experimental-selection-600-width64/run-v1`. Do not overwrite old outputs.
No laboratory experiment or dollar expenditure is performed; the user-approved
50-assay replay budget retains an unresolved $30,000 dollar mapping. Gate 1 and
endpoint/provenance restrictions are unchanged. No LLM is trained.

```sh
PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  MPLCONFIGDIR=/private/tmp/oligo-mpl-cache \
  .venv-experimental-rl/bin/python -m oligo_engine.experimental_rl run \
  --config configs/experimental_rl/atlas_600_3layer_64.toml \
  --output artifacts/experimental-selection-600-width64/run-v1
```
