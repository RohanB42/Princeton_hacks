# ASO design environment: three bounded checks

November 14, 2026. Assessed main revision `df90bb6` after the user requested about
three tests and an assessment of whether generated candidates are promising.

**Verdict:** useful engineering infrastructure; no demonstrated biological design
advantage. Further development is worthwhile, but chemistry coverage and the
optimizer comparison need attention before more real-model PPO training. A small
retrospective ranking check provides encouraging evidence for classical efficacy
models on recorded assays, not for the environment's generated ASOs.

No production environment, reward, predictor, dataset or dependency lockfile was
changed. New diagnostic script: `scripts/assess_aso_environment.py`. Generated
receipts, policies and plots remain ignored under
`artifacts/aso-environment-review-20261114/`. No commit or push was performed.

## 1. Validity, masks, scoring and reload

The 28 existing focused construction/scoring/search/reward tests passed. In an
isolated pinned RL runtime, all five optional tests passed, including actual PPO
training, scorer/environment parity, budget truncation and saved-policy reload.

An additional deterministic stress probe constructed 100 synthetic transcripts and
ran 500 legal-action episodes:

| Check | Actual count / outcome |
| --- | --- |
| Reachable candidate constructions | 1,511 checked |
| Deliberately corrupted HELM strings | 1,511 rejected |
| Environment transitions | 1,385 checked |
| Observation bounds and finite rewards | 1,885 observations checked |
| Complementarity, MOE/DNA positions, methylcytosine and PS links | Passed |
| Unexpected truncation/nontermination | None |

These checks support deterministic chemical construction and engineering validity.
They do not establish target accessibility, acceptable off-target binding, efficacy
or safety. The tested action set remains STOP/LEFT/RIGHT with fixed chemistry.

## 2. PPO versus search on the shipped synthetic task

Three fresh policies used seeds 7, 17 and 27, each with the existing fixed 2,048-step
recipe. Validation selected checkpoints as implemented; final evaluation followed
without tuning. Every saved policy reproduced its action sequence and candidate
archive after reload. Budgets were 6 or 10 unique scored candidate contexts and
100 requests per method. Each optimizer used a separate cache.

| Method | Mean best utility, cap 6 | Mean best utility, cap 10 |
| --- | ---: | ---: |
| Unchanged start | 0.150 | 0.150 |
| Random | 0.917 | 0.950 |
| Greedy/local | 0.550 | 0.950 |
| Integer genetic | 0.950 | 0.950 |
| PPO | 0.650 | 0.950 |

PPO reached the known optimum in all three seeds at cap 10, using nine unique final
scores. Each policy additionally used 2,250–2,275 training requests, ten unique
training candidate-context scores and 20 training head calls; validation added 36
requests. These costs are not included in the final rollout cap and must be reported
when comparing total optimization effort. Caching reduces actual model calls but
does not erase policy-training cost.

**Important comparison limitation:** PPO starts at site 1 and moves ±1; the optimum
is at site 9. Counting the reset, it requires at least nine unique scores to reach
that optimum. With six scores it can reach at most site 6, utility 0.65. All three
policies achieve that bound. Random and genetic search can jump directly to any
site in the reachable region. Thus the small-budget comparison mixes search-policy
quality with proposal/movement restrictions; it is not evidence that PPO learned
poorly. The methods share a candidate domain but not identical action access.

For a controlled algorithm comparison, either give PPO equivalent proposal access
or enforce comparable local moves/costs on controls. A practical end-to-end method
comparison may intentionally retain different proposal mechanisms, but must state
that scope. Include both final inference and amortized/total training costs.

The task itself is very weak evidence: the synthetic score increases with site
position, and train/validation/final transcripts have identical periodic sequences
with different IDs. Repeated sequence/chemistry can earn different position-based
rewards. This is an explicit toy oracle, not a biological model or a meaningful
test of new-target generalization. Matching its optimum shows the wiring works.

## 3. Are promising candidates assessable with existing evidence?

### Exact chemistry support

The environment fixes 19 bases, 5 MOE / 10 DNA / 4 MOE sugars, full PS internal
linkages, methylated cytosines and no terminal phosphate. We parsed chemical tracks
and compared normalized chemical identities, not raw HELM spelling.

| Audited partition | Total rows | 19-mer rows | Exact environment-template matches |
| --- | ---: | ---: | ---: |
| Atlas eligible source-training pool | 95,638 | 316 | **0** |
| Atlas F7 development test | 161 | 0 | **0** |
| Atlas STAT3 development test | 132 | 0 | **0** |
| Atlas NLRP3 development test | 493 | 0 | **0** |
| OligoGym MOE neurotoxicity structures | 2,437 | 2,006 | **26** |

No Atlas source row even has the exact 5/10/4 sugar arrangement. The most common
source 19-mer pattern is 5 MOE / 9 DNA / 5 MOE (181 rows). Among MOE neurotoxicity
19-mers, many 5/10/4 examples use mixed linkages: 784 rows have 12 PS and 6 PO links,
and 596 have 13 PS and 5 PO. Only 26 fully match the environment template.

This is absence of direct support in the audited pool, not proof the template is
biologically invalid or unlearnable. It means a broad `ps_moe_gapmer` applicability
label is insufficient to demonstrate coverage. Parsing successfully also does not
establish predictive validity. Audit fine-grained lengths, sugar patterns,
methylation, linkage patterns and assay conditions when choosing a production
profile. The result does not describe every Atlas endpoint or the entire release.

MOE outcomes were not analyzed or used to fit a model in this check. Seven reserved
Atlas campaigns were not read for outcome analysis. No matching surrogate efficacy
and safety domain is established by these counts.

### Measured ranking diagnostic

It was feasible and inexpensive to assess existing, saved Ridge predictions on
already-scored development test assays. Before loading their endpoint values, the
script fixed two arms (target-only Ridge; 5% source Ridge plus target offset),
the fixed/all-200 target protocol, top 20 rows per target/seed, and deterministic
prediction/ID tie handling. No models were refitted or settings selected.

The comparison is the measured mean inhibition of the selected top 20 minus the
mean of all eligible held-out rows, which is the expected mean of a uniformly
random 20-row selection. Means below average three seeds within each target.

| Development target | Source Ridge + offset lift | Target-only Ridge lift |
| --- | ---: | ---: |
| F7 | +9.08 percentage points | +7.46 percentage points |
| STAT3 | +9.17 | +14.45 |
| NLRP3 | +10.88 | +9.38 |
| Equal-target mean | **+9.71** | **+10.43** |

Across the equal-target mean, random selection expects 51.70% inhibition; selected
rows average 61.41% for source Ridge and 62.13% for target-only Ridge. Differences
are positive in all nine target/seed records for each model. These are three reused
development targets, not nine independent biological replications; no confirmatory
significance or prospective discovery claim is made.

This diagnostic suggests useful efficacy-ranking signal for recorded assay rows
in their supported data setting. It is not validation of PPO, new target windows,
zero-label targets, or the current 19-mer generated panel. Every comparison uses
200 target measurements for fitting/calibration. Rows may repeat compounds across
assay contexts; this is not a verified 20-distinct-molecule panel. No eligible exact-
template test rows existed for a corresponding environment-specific ranking test.

## Decision and next work

The assessment was worth doing: it found useful engineering behavior, a movement-
budget confound, and a chemistry-coverage mismatch before expensive optimization.

Proceed with:

1. Select a chemistry/length/linkage profile supported by the intended efficacy
   model and applicable risk evidence, or explicitly validate extrapolation to the
   current profile. Do not silently change chemistry to make a score attractive.
2. Package the selected classical model with fitted transforms, exact supported
   contexts, split/label provenance and inference parity probes. Existing local
   research artifacts are useful evidence but not yet a validated production bundle.
3. Build a measured candidate-ranking benchmark with molecular/assay identities,
   predefined shortlist criteria and fresh locked evaluation. Keep unknown safety
   endpoints unknown and validate screens before making them required.
4. Repair or explicitly qualify proposal-access differences in optimizer comparisons.
   Then evaluate diverse landscapes/targets and both total and deployment costs.

Do not expand PPO training merely to obtain more toy reward. No current evidence
justifies calling the environment's generated ASOs biologically promising. The
measured ranking result supports further work on the predictor/selection stage.

## Reproduction and artifacts

The optional runtime was installed in
`/private/tmp/oligoal-aso-review-20261114-env`, leaving existing environments untouched.
Its direct RL pins match the repo: Gymnasium 1.1.1, SB3/sb3-contrib 2.6.0,
PyTorch 2.3.1, NumPy 1.26.4. The measured audit used the existing Atlas runtime.

```sh
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export MPLCONFIGDIR=/private/tmp/oligoal-aso-review-mpl
review_python=/private/tmp/oligoal-aso-review-20261114-env/bin/python
atlas_python=/private/tmp/oligoal-atlas-rnafm-20261114/.venv-atlas/bin/python
"$review_python" scripts/assess_aso_environment.py structural --output artifacts/aso-review-rerun
"$review_python" scripts/assess_aso_environment.py optimizers --output artifacts/aso-review-rerun
"$atlas_python" scripts/assess_aso_environment.py measured \
  --atlas-root /private/tmp/oligoal-atlas-lora-scaling-20261114/artifacts/atlas-rnafm \
  --output artifacts/aso-review-rerun
```

Use a new directory; completed phase receipts are not overwritten. Actual receipts:
`structural.json`, `optimizers.json`, per-method/seed/budget archives, and
`measured-final/measured.json` in `artifacts/aso-environment-review-20261114/`.
The earlier measured receipt is preserved; the final one adds the MOE structural
audit. The initial script version for the first two receipts is retained under
`provenance/`; each receipt records its script hash and source revision/dirty status.
Figure: `assessment.png`, generated by the local `plot.py` and visually inspected.
Error bars are sample standard deviations over three seeds, not confidence intervals.
