# PPO incremental value: completed diagnostic and next attribution experiment

Status: November 15, 2026. The artifact-only diagnostic below is **executed**;
additional policy training and mechanistic ablations are **proposed, not run**.
The diagnostic uses the original six-target v3 study. Any subsequent two-target
extension is a separately sealed development supplement, not a retroactive change
to these target groups or estimates. These are frozen-predictor search outcomes,
not measured molecular efficacy, validated safety or biological discoveries.

## What is now established

The revised system uses its scoring budget successfully. All 360 saved evaluations
completed their exact request cap, including the shared starting design. The
selected PPO policy does **not** show a consistent incremental eight-request
advantage over its exact staged pretrained initialization. Among the four original
policy-development targets, mean PPO minus staged-pretrained terminal utility is
−0.006283 at eight requests and +0.006283 at 32. PPO's much larger eight-request
advantage over a simpler pretrained ranking controller is largely FGFR4-specific
and nearly disappears by 32 requests. The evidence supports a useful learned
search pipeline, with PPO's incremental contribution still unresolved.

These comparisons do not evaluate the retired no-COMMIT policy. Every method in
this study queried complete designs, so previous construction failures cannot
explain this particular result.

## Sealed execution and integrity checks

The executable analyzer is `scripts/molecular_ppo_attribution.py`. It froze
`artifacts/molecular-ppo-attribution-v1/protocol.json` before the new numerical
analysis. The freeze explicitly states that the parent outcomes were already
inspected. A new seal does not turn post-hoc analysis into preregistered confirmation.

The analysis verifies all 360 sealed run receipts, their complete durable journal
chains, result-index identities, the complete target × method × budget × seed grid,
matching campaign/registry/start identities for contrasts, exact cap completion,
no duplicate proposals, finite nondecreasing quality, all five selected and
pretrained weight hashes against training receipts, training-only membership of
pretraining examples, and checkpoint-selection records. Training/validation query
counts and PPO head-call costs are independently checked against sealed journals.
No policy model is deserialized, no predictor is called, and no measured label is
read. Model archives are read only as bytes for hash verification.

A transparent `code-amendment.json` records one correction after the initial
analysis failed closed: event `head_calls` is cumulative within each episode, so
costs must sum the final cumulative counters of each episode, including the partial
last episode, rather than sum every event counter. No input, estimand, contrast,
resampling rule or outcome was changed; the failed attempt wrote no analysis
result. The original protocol remains preserved.

Generated outputs, intentionally ignored by Git:

- `analysis.json`: all 360 trajectories, per-target contrasts, crossed resampling
  summaries, offline costs, checkpoint histories and cross-budget prefix audit.
- `eight-request-trajectories.md`: all requests 1–8, all six targets, all six arms.
- `eight-request-trajectories.png` and `.pdf`: mean curves for PPO, staged pretrained,
  prior ranking, random and greedy, with all eight request ticks. Curves show means,
  not confidence bands; per-request sample SD and seed trajectories remain in JSON.

Reproduction from the repository root, using an installed NumPy/Matplotlib runtime:

```sh
PYTHONPATH=src python scripts/molecular_ppo_attribution.py freeze \
  --output artifacts/molecular-ppo-attribution-reproduction
PYTHONPATH=src python scripts/molecular_ppo_attribution.py analyze \
  --output artifacts/molecular-ppo-attribution-reproduction
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_molecular_ppo_attribution.py
```

Outputs are created exclusively: use a new output directory for a fresh execution.
The eight invariant tests cover missing trajectories, repeated proposals,
nonmonotone/nonfinite quality, invalid pairs, shared seed resampling, journal
integrity, and cumulative per-episode head-call accounting. Ruff check/format pass.
The saved plot was visually inspected.

## Terminal outcomes and attribution

All entries below are means over five paired seeds, 800–804. “Warm” is the exact
saved staged policy before PPO; “ranking” scores complete candidates using that
same pretrained molecular head and directly queries its descending ranking.

| Target | Original policy role | PPO, 8 | Warm, 8 | Ranking, 8 | PPO − warm, 8 | PPO − ranking, 8 |
|---|---|---:|---:|---:|---:|---:|
| DGAT2 | Training | 0.8884 | 0.8884 | 0.8884 | 0.0000 | 0.0000 |
| CFB | Checkpoint validation | 0.7205 | 0.4872 | 0.7982 | +0.2333 | −0.0778 |
| FGFR4 | Inspected development | 0.6943 | 0.7094 | 0.2657 | −0.0151 | +0.4286 |
| F9 | Development | 0.9578 | 0.9578 | 0.9578 | 0.0000 | 0.0000 |
| F12 | Development | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| TTR | Development | 0.6944 | 0.7045 | 0.6843 | −0.0101 | +0.0101 |

| Target | PPO, 32 | Warm, 32 | Ranking, 32 | PPO − warm, 32 | PPO − ranking, 32 |
|---|---:|---:|---:|---:|---:|
| DGAT2 | 0.8884 | 0.8884 | 0.8884 | 0.0000 | 0.0000 |
| CFB | 0.8266 | 0.7205 | 0.8266 | +0.1061 | 0.0000 |
| FGFR4 | 0.7395 | 0.7244 | 0.7395 | +0.0151 | 0.0000 |
| F9 | 0.9597 | 0.9597 | 0.9578 | 0.0000 | +0.0019 |
| F12 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| TTR | 0.7246 | 0.7145 | 0.7246 | +0.0101 | 0.0000 |

The strong CFB improvement over the staged warm-start policy is on checkpoint
validation data, and the pretrained ranking controller is stronger there at eight
requests. CFB therefore cannot supply an independent claim that PPO generalizes.
DGAT2 is training data. F9/F12/TTR were excluded from policy fitting/selection in the
original study, but all reported targets are now inspected development evidence.
None is established as unseen by every supervised reward head.

Initial utility is zero on five targets and **0.595884 on TTR**, identical across
all paired arms/seeds. Consequently, TTR PPO's terminal 0.694396 at eight requests
represents only +0.098511 gained utility, not 0.694396 newly discovered utility.
F12 remains in every aggregate: a zero result under the fixed surrogate screen is
not missing data and is not measured evidence of molecular toxicity.

## The full trajectories change the interpretation

The secondary AUC here is the trapezoidal area over actual request indices 1…B,
divided by B−1. It includes the charged common start, uses no padding or interpolation
of missing observations, and is explicitly different from final utility.
The reward was designed to optimize terminal archive quality, not this AUC.

| Target, eight-request run | PPO − warm terminal | PPO − warm AUC | Implication |
|---|---:|---:|---|
| CFB | +0.233275 | −0.121091 | PPO overtakes late; warm finds useful designs earlier |
| FGFR4 | −0.015061 | +0.152890 | PPO finds useful designs earlier, but warm finishes slightly higher |
| TTR | −0.010070 | −0.006011 | Small disadvantage on both metrics |

Do not switch the primary outcome to AUC because FGFR4 looks better on that metric.
These are complementary descriptions of the same trajectories.

Budget-8 and budget-32 policies are evaluated with their own declared horizon in
the observation. Six of 30 staged warm-start pairs differ in their first eight
proposal identities across budgets (one CFB, one F9, three F12 and one TTR); one
architecture-control TTR pair also differs. All full-PPO, random, greedy and prior
ranking prefixes happen to match in the current receipts. Therefore the 32-request
study is a separate horizon evaluation, not automatically a literal continuation
of an eight-request run. The saved eight-position plot uses the actual budget-8
runs throughout.

## Seed and target uncertainty

The unit structure is crossed: the same learned policy seed is evaluated on every
target, while each target supplies a distinct molecular search problem. Queries,
grammar actions and designs from a run are not independent replicates. Neither are
five target evaluations from one policy five independently trained policies.

The descriptive aggregate uses the four original development targets with equal
target weight. It excludes training DGAT2 and validation CFB without hiding their
separate results. A two-way sensitivity bootstrap resamples target rows and whole
policy-seed columns, preserving the same sampled seed indices across targets.
There are 10,000 draws with a fixed diagnostic RNG seed. The resulting central 95%
ranges below are **not confirmatory confidence intervals** for new targets and are
not a significance test. Four already-inspected targets and five seeds cannot
justify population-level precision; target-family dependence could reduce the
effective number of target groups further.

| Budget | Contrast | Mean | SD of seed-averaged effects | Crossed resampling sensitivity range |
|---|---|---:|---:|---:|
| 8 | PPO − staged pretrained | −0.006283 | 0.019354 | [−0.030144, +0.011296] |
| 8 | PPO − pretrained ranking | +0.109676 | 0.100742 | [0.000000, +0.359720] |
| 32 | PPO − staged pretrained | +0.006283 | 0.008881 | [0.000000, +0.022592] |
| 32 | PPO − pretrained ranking | +0.000482 | 0.001077 | [0.000000, +0.002890] |

The zero lower endpoints in several sparse-effect ranges are a feature of empirical
resampling of this tiny discrete dataset, not proof of a nonnegative population
effect. No confirmatory p-values or “statistically significant improvement” claims
are produced.

## Training cost and checkpoint selection

| Seed | Pretraining requests | PPO requests | Selection requests | Selected PPO decisions |
|---|---:|---:|---:|---:|
| 800 | 576 | 4,730 | 192 | 4,096 |
| 801 | 576 | 4,922 | 192 | 4,096 |
| 802 | 576 | 4,445 | 192 | 8,192 |
| 803 | 576 | 4,493 | 192 | 4,096 |
| 804 | 576 | 4,598 | 192 | 16,384 |
| Total | 2,880 | 23,188 | 960 | — |

PPO's complete fitted-and-selected pipeline spent **27,028 offline scoring
requests**, compared with 2,880 for the five pretrained policies: approximately
**9.39×** the query cost, before the common deployment evaluations. These are model
queries, not biological labels. PPO training used 46,376 head calls; pretraining
used 5,760. Validation queries are separate. The larger compute cost is not charged
silently to the eight-request deployment cap. With mean overhead 4,829.6 extra
queries per seed, amortization across M future campaigns adds 4,829.6/M queries per
campaign versus no PPO. A practical efficiency claim needs an explicitly chosen
M and a decision-relevant utility benefit; neither is established here.

| Seed | Validation Q at 4,096 | 8,192 | 12,288 | 16,384 |
|---|---:|---:|---:|---:|
| 800 | 0.7596 | 0.7271 | 0.6162 | 0.7141 |
| 801 | 0.8830 | 0.7453 | 0.7271 | 0.7453 |
| 802 | 0.6162 | 0.7944 | 0.6892 | 0.6219 |
| 803 | 0.7540 | 0.7453 | 0.7453 | 0.7453 |
| 804 | 0.6948 | 0.7335 | 0.6219 | 0.7360 |

The earliest maximum is correctly selected in every receipt, but zero-step
pretraining was never offered to that selector. Selected-policy quality therefore
cannot answer whether training past zero was useful under the same selection rule.
Only `warm-start-policy.zip`, `selected-policy.zip` and `last-policy.zip` remain;
intermediate validation scores survive, but all intermediate weights do not.
Existing intermediate validation receipts can describe the above learning curve;
they cannot supply missing fixed-prefix development evaluations. This diagnostic
does not run additional inference using the surviving last checkpoint.

## What can and cannot be attributed

1. **Budget use:** all arms used the same full deployment query cap. Underuse is
   ruled out as the explanation for their current differences.
2. **Pretraining plus molecular representation:** the exact pre-PPO policy already
   performs strongly. This is useful engineering evidence for the learned pipeline.
   Full-versus-architecture changes data, pretraining, decision collapsing and
   training budget, so that comparison cannot isolate the causal value of any one.
3. **PPO refinement:** full-versus-warm holds the initialization and architecture
   fixed, but adds on-policy queries, optimizer updates and validation selection.
   Its result is the incremental effect of that full refinement procedure, not an
   isolated advantage of the PPO objective at equal information or compute cost.
4. **Ranking versus sequential adaptation:** direct ranking and staged policies
   differ in grammar marginalization, administrative actions and context-sensitive
   residuals. The staged warm network has not learned those residuals with PPO.
   Its advantage over direct ranking cannot establish learned history adaptation.
   PPO also updates the molecular encoder and prediction head, so improved static
   molecular ranking is a competing explanation for any PPO gain.
5. **Biology:** every arm optimizes the same frozen predictor/screen. Independent
   evaluator and measured endpoint validation remain separate open requirements.

## Next executable development experiment

This is a concrete run specification, not an assertion that missing runner features
already exist. The integrator must add and test the listed interfaces before launch.
Keep the frozen molecular profile, reward, surrogate checkpoints, masks, deployment
starts and caps unchanged; this study cannot simultaneously change the objective
or scientific predictor. Use five newly reserved development seeds **1800–1804**,
with no outcome-based extensions. Freeze an exposure manifest before any queries.

The study follows the data-diversity comparison in
[molecular-policy-data-scaling.md](molecular-policy-data-scaling.md). If its broader
24-gene, 72-window catalog passes metadata/split checks, use that same fixed catalog
for both 576 and 2,304 pretraining examples. Otherwise run the explicitly documented
feasible catalog and limit the claim; do not silently change the target count or
use reserved evaluation targets to fill it. All current six reported targets,
including newly supplemented development targets if inspected, remain development
only. Confirmation requires different target/family groups and an independent
assessment protocol after this experiment is complete.

| Factor | Frozen development levels |
|---|---|
| Pretraining count | 576 and 2,304 on the same qualified training catalog |
| Policy seeds | 1800, 1801, 1802, 1803, 1804 |
| PPO fixed decision prefixes | 0, 4,096, 16,384 |
| Deployment scoring cap | 8 primary; 32 secondary |
| Training episode cap | 8, with identical common starts and construction allowance |
| Pretraining update budget | Fixed by the preceding diversity study, not selected using these results |
| PPO optimizer | Existing pinned v3 configuration, including batch 64 and gamma = lambda = 1 |
| Primary attribution outcome | Equal-target mean terminal utility at 8 requests |
| Primary contrast | Fixed 16,384 PPO prefix minus exact staged zero-step initialization, at 2,304 pretraining examples |

This requires ten longest PPO trajectories (two pretraining counts × five seeds),
each retaining its zero-step, 4,096 and 16,384 states. These are paired prefixes,
not 30 independently trained policies. Every prefix needs a distinct immutable
inference archive and a complete exact-resume checkpoint, with RNG, optimizer,
normalizer, environment, partial episode and rollout identities preserved.
Validation execution must not perturb the training RNG stream.

Run and report four distinct analyses rather than conflating their advantages:

- **Fixed-prefix learning curve:** evaluate all three saved prefixes. Report the
  primary 16,384-minus-zero contrast above, with 4,096 and the smaller-pretraining
  tier as explicitly secondary results. No validation maximum is substituted for
  the fixed final prefix.
- **Deployment selection:** evaluate the same validation campaigns at 0, 4,096 and
  16,384. Select the earliest maximum, including zero as a valid winner. Report this
  selected deployment strategy separately from fixed-prefix results. Every policy
  family receives the same scheduled selection opportunities; account for actual
  scoring and repeated evaluation cost.
- **No-PPO controls:** at every seed/count retain exact staged zero-step and direct
  pretrained ranking, plus random and greedy. Also apply direct ranking to each
  saved PPO molecular head. This last control tests whether static molecular-head
  refinement explains a gain without claiming that removing the controller alone
  proves or disproves an RL mechanism. The spec-required evolutionary, sweep and
  exhaustive controls remain a separate general optimizer comparison; their absence
  here limits this to attribution, not a complete final benchmark.
- **Extra-pretraining query control:** fork the exact zero-step initialization, give
  it Q additional training-oracle requests where Q is its paired PPO run's observed
  training-query expenditure, and update only the pretrained molecular predictor.
  Q is obtained from expenditure, never evaluation utility. Select fresh training
  candidates from a frozen seed-specific uniform permutation, without replacement
  until the eligible training catalog is exhausted. Report unique examples,
  logical queries and saturation separately. After exhaustion, any repeated-query
  cost matching is explicitly labeled repeated information; it cannot be credited
  as extra data. Match the supervised gradient-update schedule to the paired PPO
  optimizer-update count, and separately report wall time/FLOPs because equal
  update counts do not make unlike objectives equal compute. Retain both staged
  and direct-ranking deployments of this supervised control.

The cost control's required additional samples may exceed the finite 6,408-design
catalog even in the broad tier. This is a prespecified saturation outcome, not a
reason to expand training membership after viewing performance. A reuse-of-PPO-data
supervised control can additionally isolate update rule at exactly the same queried
molecules, but its data are selected by PPO and its collection cost remains charged
to PPO; it is a mechanism diagnostic, not a standalone cheap sampling strategy.

Minimal implementation interfaces before execution:

1. Snapshot naming by fixed decision prefix, including prefix zero; immutable
   selected-checkpoint manifest pointing to a saved snapshot rather than overwriting
   the only intermediate model. Test prefix identity and exact-resume continuity.
2. Zero-step validation and an earliest-maximum selector shared by all arms. Test
   that a superior zero-step model is selected and that ties prefer the smaller cost.
3. Pretraining from an explicitly sealed query dataset with an exact update budget,
   an explicit optimizer-state fork contract, and nested count membership. Test
   training-only exposure, no evaluation identities and query charging on repeats.
4. A cost-matched control runner recording both logical and distinct queries,
   realized updates, saturation and the complete paired policy lineage.
5. Equal-target aggregation with policy seed shared across all target groups; region
   replicates nested within target, never treated as extra independent targets.

The primary result remains descriptive development evidence. Report all five seed
pairs and all frozen targets, even when no policy finds an eligible design. Do not
claim PPO advancement from improvement over random alone: require a practically
meaningful, stable development improvement over both strong no-PPO deployments and
the matched additional-pretraining control before planning a larger confirmatory
PPO study. Choose the meaningful-effect margin and independent target-group sample
size before that final study; do not tune either to make this inspected experiment
look significant. If the pretrained controller remains strongest, retain it as the
scientifically supported solution rather than extending PPO until it wins.
