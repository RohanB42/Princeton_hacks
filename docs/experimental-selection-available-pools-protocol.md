# Three-layer, 32-neuron PPO on the largest available evaluation pools

The user requested 6,000 candidates per assay campaign, retaining three hidden
layers of 32 neurons and the existing fifty-assay budget. A metadata-only audit
of all compatible Atlas campaign groups found none with 6,000 distinct recorded
compounds, even before sentinel holdout. The largest eligible human campaign is
NLRP3 with 2,618; PSD3 has 2,226 and SMAD7 has 750 in their selected assay tables.
The exact 6,000-candidate configuration is retained with a failed-preflight receipt.
No outcome reads, predictor fitting or policy training occurred for that attempt.

After this finding, the user explicitly chose the largest existing evaluation
pools: PSD3 1,759 and SMAD7 603. This profile is fixed before the new training and
replay. It does not fabricate extra candidates, promote predictions to measurements,
reuse held-out sentinels or combine incompatible assays to reach 6,000.

## Controlled comparison

Start with `atlas_600_3layer.toml` and add exact evaluation pool sizes:
`PSD3 = 1759`, `SMAD7 = 603`. All training/development membership rules stay fixed
at their previous capacities and identical sampled IDs. Their initial measurements,
source-fit/calibration IDs, feature encoding and source Ridge settings are unchanged.
Only the two final evaluation pools expand to all previously eligible pool IDs;
sentinel memberships stay fixed. Their initial ten assays are sampled from the
expanded pool using the same declared RNG rule, so the initial assays may change.
Within this new comparison, PPO and heuristics receive identical starts and budgets.

Train three layers of 32 in both actor and critic, seeds 613–617, 8,192 decisions
per seed, and the same development-only checkpoint selection. Compare PPO, updated
greedy, frozen source ranking and random, with evaluation seeds 71–75. Freeze all
PPO checkpoints before constructing final acquisition environments. Initial ten
assays count toward fifty total; reward is a new measured inhibition result strictly
above 80 percentage points among the forty selected assays. No other parameter or
threshold search is performed.

Primary contrast: PPO minus updated greedy on target-macro new hits at fifty
assays. Report all methods, targets and policy seeds, and greedy/frozen/random
expert frequencies. Average across replay/policy seeds within target and give each
target equal weight. Do not select a winning policy seed on final outcomes.

Compare source-prior identity and training/development memberships against the
earlier width-32 run. Compare checkpoint parameters for deterministic equality
where feasible. Historical 600-candidate hit counts are context, not a controlled
paired improvement estimate: evaluation pool composition and initial assays differ.

This is an exploratory replay on two repeatedly examined target groups. Previously
observed outcomes make it development evidence, not untouched confirmatory testing.
Gate 1 remains open; there is no wet-lab measurement, clinical safety result, or
verified dollar saving. The $30,000-to-assay mapping remains unresolved.

## Artifacts and reproduction

Configuration: `configs/experimental_rl/atlas_available_3layer.toml`.
New ignored output: `artifacts/experimental-selection-available/run-v1/`.
The impossible 6,000-candidate audit and preflight failure remain separately in
`artifacts/experimental-selection-6000/`. Preserve earlier outputs unchanged.

```sh
PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  MPLCONFIGDIR=/private/tmp/oligo-mpl-cache \
  .venv-experimental-rl/bin/python -m oligo_engine.experimental_rl run \
  --config configs/experimental_rl/atlas_available_3layer.toml \
  --output artifacts/experimental-selection-available/run-v1
```
