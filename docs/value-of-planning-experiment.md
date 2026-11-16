# Executed value-of-planning experiment

November 15, 2026. This is a **model-based, ASO-inspired sensitivity experiment**,
not a measured ASO assay study or a re-evaluation of the existing molecular-design
PPO checkpoints. It asks how much room exists above greedy when the probabilistic
model, observations, assay costs and budget are specified exactly.

**Greedy is Bayes-optimal in 108 of 162 parameter cells.** In the remaining cells,
the maximum attainable improvement is 0.400 expected confirmed discoveries per
four-candidate panel. A simple Bayesian rollout reaches the optimum in 150 cells.
A freshly trained small PPO policy does not beat greedy in this bounded pilot.
These findings distinguish limited planning headroom from failure to learn an
available strategy; they do not establish why the original ASO PPO performed as
it did.

## The model and information boundary

There are four candidates in two independent pairs, (0,1) and (2,3). Each candidate
has a hidden binary label Y: whether it meets a hypothetical fixed discovery
criterion. No IC50 curve, sequence, chemistry or biological outcome is fabricated
as a measured observation. All parameters below are declared sensitivity settings,
not estimates from the ASO datasets.

At any state a policy may purchase one of two assays for an unconfirmed candidate:

- A cheap binary screen costs one unit, with sensitivity and specificity both 0.9.
  It can be purchased once per candidate, yields no confirmed discovery, and
  updates the belief about that candidate and correlated partners.
- A definitive confirmation costs c units and reveals Y without error in this
  idealized model. It awards one discovery if Y=1. It may be purchased directly,
  without a screen, and cannot be repeated. A screened compound still pays the
  full confirmation cost.

STOP is available and yields no further reward. Screens after confirmation are
disallowed. The total assay-cost cap B is fixed; unused budget is allowed and
does not count as a discovery. There is no reward for an unconfirmed prediction.
Each action's cost is deducted before the next choice. The same rules apply to
all methods; the random comparator samples uniformly among affordable assays
until none remain, rather than randomly choosing STOP.

The state contains paid screen/confirmation outcomes and remaining budget. The
belief is the exact posterior over all 16 binary label configurations. The PPO
observation includes this entire posterior, eight observed-history entries, cost
and budget, for 26 numerical features. The sampled hidden configuration exists
only in the simulator, never in the policy observation or action-selection code.
The immediate reward is a newly confirmed hit. Gamma and GAE lambda are one.

## Separating uncertainty, prevalence and dependence

For panel mean prevalence p in {0.25,0.5,0.75}, fixed reference propensity vectors
z are (1,0,0,0), (1,0,1,0) and (1,1,1,0), respectively. Marginal probabilities are

`q_i = (1-u) z_i + u p`.

Increasing u from 0.1 to 0.5 to 1 moves propensities toward their common mean,
increasing average Bernoulli entropy while keeping mean prevalence exactly p.
The actual mean entropy is recorded in each result. At p=0.5 these entropy levels
are approximately 0.2864, 0.8113 and 1 bit. The z values are prior-propensity
anchors, not revealed true labels. The parameterization also changes prior
heterogeneity; it does not independently manipulate every possible notion of
uncertainty or distinguish aleatoric and epistemic uncertainty in empirical data.

Within each pair, the joint prior is a mixture: weight 1-r uses independent
Bernoulli draws; weight r uses a shared U~Uniform(0,1), with Y_i=1[U<q_i]. This
preserves each marginal q_i. The mixture coefficient r is **not** a Pearson
correlation coefficient. The two pairs remain independent. We compare r=0 with
r=0.75 to separate within-pair information transfer from candidate-wise screening.
Screen noise remains fixed, so it is not confounded with the uncertainty axis.

The protocol fixes the full Cartesian grid before execution:

| Factor | Levels |
|---|---|
| Marginal uncertainty strength u | 0.1, 0.5, 1.0 |
| Confirmation/screen cost ratio c | 2, 3, 4 |
| Total cost budget B | 4, 6, 8 |
| Mean hit prevalence p | 0.25, 0.5, 0.75 |
| Within-pair mixture r | 0, 0.75 |

This gives 162 cells. Their equal-weight average is a descriptive summary of this
chosen grid, **not** an estimated distribution of real ASO screening campaigns.

## Algorithms and exact evaluation

For belief-state s, the dynamic program uses

`V*(s) = max(0, max_a sum_o P(o|s,a)[reward(s,a,o) + V*(s')])`.

Every assay is available at most once and costs at least one unit, so the recursion
is finite. States are memoized by observed outcomes; posteriors and transitions
are computed from the fixed joint model. Values are exact expectations up to
floating-point arithmetic, not estimates from a finite sample of simulated worlds.

The comparators are:

1. **Greedy:** confirm the candidate with highest current posterior hit probability.
   Confirmation costs are equal across candidates, so maximizing immediate yield
   per cost gives the same ordering. It updates the full Bayesian posterior after
   every observation; it is not a frozen initial ranking. Cheap screens have zero
   immediate confirmed-hit reward and are not chosen by this policy.
2. **Bayesian rollout:** evaluate each possible next assay, average over its
   possible outcomes, and assume greedy-to-budget completion thereafter. Execute
   the best first action, then recompute this one-step rollout at the new state.
   This is a strong information-aware control, not just immediate-gain greedy.
3. **Random:** uniformly choose among legal affordable assays, with the same
   charged costs and terminal objective.
4. **PPO:** a fresh MaskablePPO controller trained on this exact belief MDP, as
   described below. The old molecular and experimental-selection checkpoints have
   incompatible state/action contracts and were not relabeled as this experiment.

A separate clairvoyant upper bound averages `min(number of true hits, floor(B/c))`
over hidden worlds. It knows every label and therefore cannot be executed under
the allowed information. It is reported separately from the attainable Bayesian
optimum. All evaluated policies satisfy the Bayesian-optimal upper bound.

## Actual planning map

The prespecified primary slice is B=6, p=0.5, r=0.75. Entries are **exact optimal
minus greedy expected confirmed discoveries**, not measured efficacy gains:

| Uncertainty strength | Cost ratio 2 | Cost ratio 3 | Cost ratio 4 |
|---|---:|---:|---:|
| 0.1 | 0.000 | 0.000 | 0.038 |
| 0.5 | 0.000 | 0.000 | 0.150 |
| 1.0 | 0.000 | 0.000 | 0.225 |

This differs from the hypothesized monotonic high-cost disadvantage. With six
cost units, ratios two and three allow three or two direct confirmations. A ratio
of four allows only one confirmation, leaving two units that can buy informative
screens without sacrificing a confirmation. Integer budget allocation and the
number of remaining candidates materially affect planning value. Increasing assay
cost does not uniformly increase or decrease that value.

Across all cells:

- Greedy equals the optimum in **108/162**; it has positive headroom in 54 cells.
- The largest greedy gap is **0.400**, at p=0.5, u=1, r=0, c=3, B=8: greedy 1.000,
  Bayesian rollout 1.400, optimum 1.400, clairvoyant bound 1.625.
- Bayesian rollout equals the optimum in **150/162**. Its maximum remaining gap is
  **0.0785**, at p=0.25, u=1, r=0, c=4, B=8: greedy/rollout 0.500, optimum 0.5785.
  Here a sequence of exploratory decisions can have value that one exploratory
  action followed by greedy completion does not capture.
- Mean greedy headroom is **0.038110**; after Bayesian rollout it is **0.002123**.

Independence between candidates does not itself make greedy optimal when cheap
screens can improve knowledge about an individual candidate. A separate invariant
control sets r=0 and screen accuracy=0.5: screens then provide no information and
greedy matches the optimum at tested budgets, selecting the largest marginal
probabilities. This control is distinct from the informative independent-prior
cells in the map.

All grid cells, including zeros, are in `grid.csv` and sealed `grid.json`. Four
standalone PNG/PDF maps show both coupling settings and both contrasts (optimum
minus greedy; optimum minus Bayesian rollout), with all budgets and prevalences.
The main figure is `planning_gain-coupling-0.75.png` in the artifact directory.

## Fresh PPO pilot and negative result

Three fixed seeds, 2700–2702, each trained for 32,768 decisions using a two-layer
64-unit MLP, rollout length 256, minibatch 64, two epochs per update, learning rate
0.0003, entropy coefficient 0.01, gamma=lambda=1 and one CPU thread. Episodes sample
uniformly from the declared 162-cell grid. No supervised pretraining, model
selection, hyperparameter search or performance-based stopping was used. The fixed
last checkpoint is evaluated on that same task distribution; this is **not** a
held-out parameter-grid generalization study.

The 1,024-step resource profile used excluded seed 2699 and forecast 64.7 seconds,
below the prespecified 180-second launch gate. The three complete fits actually
took 6.40, 6.35 and 7.33 seconds, totaling about 20.1 seconds. They consumed 98,304
training decisions, 71,013 simulated confirmations, 22,461 simulated screens and
217,200 simulated assay-cost units. These are simulator operations, not biological
measurements or paid laboratory experiments. Distinct policy hashes are recorded.

Deterministic argmax deployment is evaluated by exact expectation over every
reachable observation branch. No Monte Carlo error bars are needed for those
conditional expectations; model misspecification and training variability remain.

| Method | Equal-cell mean expected confirmed discoveries |
|---|---:|
| Exact Bayes-optimal DP | 1.298591 |
| Bayesian rollout | 1.296469 |
| Greedy with Bayesian updates | 1.260482 |
| PPO deterministic, each of three seeds | 1.241975 |
| Random assays | 0.691171 |

Each PPO seed ties greedy in 126 cells, loses in 36 and wins in zero. The three
different checkpoints have identical expected-yield values on this grid under
argmax deployment; that does not imply their probability distributions or every
unreached action are identical. Do not interpret the zero spread as proof of
algorithmic certainty. This is a small, short-training diagnostic, not an optimized
PPO comparison or evidence that no RL algorithm can learn the optimal policy.

A posthoc inspected example makes one missed adaptation concrete. For seed 2700
at p=0.5, u=1, r=0.75, B=6 and c=3, PPO first confirms candidate0. If it is positive,
candidate1's posterior becomes 0.875 while candidate2 remains 0.5. Greedy next
confirms candidate1; PPO confirms candidate2. If the first result is negative,
both select candidate2. The sealed `behavior-example.json` records both branches.
This illustrates one failure to exploit available posterior information; it is
not a causal diagnosis of the optimizer, representation or training schedule.

A separately sealed posthoc stochastic-deployment supplement profiled its largest
state case (3,745 states). The full-grid forecast was 142.7 seconds, exceeding its
fixed 90-second gate, so the complete stochastic comparison was **not launched**.
Its status is saved explicitly; no missing stochastic result is imputed from the
deterministic values. The primary deterministic result is unaffected.

## What this tells us about the project

There can be little or no room above a strong greedy policy in some resource and
information regimes. In other regimes room exists, and simple Bayesian rollout
captures nearly all of it in this model. The PPO result can therefore reflect
both limited headroom and incomplete learning of a useful strategy. Neither
explanation should be asserted globally from a comparison against random alone.

To explain the real ASO benchmark, the next study must estimate and validate its
prior dependence, screen fidelity, hit prevalence, assay-cost units and endpoint
definition using permitted development evidence, then freeze an independently
evaluated model/benchmark. The current molecular task maximizes normalized frozen
predictor utility, whereas this study maximizes expected confirmed binary hits.
Their scores and optimal-policy bounds cannot be transferred directly.

The approach builds on established active-search theory; it is not a claim to
invent nonmyopic selection. The requested reference is verified:
[Nguyen, Modiri and Garnett, Nonmyopic Multifidelity Active Search, ICML 2021](https://proceedings.mlr.press/v139/nguyen21f.html).
That work motivates budget-aware multifidelity search; this four-candidate solver
is an independent illustrative model, not a reproduction of its experiments.

## Reproduction and verification

Owned code: `experiments/value_of_planning/{model,environment,runner,stochastic}.py`.
Core invariants: `tests/test_value_of_planning.py`.
Ignored output directory: `artifacts/value-of-planning-v1/`.

```sh
MPLCONFIGDIR=/private/tmp/value-planning-mpl PYTHONPATH=src \
  /private/tmp/oligoal-aso-review-20261114-env/bin/python \
  experiments/value_of_planning/runner.py prepare \
  --output artifacts/value-of-planning-v1
# Repeat with grid, train, then plot instead of prepare.
.venv/bin/pytest -q tests/test_value_of_planning.py
```

Use a fresh directory for reproduction; sealed files refuse overwrite. The
protocol pins implementation hashes, factor levels, primary display slice,
training settings and runtime gate before the grid/training. The stochastic
supplement has its own script/policy hashes and explicitly posthoc scope.

Actual checks: 12 invariant tests pass; Ruff lint/format and whitespace checks
pass. Tests cover prior normalization and fixed marginals, entropy/prevalence
separation, Bayesian posterior expectation, cost conservation/nonrepeat assays,
independent uninformative-screen controls, candidate-permutation invariance,
greedy/rollout/optimal/clairvoyant ordering and full-budget confirmation. The Gym
environment checker passes. Two different sampled hidden worlds give identical
initial observations for the same declared belief. All 486 deterministic PPO
evaluation cells respect the exact optimal bound. Maps were rendered and visually
inspected. No measured endpoint table, current model, shared dependency or active
scientific profile was changed.

## Scope addendum: subsequently supplied V3 handoff

The subsequently supplied Harrison handoff describes an original V3 protocol
that has **not been independently verified against its implementation in this
checkout**. It reports a mandatory $500 single-dose screen; only measured
inhibition strictly above 80 unlocks a $2,000 dose-response curve. Total budget is
$15,000, and a hit requires absolute IC50 <=500 nM. Reported beliefs use EZH2/SPDEF
source-trained inhibition/log-IC50 Ridge models with Bayesian residual updates;
the handoff also reports a Qwen3-4B six-ranker menu and first-letter selection bias.

That is a different decision problem from this executed model. Here confirmation
can be purchased directly, returns a perfect binary label, and has no screen-based
eligibility gate. Screen error, joint priors and their correlations are assumed,
not calibrated to V3. Normalizing by the reported $500 screening cost gives V3 a
confirmation cost of four but a total budget of **30**, outside our 4/6/8 grid.
The shared cost ratio alone does not make the experiments equivalent. The maps
remain mechanistic results under the declared model, not matched V3 forecasts or
a proven explanation of its PPO/Qwen results. No parameters, training runs or grid
results were changed after receiving this handoff.
