# ASO experimental selection: consolidated results and assessment

**Snapshot:** November 15, 2026. This report combines the Harrison-side handoff
assessment, the newly executed IC₅₀/Qwen pilot, the value-of-planning experiment,
and the evaluation-data investigation. Section 9 adds the subsequently authorized
and executed final extension on adaptive concentration selection. This document
summarizes those runs; editing it introduces no additional experimental run.

## 1. Overall conclusion

The strongest current contribution is an auditable retrospective assay-selection
benchmark, together with evidence that endpoint adjudication and decision
interfaces can materially affect its conclusions. A reliably superior PPO or Qwen
selector has **not** been established. Direct greedy remains the reference method;
Bayesian lookahead deserves continued comparison.

The new work supports three narrower conclusions:

1. **Recognizing threshold-qualified potency bounds changes discovery credit.**
   In the new F7 pilot, this increased mean new-hit counts for Qwen, random and
   greedy equally, without improving Qwen's acquisition yield under a common
   evaluator. The original MSH3 handoff reports a larger analogous rescoring effect.
2. **Planning headroom depends on the information and budget model.** Greedy was
   optimal in 108 of 162 explicitly modeled settings; one-step Bayesian rollout
   reached the optimum in 150. Fresh PPO did not beat greedy in this pilot.
3. **More evaluation is possible, but independence and compatibility remain the
   bottlenecks.** Existing reserved risk records and retrospective efficacy-transfer
   strata are useful. External candidates require further metadata and exposure
   qualification before they can support independent validation claims.

These findings do not establish clinical efficacy, clinical safety, validated
generated molecules, or statistically superior learned experimental selection.

**Final extension:** adaptive per-ASO dose selection was subsequently evaluated on
240 assessment panels after development on 93 separate panels. Decision-aware
selection used 1.683 measurements per ASO versus 1.592 for a strong fixed early-stop
baseline, with three binary classification errors versus zero. All early-stop
methods classified the sole reference-unresolved panel, failing the prespecified
unresolved-assertion check. This did not establish the proposed incremental
efficiency benefit. See Section 9 for the target-specific exception and full scope.

## 2. Evidence provenance and separation of systems

| Evidence | Status | Scope |
|---|---|---|
| Harrison experimental-selection V3/Qwen3 results | Reported in the user-supplied November 14 handoff; original later code and artifacts unavailable here | Historical linked screen/curve purchases, original 500 nM criterion |
| New IC₅₀/Qwen pilot | Executed locally, with sealed protocol, decisions and completion audit | Direct recorded-panel purchases, Qwen2.5-3B, 100 nM primary criterion |
| Value-of-planning study | Executed locally, exact model expectations and three fresh PPO fits | Four-candidate probabilistic model; no measured biological outcomes |
| Evaluation-data expansion | Completed metadata and provenance audit | No new fitting, prediction, calibration or final-label evaluation |

**Molecular design and experimental selection are different systems.** The current
molecular-design code constructs ASOs and searches frozen inhibition/risk
predictions. Its candidate-MLP pretraining and eight-target utility comparisons
belong to that system. Its efficacy and risk Ridge heads used 2,284 and 873 fitting
records, respectively.

The Harrison-side experimental selector purchases assays for existing compounds.
Its original V3 priors were source-only inhibition and log₁₀-IC₅₀ Ridge models
trained on EZH2/SPDEF, with Bayesian residual updates after paid observations.
They are not the molecular-design heads, the earlier OligoGym advisory models,
or the teammate's RNA-FM model. Qwen inference does not update Qwen's weights.

The handoff places the later V3/Qwen work on local branch
`codex/experimental-selection-llm-agent`, commit `30ac0e9`, in Harrison's
experimental-selection worktree. Neither that worktree nor the later commit
objects were available here. Fetching all 11 remote branches left the published
experimental-selection branch at `1b92731`. The original experiments therefore
were not independently reproduced in this checkout; they were not nonexistent.

## 3. Assessment of the original experimental-selection side process

### Original benchmark contract

- A single-dose screen costs **$500**. Measured inhibition **strictly above 80%**
  unlocks the linked potency curve, costing **$2,000** at nominal prices.
- The campaign budget is **$15,000**, with $1,000/$4,000 curve-cost sensitivities.
  These are modeled costs, not newly incurred laboratory expenses.
- Original success requires a paid, usable, in-range absolute **IC₅₀ ≤500 nM**.
  Reported QC includes at least four finite distinct positive doses, sufficient
  observed response span, and fit R² >0.5. Exact remaining settings require the
  original implementation.
- Full direct PPO and greedy expose all eligible compound–assay pairs. The Qwen
  interface instead offers up to six ranker-proposed purchases.
- Recorded linked curves reflect historical advancement. This panel is not an
  unbiased sample of every compound in an initial screen.

The eight reported evaluation pools contain MSH3 101, FUS 54, ATXN1 72, KCNT1 325,
SCN2A 79, YAP1 98, IFNAR1 160 and SNCA 35 compounds.

| Policy | Reported eight-cohort mean confirmed hits, original rule |
|---|---:|
| Direct greedy | 3.000 |
| Bayesian lookahead | 3.125 |
| Random | 2.234375 |
| Qwen3-4B | 2.500 |

These results do not establish learned-selector superiority. The handoff also
describes expert-action, full-action and residual PPO studies, supervised
initialization controls, and conditional confirmation models without a reliable
advantage over greedy. Repeated availability draws from one NLRP3 panel are not
independent biological replications.

### Endpoint adjudication: the strongest immediate lead

On MSH3, Qwen3-4B reportedly bought ten screens and five curves. Two curves had
usable exact estimates near 136.85 and 261.43 nM. The other three were already
above 50% inhibition at the lowest tested dose, 62.5 nM, and increased across the
observed grid. Under a monotonic-response assumption, these can support upper
bounds rather than in-range point estimates.

The handoff's **post-hoc rescoring of unchanged purchases** gives:

| Policy | Original point-estimate hits | Exact plus qualified upper-bound hits |
|---|---:|---:|
| Qwen3-4B | 2 | 5 |
| Direct greedy | 3 | 5 |
| Random, mean over 32 seeds | 2.1875 | 3.03125 |

This removes the observed Qwen–greedy deficit on MSH3. It does not establish Qwen
superiority or show that revised feedback improves subsequent decisions. The
issue is a mismatch between requiring an in-range estimate and asking whether
potency meets a threshold; the original code may correctly implement its original
specification. Bound qualification still needs frozen QC, measurement uncertainty
and source-context rules.

### Qwen interface limitation

The original Qwen3-4B selected the first letter on **93/116 calls**. In the reported
permutation diagnostic, it retained its chosen letter and changed its assay in
**16/16 cases**. This is evidence about that model/interface combination, not all
language models. Future comparisons need stable or counterbalanced identifiers,
permutation controls, and deterministic/random baselines sharing the same menu.

**Assessment:** the side process is a substantial benchmark and negative-result
research pipeline. A finalized claim of a superior learned selector remains open.

## 4. Executed IC₅₀/Qwen experiment from scratch

### Frozen design and scientific interpretation

The new pilot was sealed and running before the Harrison handoff arrived. It
remains a separate retrospective experiment, not an original-V3 reproduction.

| Item | Executed pilot |
|---|---|
| Model | Frozen local Qwen2.5-3B-Instruct, MLX four-bit quantization |
| Primary endpoint | Operational apparent absolute IC₅₀ ≤100 nM |
| Sensitivities | 10 and 1,000 nM, rescoring fixed trajectories |
| Purchase | One complete recorded dose-response panel; no preliminary screen gate |
| Budget | Eight panels, including two common starting panels |
| Primary outcome | New discoveries among the remaining six purchases |
| Comparators | Uniform random; GC-bin Beta-Bernoulli greedy; matched group Thompson sampling |
| Replication | Three common-start seeds, four policies, two feedback rules, three targets |
| Execution | 72 completed arms; 108 actual Qwen choices; no fallback decisions or inference failures |

Metadata-only selection chose a common complete dose grid within each campaign,
with a fixed hash cap of 24 panels. No panel was selected by observed response.

| Target | Recorded assay context | Doses, nM | Panels |
|---|---|---|---:|
| F7 | Human Hep3B, electroporation, 16 h | 50, 150, 440, 1,330, 4,000 | 24 |
| STAT3 | Human HUVEC, electroporation, 16 h | 39.1, 156.3, 625, 2,500 | 24 |
| NLRP3 | Human THP-1, electroporation, 24 h | 16, 63, 250, 1,000, 4,000 | 15 |

The experiment reused **63 historical panels / 291 source observations**. Across
repeated arms it charged **576 panel purchases / 2,688 dose readouts**. These are
replay accounting totals, not new biological measurements. Qwen generation took
369.6 seconds in total, with no API bill.

Each curve needs at least four distinct positive finite doses. Increasing isotonic
regression permits at most 15 percentage points of adjustment; nonfinite responses
or values outside [−20, 120] remain unresolved. An in-range 50% crossing is
interpolated in log concentration. A lowest-dose fitted response ≥50% gives an
upper bound; a highest-dose response <50% gives a strict lower bound. No
extrapolated point estimate is invented. A zero-adjustment sensitivity tests strict
monotonicity. These are operational rules, not validated assay-error estimates.

The constructed **exact-only** rule denies hit credit to qualified upper bounds;
**bound-aware** credits bounds at or below the cutoff. Unknowns remain unknown.
Raw controls, viability, replicate uncertainty and extraction accuracy were not
established, so this is apparent potency adjudication rather than biological
validation. The GC-bin baselines are not original V3 Ridge greedy or a continuous
censored-GP optimizer.

Qwen receives molecular descriptors and purchased feedback, never unpurchased
outcomes. Constrained next-token argmax selects a legal candidate letter. Seeded
letter permutations are shared across feedback arms; no repair or heuristic
substitution is used.

### Primary results

Entries are mean **new-hit counts among six purchases**, across three seeds.

| Target | Policy | Exact-only | Bound-aware |
|---|---|---:|---:|
| F7 | Random | 1.667 | 2.000 |
| F7 | GC-group greedy | 1.667 | 2.000 |
| F7 | GC-group Thompson | 0.333 | 0.333 |
| F7 | Qwen2.5-3B | 1.667 | 2.000 |
| STAT3 | All four policies | 0.000 | 0.000 |
| NLRP3 | All four policies | 0.000 | 0.000 |

F7 has six qualifying in-range estimates and two additional upper bounds at
50 nM: eligible pool size changes from **6/24 to 8/24**. STAT3 and NLRP3 have no
qualifying panels at 100 nM, so their zero yields do not distinguish policies.

Rescoring each F7 exact-only trace with the bound-aware evaluator adds **0.333
hits** for every method. Comparing both adaptive arms using that same evaluator
gives acquisition gains of **0 for Qwen, random and greedy**, and **−0.333 for
Thompson**. Increased Qwen credit is therefore not improved acquisition yield.

All nine paired Qwen trajectories change order or membership, including targets
with no changed censoring labels. Because the active rule name also changes the
prompt, these action changes cannot be attributed exclusively to feedback.

### Sensitivities and interface diagnostic

At 10 nM, no selected panel qualifies. At 1,000 nM, nearly all pool panels qualify:
F7 23/24, STAT3 24/24 and NLRP3 13/15. Fixed bound-aware trajectories give:

| Target | Random | Greedy | Thompson | Qwen |
|---|---:|---:|---:|---:|
| F7 | 5.667 | 5.667 | 5.333 | 5.333 |
| STAT3 | 6.000 | 6.000 | 6.000 | 6.000 |
| NLRP3 | 5.000 | 4.667 | 5.000 | 5.333 |

Strict monotonicity leaves primary 100 nM hit counts unchanged. At 1,000 nM it
reduces NLRP3 means to **4.000 random, 3.667 greedy, 3.667 Thompson and 3.000
Qwen**, reversing Qwen's small apparent advantage. This is not robust superiority.

A post-hoc log diagnostic found first-available-letter selection **0/108 times**;
the mean probability under uniform choice was 6.71%. This differs from the
historical Qwen3 interface but does not demonstrate freedom from presentation
bias. No matched permutation test ran, and adaptive choices are not independent
binomial trials.

### Exposure limitation

These are reused development targets, not fresh independent campaigns. Reserved
risk-final outcomes were not accessed. However, the late handoff disclosed a
historical NLRP3 train/development/test split whose exact membership is unavailable.
Overlap is therefore unverified. A sealed scope amendment preserves that limitation;
the pilot's protocol was not changed after seeing outcomes. Its outputs must not
be reused to fit or tune future policies. No significance claim is supported.

## 5. Executed value-of-planning experiment

### Model and algorithms

Four candidates form two independent pairs. Hidden binary hit labels have an
explicit joint prior over 16 worlds. A noisy screen costs one unit, has sensitivity
and specificity 0.9, and gives no discovery reward. A perfect confirmation costs
two, three or four units and reveals the label, awarding one for a hit. Confirmation
can be purchased **without screening**. Assays cannot repeat; budget is enforced.

The state includes paid outcomes and remaining budget. All methods receive the
same exact posterior information. Candidate marginals are
`q_i = (1-u) z_i + u p`, with anchors z chosen to preserve mean prevalence p.
Within-pair dependence mixes independent draws with shared-uniform draws at weight
r; r is not a Pearson correlation coefficient.

| Factor | Frozen levels |
|---|---|
| Uncertainty strength u | 0.1, 0.5, 1.0 |
| Confirmation/screen cost ratio | 2, 3, 4 |
| Budget | 4, 6, 8 |
| Mean hit prevalence p | 0.25, 0.5, 0.75 |
| Pair dependence mixture r | 0, 0.75 |

This yields **162 settings**. Increasing u also changes prior heterogeneity;
these axes are declared model parameters, not calibrated biological measurements.

Exact dynamic programming solves
`V*(s) = max(0, max_a Σ_o P(o|s,a)[reward(s,a,o) + V*(s')])`.
Its expectations integrate over every possible observation branch. It is
Bayes-optimal under the specified model, **not clairvoyant**. A separately reported
clairvoyant ceiling knows every hidden label and is not an executable policy.

Greedy confirms the candidate with highest updated posterior hit probability.
Bayesian rollout evaluates each next assay followed by greedy completion, then
replans after the actual purchase. Random samples legal affordable assays. Fresh
MaskablePPO receives the full posterior and observed history.

### Results and planning map

| Method | Equal-setting mean expected confirmed discoveries |
|---|---:|
| Exact Bayes-optimal DP | 1.298591 |
| Bayesian rollout | 1.296469 |
| Greedy with Bayesian updates | 1.260482 |
| PPO deterministic, each of three seeds | 1.241975 |
| Random assays | 0.691171 |

These averages describe the chosen grid, not a real-campaign distribution.

- Greedy is optimal in **108/162** settings; 54 have positive planning headroom.
- Bayesian rollout is optimal in **150/162** settings.
- Maximum optimal-minus-greedy gain is **0.400 expected hits**: greedy 1.000,
  rollout/optimum 1.400, clairvoyant ceiling 1.625.
- Mean headroom is **0.038110** above greedy and **0.002123** above rollout.
- Rollout's largest remaining optimality gap is **0.0785**.

The prespecified primary slice is budget 6, prevalence 0.5, pair mixture 0.75.
Cells show **optimal minus greedy expected hits**:

| Uncertainty strength | Cost ratio 2 | Cost ratio 3 | Cost ratio 4 |
|---|---:|---:|---:|
| 0.1 | 0.000 | 0.000 | 0.038 |
| 0.5 | 0.000 | 0.000 | 0.150 |
| 1.0 | 0.000 | 0.000 | 0.225 |

Planning value is not monotonic in assay cost. With six units and confirmation
cost four, two remaining units buy information without sacrificing a confirmation.
Integer budget allocation matters alongside uncertainty and prevalence.

### PPO execution and limitations

Three seeds each trained for 32,768 decisions: **98,304 total**, approximately
20.1 seconds of fitting. The policy used a two-layer 64-unit MLP, rollout 256,
minibatch 64, two epochs, learning rate 0.0003, entropy coefficient 0.01, and
gamma/GAE lambda 1. No pretraining, hyperparameter selection or performance-based
stopping ran. Training and evaluation use the same declared task grid; this is
not held-out-grid generalization.

Each deterministic PPO policy ties greedy in 126 settings, loses in 36 and wins
in zero. Distinct checkpoint hashes yielded identical expected discovery values;
this does not establish identical probability distributions or algorithmic certainty.
One inspected branch shows PPO failing to exploit a partner's increased posterior
after a positive confirmation. That is an illustrative failure, not a causal
diagnosis of all prior PPO results. A separately profiled stochastic-deployment
supplement exceeded its fixed runtime gate and was not executed.

The model is **not original V3**: no mandatory >80% screen gate, no measured IC₅₀
curves, and no calibrated source Ridge priors. Original V3 normalized by its
$500 screen cost has budget 30, outside this grid's 4/6/8. The result demonstrates
mechanisms and attainable headroom under assumptions; it does not prove why real
V3 PPO failed. Nonmyopic active search is established prior work, including
[Nguyen, Modiri and Garnett, ICML 2021](https://proceedings.mlr.press/v139/nguyen21f.html).

## 6. Evaluation-data expansion

### Audit boundary

The audit reads allowlisted sequence, chemistry, patent, target and assay metadata,
plus existing provenance manifests. It does not open raw endpoint columns, run
predictors, fit models, calibrate thresholds or assign new final sets. Public
article summaries and aggregate findings were visible during literature research;
this is not complete literature-outcome blinding.

Own-head fitting/selection/calibration exclusion is distinguished from project-wide
freshness. Independence sensitivities use source IDs, exact sequence/patent-ID
components, and expanded near-sequence components. These are conservative metadata
checks, not a complete patent-family or biological homology resolver.

### Existing risk evaluation

The risk head has 873 fitting, 259 development and 283 calibration observations.
Its **304 original final records remain sealed**. The matching context contains
1,720 metadata records representing 1,720 parsed compounds, including one original
fitting allocation without a usable observation.

| Assessment definition | Original final records retained |
|---|---:|
| Original reserved allocation | 304 |
| Full-release exact-sequence/patent-ID exclusion | 303 |
| Full-release near-sequence/patent-ID exclusion | 226 |

The strict set has three components, targeting ATXN3, FUS and LRRK2. The difference
of 78 records is an independence concern, not an observed error rate. Preserve all
original roles and preregister the stricter sensitivity before unsealing. Three
components do not provide 226 independent biological replications.

### Efficacy transfer opportunities

No parsed release row matches both the current grammar and the active human
HepG2/electroporation/**4,500 nM**/24 h context. Other contexts support explicitly
separate retrospective transfer diagnostics:

| Target | Context | Rows | Components |
|---|---|---:|---:|
| KCNQ2 | Human SH-SY5Y, electroporation, 4,000 nM, 24 h | 1,008 | 1 |
| PTBP1 | Human A431, gymnosis, 3,000 nM, 48 h | 463 | 1 |
| GYS1 | Mouse B16-F10, electroporation, 7,000 nM, 24 h | 67 | 1 |
| MECP2 | Human HepG2, electroporation, 4,000 nM, 24 h | 9 | 1 |
| GYS1 | Human A431, gymnosis, 4,000 nM, 48 h | 3 | 1 |

These survive the current efficacy head's near-sequence/patent exclusion but are
not globally untouched. The late handoff reports KCNQ2 in conditional-model
training elsewhere. Missing recovered memberships are not proof of non-exposure.
The earlier 298-row MECP2 fitting-data lead used different eligibility criteria
and is not interchangeable with this nine-row evaluation stratum.

Another 191 rat risk records use a different route, dose and body-parts scale;
two mouse records use 500 rather than 700 micrograms. Neither belongs in pooled
calibration for the current mouse behavioral endpoint.

### External candidates

| Source | Opportunity | Qualification still needed |
|---|---|---|
| OligoAI KCNT2 | 50 experimental ASOs: 32 random-library and 18 model-selected; MOE, HeLa/RNAiMAX, 30 nM, 48 h, with follow-up curves | Per-record chemistry, raw tables, overlap and rights; preserve selection strata |
| ClinASO | PCSK9, IRS1, ACSL4 and SRPK1 panels | Compound deduplication, context/chemistry compatibility, candidate-selection provenance and supplement review |
| Acute-CNS study | 34-ASO mouse ICV 700-microgram/3-hour panel | Potential overlap with existing Atlas/risk provenance; not certified additional data |
| Small-data wet-lab study | Eight staged records: six DAZAP1, two FAM69C | Missing full chemistry and treatment concentration; QC-selected panel, not unbiased validation |

For the staged eight-record panel, metadata checks found no own-head exact/near
sequence or patent-component connection to fitting/selection/calibration records,
and no target overlap. The sequences form five local components across two targets
in one study. Missing chemistry and patent annotations prevent full certification.
Original bytes were preserved; endpoint columns were not projected.

Source links: [OligoAI paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13427547/),
[OligoAI release](https://github.com/barneyhill/OligoAI),
[ClinASO paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13156736/),
[acute-CNS study](https://doi.org/10.1093/nar/gkaf1333), and
[pinned small-data repository](https://github.com/rguha-cs/small-data-aso-ml-pipeline/tree/5b5f3462a0193cad93d9a898ac8fa0abcaaed250).
External **KCNT2 is distinct from original V3 KCNT1**. Publication or repository
licenses do not automatically establish redistribution rights for every source
measurement.

The handoff additionally reports potential linked risk panels FUS 25/APP 71 and
hepatic panels EZH2 41/SPDEF 19/NLRP3 39/IRF4 18. These are unverified linkage leads,
not newly admitted independent evaluation labels.

## 7. Scientific claims and next decisive experiments

**Supported now:** a reproducible local recorded-panel pilot; real changes in hit
credit from qualified upper bounds; exact planning headroom under an explicit
model; negative PPO/Qwen findings within the tested scope; and concrete metadata
paths toward better evaluation.

**Not supported now:** general PPO or Qwen superiority, censoring-induced policy
ranking reversal in the new pilot, original-V3 reproduction, independent biological
generalization, or validated safety/efficacy of generated ASOs. More replay seeds
cannot substitute for more independent campaigns.

Recommended sequence:

1. Recover original V3 code, source/curve reviews, frozen predictors, ledgers and
   split/access manifests from Harrison's checkout.
2. Freeze a bound-aware **500 nM** adjudication rule that preserves exact estimates,
   threshold-qualified bounds, unresolved curves and threshold failures separately.
   Specify QC and uncertainty handling before another benchmark.
3. First rescore fixed original traces. Then run adaptive replays under the same
   screen gate, costs, candidate pools and information access. Separate count
   changes from decision-quality changes; treat PPO retraining as another arm.
4. Counterbalance Qwen identifiers, run permutation checks, and include both
   shared-menu and full-pool controls. Preserve greedy and Bayesian lookahead.
5. Match a planning model to the real screen gate, costs and permitted-development
   evidence before interpreting an optimal-policy gap as V3 headroom.
6. Freeze the original 304-record risk evaluation and 226-record sensitivity,
   evaluate transfer contexts separately, and qualify external campaign metadata
   before opening outcomes. Keep those campaigns out of policy development.

## 8. Verification, artifacts and source reports

The integrated repository suite passed **318 tests**, with lint, formatting,
import and whitespace checks passing. Scientific tests include 17 IC₅₀ pilot,
12 planning and seven evaluation-audit invariant cases. The Qwen completion audit
checks all 72 unique arms, common starts, eight distinct charged panels per arm,
identical random trajectories across rules, and 108 sealed legal request/response
pairs. Protocol, result, audit and late-scope-amendment seals were verified.

Planning checks include posterior normalization, cost conservation, nonrepeat
assays, permutation invariance, uninformative-screen controls, policy-value ordering
and all 486 deterministic PPO evaluation cells respecting the optimal bound.
Standalone planning maps were rendered and inspected.

| Evidence | Local location |
|---|---|
| IC₅₀ protocol, decisions, report, scope amendment and audit | `artifacts/ic50-qwen-from-scratch-v1/` |
| Qwen model identity, license and runtime receipts | `artifacts/ic50-qwen-runtime-v1/` |
| Exact grid, PPO runs, maps and execution receipts | `artifacts/value-of-planning-v1/` |
| Outcome-free candidate manifests and external provenance | `artifacts/molecular-evaluation-data-expansion-v1/` |

These directories are ignored local artifacts, not files supplied by a Git clone.
Datasets, model weights and generated run artifacts were not committed by this work.
The original Harrison-side artifacts remain unavailable here. Reproduction should
use fresh output directories and the commands in the individual reports.

Detailed source reports consolidated here:

- [Experimental-selection handoff assessment](experimental-selection-handoff-assessment.md)
- [Executed IC₅₀/Qwen pilot](ic50-qwen-from-scratch.md)
- [Executed value-of-planning experiment](value-of-planning-experiment.md)
- [Evaluation-data expansion audit](molecular-evaluation-data-expansion.md)

The original reports and sealed run evidence retain authority for exact protocol
details. This consolidated document preserves their distinctions and limitations;
it does not merge incompatible endpoints or retroactively change any experiment.

## 9. Final extension: adaptive dose-response measurement

### Question, cohort and frozen methods

Can choosing individual concentrations sequentially resolve absolute apparent
IC₅₀ ≤500 nM with fewer measurements than a strong fixed early-stopping rule,
while preserving classification reliability? This extends the purchase unit from
a complete assay panel to one recorded concentration-response measurement.

The experiment used **333 ASO panels and 1,473 distinct recorded dose observations**:
93 development panels (F7 45, STAT3 48) and 240 assessment panels (48 each for
DNM2, PCSK9, KRAS, TMPRSS6 and AGT). Seven distinct patent IDs were represented.
Development and assessment were disjoint by target, patent ID and source rows,
with exact/near sequence exclusions between them. All original reserved risk
records, the seven previously reserved target groups and NLRP3 were excluded
through the declared metadata guards. This is experiment-held-out retrospective
assessment, not certified project-wide freshness or new biological validation.

Selection used only metadata: human, assay-consistent panels with 4–10 distinct
positive concentrations, the largest complete common grid per target, and a fixed
48-panel hash cap. Reference QC was not used to select panels. The reference
preserved in-range log-dose interpolated estimates, qualified upper/lower bounds
and unresolved curves using the previously declared PAVA rule (maximum adjustment
15 percentage points); strict monotonicity was a prespecified sensitivity.

Policies receive only purchased inhibition values. No unrecorded concentration
can be purchased, repeated doses are forbidden, and at least one measurement is
required before stopping. Full-grid reference labels and unpurchased responses
never enter policy selection. Complete causal orderings are cached for replay;
each operating point uses and charges only its stopping prefix. This is offline
accounting, not new physical assays.

The four methods were:

- **Full grid:** buy every available concentration, then adjudicate.
- **Fixed early stopping:** buy doses in increasing log-distance from 500 nM;
  stop on a monotonic threshold witness or interpolation using the purchased
  nearest bracketing doses. Development selects a response margin from 0/5/10/15
  percentage points or full-grid-only stopping.
- **Bayesian information gain:** select the dose maximizing expected information
  about a finite dose-response parameter model.
- **Decision-aware Bayesian selection:** select the dose minimizing expected
  posterior binary classification error about inhibition at 500 nM.

The Bayesian model uses 1,500 fixed, uniformly weighted combinations of bottom,
top, Hill slope and log-midpoint, including top responses below 50%. Gaussian
observation noise is fixed at 10 percentage points. Prospective responses use
binned Gaussian probability masses; actual updates use continuous observations.
These are declared model assumptions, not calibrated assay uncertainty. Confidence
thresholds 0.90/0.95/0.975/0.99/0.995/full-grid-only were selected on development.
All methods can fall back to the identical adjudicator once all doses are paid.
No PPO, neural training or outcome-driven model revision ran.

### Reliability criterion and selection

Development selection minimized mean measurements subject to empirical FPR and
FNR ≤5%, resolved-reference coverage ≥95%, and definitive assertions on
reference-unresolved panels ≤5% when that denominator exists. Bayesian coverage
also had to remain within two percentage points of the fixed baseline. Missing
positive/negative classes could not silently pass an error constraint.

The selected settings were fixed margin **0**, information-gain confidence
**0.95**, and decision-aware confidence **0.90**. Their selection was sealed
before assessment outcomes were opened. Development contained no unresolved
references, so its unresolved-assertion behavior was unassessed, not validated.
These empirical criteria do not guarantee population error rates.

### Assessment results

Full-curve references were **108 potent, 131 not potent and one unresolved**.
Curve categories were 209 interpolated estimates, 15 upper bounds, 15 lower bounds
and one unresolved curve. False-positive rates use the 131 reference-negative
panels; false-negative rates use the 108 reference-positive panels.

| Method | Mean measurements/ASO | False positives | False negatives | FPR | FNR | Definitive assertions on unresolved references |
|---|---:|---:|---:|---:|---:|---:|
| Full grid | 4.400 | 0 | 0 | 0% | 0% | 0/1 |
| Fixed early stopping | 1.592 | 0 | 0 | 0% | 0% | 1/1 |
| Bayesian information gain | 2.817 | 0 | 0 | 0% | 0% | 1/1 |
| Decision-aware Bayesian | 1.683 | 1 | 2 | 0.763% | 1.852% | 1/1 |

All methods classified every reference-resolved panel. Full-grid inconclusive
rate was 1/240 (0.417%); the other methods stopped with definitive answers for
every panel. Full-grid agreement is by construction because its adjudicator
defines the reference; it is not independently validated biological accuracy.

Relative to fixed early stopping, decision-aware selection used **5.76% more**
measurements and information gain used **76.96% more**. All early-stop methods
failed the prespecified unresolved-assertion condition: their one assertion among
one unresolved panel gives 100% for that rate. This tiny denominator must not be
interpreted as a precise population estimate. The result is a concrete demonstration
that early classification can miss a full-curve operational QC flag. Specifically,
the DNM2 panel's lowest-dose response was −25%, outside the frozen [−20%, 120%]
range. Its increasing responses otherwise supported nonpotency. Missing this flag
does not establish an incorrect biological potency decision.

| Assessment target, 48 panels each | Full grid | Fixed early | Information gain | Decision-aware |
|---|---:|---:|---:|---:|
| AGT | 5.000 | 1.438 | 4.042 | 2.583 |
| DNM2 | 4.000 | 1.000 | 2.250 | 1.021 |
| KRAS | 4.000 | 1.458 | 3.396 | 1.771 |
| PCSK9 | 4.000 | 1.646 | 2.667 | 1.833 |
| TMPRSS6 | 5.000 | 2.417 | 1.729 | 1.208 |

DNM2 includes a measured 500 nM concentration, making the threshold-nearest
baseline particularly strong. The unresolved reference is in DNM2. Decision-aware
errors were two false negatives in AGT and one false positive in PCSK9.
TMPRSS6 is a descriptive exception: decision-aware selection halved measurements
versus fixed stopping, with no observed binary errors. Both methods started at
440 nM for every TMPRSS6 panel, so this reduction did not come from a better first
dose. It reflects their subsequent decision rules, including model-based stopping;
the experiment does not isolate an effect of adaptive dose ordering from stopping.
This one campaign does not establish a general gain. No post-hoc policy tuning or
additional experiment was launched to improve these results.

### Interpretation and evidence

The study did **not** establish the proposed primary contribution of measurement
reduction over strong fixed early stopping at the full prespecified reliability
criterion. Large savings relative to measuring every dose are insufficient for
that claim. It instead supplies a useful negative comparison, a target-specific
signal, and a distinction between resolving a threshold and verifying full-curve QC.

Historical reference curves share measurements with the replay and are fallible;
no independent replicate truth or validated noise model was available. Only five
assessment campaigns contribute, and within-campaign ASOs are correlated. No
statistical superiority or proportional wet-lab cost savings are claimed. Plate
layout, replication, setup and sequential turnaround remain outside the replay.

The integrated checks now pass **330 tests**, including 12 new invariants for paid
information isolation, poisoned-suffix invariance, dose costs, censoring, posterior
normalization, unresolved decisions and undefined error rates. Independent review
verified protocol/result/source hashes, selection-before-assessment provenance,
disjoint target/patent/source memberships and nonrepeating dose orderings.

Detailed report: [Adaptive dose-response experiment](adaptive-dose-response-experiment.md).
Code: `experiments/adaptive_dose_response/`. Local ignored evidence:
`artifacts/adaptive-dose-response-v1/`, including metadata configuration, frozen
protocol, development selection, both replay sets, results and figures. This
completes the requested final major extension; subsequent ideas are not executed
experiments.
