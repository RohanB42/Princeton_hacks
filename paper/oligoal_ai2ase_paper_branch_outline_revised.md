# OligoAL — Revised AI2ASE Paper Outline (Branch Structure)

**Format:** AAAI long-paper format; references excluded from the workshop's eight-page main-text limit.  
**Working title:** **OligoAL: Evaluating Adaptive Molecular Search and Experimental Decisions for Oligonucleotide Discovery**  
**Scope:** Two **parallel decision environments** developed in tandem, grounded in a shared molecular-prediction and data-evaluation foundation. The experimental-selection evidence is stronger because it replays recorded outcomes; molecular-design findings concern constrained **surrogate-guided search** and require separate biological validation.  
**Editorial principle:** Let the relative space assigned to sections follow the figures and evidence; **do not preassign page allocations**.

> **Core question:** When do learned or adaptive policies improve decisions in oligonucleotide discovery under limited resources, and when do strong conventional methods already capture most of the attainable value?
>
> **Central contribution:** A decision-centered research framework spanning (i) data-efficient prediction, (ii) chemistry-constrained molecular proposal, and (iii) measured-outcome experimental acquisition. We evaluate decision quality against appropriate baselines and make information access, evidence reliability, and scientific applicability explicit.
>
> **Boundaries:** Do not claim a newly invented RL algorithm, superior therapeutic molecules, verified laboratory savings, or a prospectively validated end-to-end design–test–learn system.

---

## A. Whole-paper research map

```text
OLIGOAL — LEARNING, DESIGNING, AND TESTING UNDER CONSTRAINTS
│
├── I. Scientific/data foundation
│   ├── OligoGym: endpoint-specific oligo benchmarks and historical measurements
│   ├── ASO Atlas 2.0: ASO chemistry, assay context, potency curves, provenance
│   ├── Scientific restrictions: chemistry, target, endpoint applicability
│   └── Common rules: source provenance, exposure boundaries, sealed outcomes
│
├── II. Predictive knowledge and efficient learning
│   ├── Classical supervised predictors (Ridge / RF / GP / CNN)
│   ├── Active learning: random / diversity / uncertainty / hybrid
│   │   └── Measured-label efficiency on Huesken
│   └── RNA-FM features and LoRA / ASO Atlas target adaptation
│       └── Does pretrained representation transfer outperform classical models?
│
├── III. Decision environment A — MOLECULAR DESIGN
│   ├── Question: what valid ASO should the system propose or score next?
│   ├── Transcript-anchored, chemistry-constrained construction grammar
│   ├── Frozen, applicability-aware endpoint scorer (surrogate feedback)
│   ├── Supervised surrogate-guided candidate-policy initialization
│   ├── Optional MaskablePPO refinement
│   └── Random / greedy / pretrained / PPO comparisons at matched query budgets
│
├── IV. Decision environment B — EXPERIMENTAL SELECTION
│   ├── Question: which recorded ASO–assay pair is worth purchasing next?
│   ├── Private measured-outcome oracle and assay eligibility
│   ├── V1: frozen-predictor efficacy acquisition
│   ├── V2: online Bayesian prediction updates
│   ├── V3: initial screen -> qualified potency follow-up
│   └── Random / greedy / Bayesian rollout / PPO / Qwen comparisons
│
├── V. Experimental-evidence interpretation and sufficiency
│   ├── Exact versus bounded versus unresolved IC50 evidence
│   ├── Original V3 scoring versus separately frozen censor-aware pilots
│   └── Sequential concentrations: full grid, fixed stopping, Bayesian,
│       decision-aware selection (assessment QC is an explicit result)
│
├── VI. Explaining the value and limits of planning
│   ├── Exact finite-horizon model over 162 synthetic settings
│   ├── Optimality gap vs greedy / one-step rollout / PPO
│   └── Hypothesis for when sophisticated search/planning is worthwhile
│
└── VII. Scientific interpretation and claims
    ├── Predictive metrics ≠ acquisition yield ≠ surrogate search quality
    ├── Actual historical measurements ≠ novel wet-lab validation
    ├── Model/policy complexity ≠ demonstrably improved decisions
    ├── Repeated seeds/draws ≠ independent biological campaigns
    └── Benchmarks and failure analyses as reusable scientific contributions
```

**Narrative relationship:** The two RL environments are **parallel evaluations of different decisions**, not two confirmed steps in one already-validated closed loop. The predictor and data infrastructure support both; measurement interpretation primarily informs experimental selection, while surrogate applicability primarily constrains molecular design.

---

## B. Abstract — proposed argument sequence

```text
Abstract
├── Problem: predicting ASO properties is not the same as making useful
│   molecular-design or experimental-allocation decisions
├── Framework: OligoAL supplies shared, provenance-aware molecular data
│   and two distinct budgeted decision environments
├── Evidence: OligoGym active learning; ASO Atlas assay-purchase replay;
│   chemically constrained ASO molecular search
├── Methods: classical predictors; RNA-FM/LoRA; greedy/Bayesian methods;
│   supervised policy initialization; PPO; LLM policies
├── Results:
│   ├── Modest Huesken uncertainty-acquisition benefit
│   ├── Strong classical controls in efficacy transfer
│   ├── Greedy/Bayesian assay selection competitive with learned policies
│   ├── Strong fixed stopping under retrospective potency assessment
│   └── Supervised molecular search often competitive with PPO refinement
└── Conclusion: assess evidence semantics, opportunity for planning,
    and genuine decision value rather than complexity alone
```

**Avoid overstating:** The observed policies did not establish broad experimental-label savings, PPO superiority, clinical safety, or measured efficacy of generated candidates.

---

## 1. Introduction — from molecular prediction to scientific decisions

```text
1. Introduction
├── 1.1 Scientific setting
│   ├── Oligo activity depends on sequence, target, chemistry and assay conditions
│   ├── Scientists cannot screen every molecule or purchase every follow-up assay
│   └── Models and optimizers increasingly guide those choices
├── 1.2 Distinguish three questions
│   ├── Prediction: what molecular outcome should we expect?
│   ├── Molecular design: which chemically valid design should we propose?
│   └── Experimental selection: which measurement should we acquire?
├── 1.3 Common risk
│   ├── Predictive accuracy does not guarantee useful selection
│   ├── High surrogate reward is not observed biological efficacy
│   └── An unqualified/censored outcome may distort policy evaluation
├── 1.4 Research questions
│   ├── RQ1: Do representations and active acquisition improve learning
│   │   at limited measured-label budgets?
│   ├── RQ2: When do learned policies improve surrogate-guided ASO search
│   │   beyond strong, inexpensive search strategies?
│   ├── RQ3: When do adaptive assay-selection policies improve measured
│   │   discovery over greedy and Bayesian planning?
│   └── RQ4: How do measurement definitions and stopping decisions
│       change what we infer about experimental efficiency?
└── 1.5 Contributions
    ├── Shared scientifically constrained tasks and evaluation contracts
    ├── Chemistry-aware, budgeted molecular-search environment
    ├── Historical measured-outcome sequential assay-selection environment
    └── Comparative empirical findings and failure analyses
```

**Claim discipline:** The core innovation is an auditable **scientific decision evaluation** in a specific domain, not the mathematical novelty of PPO, LoRA, Gaussian processes, or active learning.

---

## 2. Related Work — distinguish direct foundations from precedents

```text
2. Related work
├── 2.1 Oligonucleotide data and prediction
│   ├── OligoGym: datasets, published prediction baselines and split definitions
│   ├── ASO Atlas 2.0 / OligoAI: ASO assays, efficacy and chemical context
│   ├── ASOptimizer and other chemistry-aware ASO prediction approaches
│   └── RNA-FM / OligoFormer / LoRA as representation/adaptation precedents
├── 2.2 Molecular optimization
│   ├── OligoRL: established constrained oligo RL framing
│   ├── PPO, valid-action masking and supervised policy initialization
│   └── Surrogate optimization, reward exploitation and query accounting
├── 2.3 Sequential experimental decisions
│   ├── Classical active learning and GP information gain
│   ├── Efficient Nonmyopic Active Search
│   ├── Nonmyopic Multifidelity Active Search
│   └── Cost-aware assay screening and Bayesian lookahead
└── 2.4 Measurement and scientific validity
    ├── Exact/censored IC50 reporting, assay QC and missing outcomes
    ├── Optimal concentration design and early stopping
    ├── LLM option-order sensitivity
    └── Historical selection and patent/compound exposure bias
```

**Positioning:** Prior papers establish the algorithms and datasets. Our contribution is the particular decision tasks, controlled information access, qualified biological rewards, comparisons and concrete empirical findings. Avoid unsupported “first ever” claims.

---

## 3. Data, shared infrastructure, and information boundaries

```text
3. Datasets and framework
├── 3.1 Data sources
│   ├── OligoGym: 12 released datasets, endpoint-specific modalities
│   │   └── Huesken: 2,431 siRNA measurements / 30 targets
│   ├── ASO Atlas 2.0: ASO inhibition, dose-response and risk records
│   └── Versioned transcript sequences for target-complement designs
├── 3.2 Molecular and assay features
│   ├── Natural base sequence; HELM and sugar/backbone modification tracks
│   ├── Target, cell, treatment, concentration, species and readout metadata
│   ├── Compound, source-row and patent provenance
│   └── Model-applicability flags (separate siRNA, ASO, MOE and OMe tasks)
├── 3.3 Shared evaluation contracts
│   ├── Stable observation and chemical identities
│   ├── Grouped train/selection/calibration/final roles
│   ├── Hidden measured-label oracle for acquisition tasks
│   ├── Frozen scoring registry for molecular-design tasks
│   ├── Initial labels and all query/assay expenditures are accounted for
│   └── Versioned ledgers, policies and result artifacts
└── 3.4 Two noninterchangeable evidence systems
    ├── Experimental selection: recorded historical assay outcomes
    └── Molecular search: frozen predictor / surrogate score estimates
```

**Figure 1 (main): Dual OligoAL environments.** Two branches from shared data/predictive models: **construct → score → archive** for molecular design, and **choose assay → purchase/reveal → update belief** for experimental selection. Label which arrows carry *surrogate* scores and which carry *measured* feedback.

**Essential limitation:** Assay costs are modeled rather than documented invoices; historically tested ASOs may be selected; not every compound has every assay. A simulated reward is not a biological observation.

---

## 4. Predictive models, representation transfer, and active learning

```text
4. Prediction and acquisition foundations
├── 4.1 Endpoint-specific classical prediction
│   ├── Ridge, RF, GP and CNN representations
│   ├── Efficacy, neurotoxicity and immunomodulation modeled separately
│   ├── Published benchmark reproduction and provenance checks
│   └── Expanded reproduction: 4/7 within prespecified ±0.03 Pearson tolerance
├── 4.2 Original Huesken active learning
│   ├── Random acquisition
│   ├── Sequence diversity
│   ├── GP-based uncertainty
│   ├── Hybrid uncertainty/diversity (distinct implementations)
│   └── Test-set learning curves at matched measured-label budgets
├── 4.3 Completed Huesken result
│   ├── Forty-seed GP study under official nucleobase holdouts
│   ├── Uncertainty minus random normalized Pearson AULC = +0.0095
│   ├── Bootstrap 95% interval [+0.0043, +0.0146]
│   ├── Hybrid: modest average improvement under the same protocol
│   └── No statistically reliable threshold-based label saving established
└── 4.4 RNA foundation-model / LoRA comparisons — main-text compact study
    ├── Frozen RNA-FM, neural heads and rank-4 query/value LoRA adaptation
    ├── Huesken: LoRA improves its matched frozen neural-head control,
    │   but underperforms one-hot Ridge
    ├── Atlas ASO source-to-target chemistry-aware adaptation:
    │   ├── 3%: Ridge+offset RMSE 19.883, LoRA 22.391
    │   └── 5%: Ridge+offset RMSE 19.656, LoRA 22.340
    └── Interpretation: sophisticated representations are not guaranteed
        to improve a limited-label ASO endpoint
```

**Figure 2 (main):** Huesken acquisition performance versus labels revealed. Include confidence information; optionally add a small inline table for the Atlas RNA-FM vs classical comparison rather than a standalone figure.

**Limits:** The Huesken study concerns siRNA and cannot be described as an ASO replication; 40 split seeds are not 40 independent biological studies. Atlas source allocations did not hold every inner-validation group fixed, so do not claim a clean sample-size scaling curve.

---

## 5. Decision environment A — Chemistry-constrained molecular design

**Make this a genuine main-paper experiment, not a short demo footnote.** It was developed alongside experimental selection and independently evaluates the decision **which valid molecule to construct and score next?**

```text
5. Surrogate-guided molecular search
├── 5.1 Scientific objective and task setup
│   ├── Target: transcript and allowed binding intervals
│   ├── Explicit valid ASO grammar for supported sequences/chemistry
│   ├── Initial molecule/archive and bounded construction/scoring budget
│   └── Optimize best eligible archive utility; no new wet-lab feedback
├── 5.2 Molecular construction and constraint engine
│   ├── NEW -> LENGTH -> SITE -> LAYOUT -> PATTERN -> TERMINAL -> COMMIT
│   ├── Exact-complement design and supported sugar/linkage patterns
│   ├── Invalid-action masks and prevention of meaningless repeats
│   ├── Only complete, valid ASOs trigger frozen predictor requests
│   └── Distinguish grammar steps from charged scoring calls
├── 5.3 Chemistry- and endpoint-aware reward system
│   ├── Frozen efficacy utility derived from a fixed training-reference scale
│   ├── Required versus advisory endpoint roles
│   ├── Chemistry, assay and model-domain applicability checks
│   ├── Unknown or unsupported safety readouts remain unknown
│   ├── Best-eligible-archive objective Q(A)
│   └── Incremental reward r_t = Q(A_(t+1)) - Q(A_t)
├── 5.4 Surrogate-guided policy pretraining
│   ├── Build valid candidate examples in permitted training campaigns
│   ├── Score with frozen endpoint models (pseudo-targets, not wet-lab labels)
│   ├── Train a positional sequence/chemistry MLP to predict eligibility
│   │   and utility from frozen model outputs
│   └── Distinguish direct ranking and staged pretrained policy controls
├── 5.5 Optional MaskablePPO search refinement
│   ├── Context/history encoder and valid-action policy
│   ├── Initialize from supervised candidate scorer
│   ├── Fine-tune with archive-improvement reward
│   ├── Compare pretraining-only, direct ranking, random, greedy and PPO
│   └── Account for total offline and deployment predictor queries
├── 5.6 Completed molecular-design findings
│   ├── Tested eight training/development targets, with heterogeneous exposure
│   ├── Pretraining-only matched/exceeded PPO on six of eight reported targets
│   ├── PPO minus pretrained staged policy on four original development targets:
│   │   ├── ~-0.0063 surrogate utility at eight charged requests
│   │   └── ~+0.0063 at 32 charged requests
│   ├── Full fitting/selection used ~27,028 offline predictor requests
│   │   versus ~2,880 for pretraining alone in the reported comparison
│   └── Additional PPO value is small/mixed under tested conditions
└── 5.7 Scientific limitations
    ├── Surrogate reward improvement != measured ASO efficacy
    ├── Development targets are not eight independent held-out targets
    ├── Current joint profile has zero certified independent final groups
    ├── Expanded chemistry context is incompletely supported by measured data
    └── Supervised-pretraining gain vs same architecture without pretraining
        remains to be isolated cleanly
```

**Equation for the result section:**

\[
Q(A)=\max\bigl(\{u(x):x\in A,\ \mathrm{eligible}(x)\}\cup\{0\}\bigr),\qquad
r_t=Q(A_{t+1})-Q(A_t).
\]

**Figure 3 (main if space permits):** Valid ASO grammar + best eligible *surrogate* utility versus **total predictor-query expenditure**, comparing random, greedy, supervised staged search and pretraining+PPO. If a figure is too large, include a concise task schematic plus results table.

**Interpretation:** Scientifically relevant contribution is **chemistry-aware, auditable, budgeted surrogate-guided learned search** and a rigorous assessment of what supervised initialization versus additional RL contributes—not a claim of biologically validated ASO improvement.

---

## 6. Decision environment B — Sequential experimental selection

**Give this a full main-paper environment section in parallel with Section 5.** It evaluates the distinct decision **which compound–assay outcome is worth measuring next?** and uses recorded historical results rather than fabricated molecular feedback.

```text
6. Experimental selection and sequential assay allocation
├── 6.1 V1 — single-dose efficacy acquisition
│   ├── Candidate pool is fixed and supported by historical records
│   ├── Predictive source model initially frozen
│   ├── Policy chooses which unrevealed efficacy label to purchase
│   └── Initial purchases and budgets explicitly counted
├── 6.2 V2 — online probabilistic belief updating
│   ├── Fit/update Bayesian residual model on acquired evidence
│   ├── Keep latent/model uncertainty distinct from observation noise
│   ├── Compare fixed predictor, updateable predictor and GP acquisition
│   └── Report sentinel RMSE improvement 29.42 -> 25.80 in its own protocol
├── 6.3 V3 — linked assay-purchase environment
│   ├── Actions: purchase a single-dose screen, eligible potency curve, STOP
│   ├── Screen eligibility: measured inhibition strictly >80% for follow-up
│   ├── Original endpoint: usable in-range IC50 <=500 nM
│   ├── Nominal modeled costs: $500 screen / $2,000 follow-up
│   ├── Campaign budget: $15,000, with documented cost sensitivities
│   ├── Linked compound chemistry and compatible assay context required
│   └── Missing/unobserved assay outcomes stay unavailable
├── 6.4 Policies and comparability
│   ├── Uniform random
│   ├── Direct greedy screening/potency prioritization
│   ├── Approximate Bayesian lookahead with belief updates
│   ├── PPO: expert-action, direct-action and residual-policy studies
│   ├── Qwen: restricted menu interface; not identical full-action reach
│   └── Track differences in source models, actions and study populations
├── 6.5 Observed historical V3 results
│   ├── Original eight-cohort mean confirmed hits:
│   │   ├── Bayesian lookahead 3.125
│   │   ├── Direct greedy 3.000
│   │   ├── Qwen3-4B 2.500
│   │   └── Random 2.234375
│   ├── PPO variants have not established consistent improvement over greedy
│   ├── Qwen option/menu ordering affected action choices in a diagnostic
│   └── Report target-wise outcomes and paired rather than pooled-seed claims
└── 6.6 Validity concerns
    ├── Historical follow-up panel is selection-biased
    ├── Recorded outcomes exist only for eligible purchased actions
    ├── Modeled assay costs are not verified laboratory savings
    ├── Action menus differ across some historical policy comparisons
    └── Recover original V3 ledgers and source-model provenance before final claim
```

**Figure 4 (main):** Discovery count (confirmed hits) versus modeled assay budget and/or target-wise paired comparison. Use original point-estimate rule for historical results unless a separately frozen re-evaluation is performed; do not conflate Qwen menu and full-pool action spaces.

**Interpretation:** This is the strongest **measured-outcome** environment and the primary benchmark contribution. A complex policy's failure to beat greedy is informative; no claim that greedy is universally optimal.

---

## 7. What counts as experimental evidence, and when is enough enough?

```text
7. Potency adjudication and sequential measurement
├── 7.1 Potency evidence from dose-response assays
│   ├── Exact in-range IC50 estimates
│   ├── Qualified upper/lower bounds when 50% crossing is outside tested range
│   ├── Unresolved or failed QC distinct from failed potency threshold
│   ├── MSH3 historical post-hoc rescoring: credit changed, policy did not
│   └── Independent F7 sealed pilot: qualification increased hit counts
│       for multiple methods, without established Qwen selection improvement
├── 7.2 Adaptive concentration selection experiment
│   ├── 93 development ASOs; 240 frozen assessment ASOs
│   ├── Historical reference: 239 resolved and one unresolved panel
│   ├── Full grid: 4.400 mean concentration readouts per ASO
│   ├── Fixed early stopping: 1.592; zero FP/zero FN on resolved references
│   ├── Bayesian information gain: 2.817; zero/zero on resolved references
│   ├── Decision-aware stopping: 1.683; one FP/two FN
│   ├── Fixed rule reduces retrospective readout count by 63.8%
│   ├── All early-stopping policies failed the unresolved-panel QC criterion
│   └── TMPRSS6 improvement is exploratory and not a general method win
└── 7.3 Scientific interpretation
    ├── Detecting potency-threshold evidence != verifying entire-curve QC
    ├── Fewer retrospective readouts != proportional lab cost savings
    ├── Full-curve reference agreement != independent biological truth
    └── Strong fixed stopping is an essential adaptive-method baseline
```

**Figure 5 (main):** Combine (a) illustrative exact/left-censored/unknown potency evidence and (b) measurements per ASO, error counts and unresolved-QC status. The QC failure must appear in the main text and/or figure caption.

---

## 8. Value of nonmyopic planning — analytical explanation

```text
8. Planning headroom under explicit assumptions
├── 8.1 Why calculate attainable headroom?
│   ├── A learned agent cannot systematically improve on an already-optimal rule
│   └── Quantify the gap before attributing poor PPO results to optimization
├── 8.2 Exact finite-horizon probabilistic task
│   ├── Four candidates in two pairs; hidden binary outcome prior
│   ├── Noisy initial screen and perfect confirmation, with explicit costs
│   ├── Uncertainty, dependence, prevalence, cost ratio and budgets varied
│   ├── 162 prespecified model settings
│   └── Exact dynamic programming; no hidden-outcome clairvoyance
├── 8.3 Results
│   ├── Optimal DP: mean expected hits 1.298591
│   ├── One-step Bayesian rollout: 1.296469
│   ├── Greedy: 1.260482
│   ├── PPO: 1.241975
│   ├── Random: 0.691171
│   ├── Greedy optimal in 108/162 settings
│   ├── Rollout optimal in 150/162 settings
│   └── Maximum optimal-minus-greedy gap 0.400 expected hits
└── 8.4 Limits and connection to V3
    ├── A synthetic explanatory model, not historical dose-response measurements
    ├── Task differs from real V3 gate/cost model
    └── Motivates, but does not prove, why greedy is competitive in Atlas replay
```

**Planning equation:**

\[
V^*(s)=\max\left(0,\max_a\sum_o P(o\mid s,a)\,[r(s,a,o)+V^*(s')]\right).
\]

**Figure 6 (if space permits):** Headroom heatmap for the prespecified planning slice, labeled clearly as a *model-based* expectation rather than an empirically observed ASO hit gain.

---

## 9. Discussion, synthesis, limitations, conclusion

```text
9. Discussion and conclusions
├── 9.1 What the two decision environments jointly teach us
│   ├── Molecular search: supervised proxy learning often matches PPO refinement
│   ├── Experimental selection: greedy/Bayesian approaches compete with PPO/LLMs
│   ├── The objectives and feedback sources differ fundamentally
│   └── Complexity does not guarantee a measured decision advantage
├── 9.2 Why evidence representation matters
│   ├── Assay units, exact/bounded/unresolved labels and applicability
│   ├── Online uncertainty and access to newly purchased results
│   └── Appropriate stopping criteria and reliable reference outcomes
├── 9.3 Contribution and practical implications
│   ├── Public-data-to-decision benchmark with explicit information restrictions
│   ├── Useful negative and positive comparisons with strong simple methods
│   ├── Operational guidance on when complex policies merit evaluation
│   └── Interfaces for eventual measured feedback on generated candidates
├── 9.4 Limitations
│   ├── Historical patent selection and sparse assay overlap
│   ├── Huesken siRNA not a direct ASO validation cohort
│   ├── Model-driven molecular rewards and unsupported chemistry contexts
│   ├── No independently qualified final molecular-design groups
│   ├── Unresolved dose-response QC panel
│   ├── Repeated seeds/candidate draws are not independent biological cohorts
│   └── No prospectively measured new molecules or realized monetary savings
└── 9.5 Closing claim
    └── Decision-centered evaluation should test predictions, proposals,
        purchases and evidence sufficiency under their proper budgets
        and feedback, rather than use proxy scores as a stand-in for discovery
```

---

## C. Figures and tables — narrative priority, not fixed page allocation

```text
CORE VISUAL STORY
├── Figure 1: Dual decision environments + data/evidence boundaries
├── Figure 2: Huesken measured-label learning curves (+ RNA-FM compact result)
├── Figure 3: Chemistry-constrained molecular-design search and pretraining/PPO
│   └── Best eligible surrogate utility vs total predictor calls
├── Figure 4: ASO historical assay-selection yield by policy and target
├── Figure 5: IC50 censoring + fixed/adaptive concentration stopping
└── Figure 6: Planning-headroom map (move to supplement if layout requires)

TABLES
├── T1: Datasets / endpoint types / model and feedback applicability
├── T2: Matched molecular-search methods, query costs, result and caveat
├── T3: ASO assay-selection policies, distinct interfaces and results
└── T4: Dose-response measurement counts, resolved errors and failed QC
```

**Preferred trade-off if the manuscript is dense:** Shorten generic algorithm descriptions and use the supplement for implementation details **before** reducing molecular-design RL back to a token paragraph. Keep the scientific qualifications wherever the main result appears.

---

## D. Supplementary evidence tree

```text
SUPPLEMENT / TECHNICAL REPORT
├── S1. Data inventories, original sources, eligibility and licensing
├── S2. OligoGym reproduction, feature conventions and split audits
├── S3. All acquisition variants, hybrid definitions, seeds and statistics
├── S4. RNA-FM frozen features, LoRA recipe and Atlas scaling controls
├── S5. Endpoint predictor registry, calibration and applicability checks
├── S6. Molecular grammar, masks, reward adapter and archive objective
├── S7. Candidate MLP pretraining, PPO architecture and query accounting
├── S8. Full molecular search target table and independent-evaluation audits
├── S9. Experimental-selection V1/V2/V3 data, state/action/reward contracts
├── S10. V3 target-level ledgers, PPO ablations and Qwen menus/diagnostics
├── S11. Potency adjudication, censored outcomes and original/frozen analyses
├── S12. Concentration-selection protocol, frozen assessment and QC failures
├── S13. Exact planning prior, 162-setting design, DP checks and PPO
└── S14. Statistical/evidence audits, reproducibility and threat-to-validity notes
```

Supplementary material must follow the venue's actual supplementary-file and anonymity rules. A non-anonymized public repository or artifact path should not appear in double-blind manuscript material.

---

## E. Claims-to-evidence gate before submission

- [ ] The two environments are described as **parallel decision tasks**, not an experimentally proven integrated loop.
- [ ] Distinguish **historical measured outcomes** from **frozen surrogate rewards** at every result.
- [ ] Verify/recover the original V3 ledgers, source fits and eligible pools for historical eight-cohort headline values; label unverified historical means as preliminary.
- [ ] Report V3 Qwen restricted-menu comparisons separately from full-action PPO/greedy comparisons.
- [ ] Keep original point-estimate and post-hoc censor-aware results distinct; do not claim the historical policies were rerun when only ledgers were rescored.
- [ ] Preserve the 240-ASO stopping assessment as frozen, including its unresolved-panel QC failure.
- [ ] Report molecule-search policy training and deployment expenditures separately; avoid implying equal total cost from equal deployment limits.
- [ ] Do not call six-of-eight molecular-search results independent held-out biological replication.
- [ ] State the Atlas 3%/5% source-composition caveat in the representation study.
- [ ] Avoid projecting ASO safety or IC50 from predictors trained on incompatible endpoints/assay settings.
- [ ] Keep Huesken (siRNA), ASO potency, risk endpoints and synthetic planning in distinct evaluation units.
- [ ] Ensure main claims can be traced to frozen reports and reproducible artifacts.
- [ ] Anonymize the manuscript and follow AAAI/AI2ASE venue formatting and submission requirements.

---

## F. Key bibliography anchors

**Direct data and application foundations**
- [OligoGym (NeurIPS 2025)](https://proceedings.neurips.cc/paper_files/paper/2025/hash/4927dd556ff6e49671e3a77ac1f12487-Abstract-Datasets_and_Benchmarks_Track.html)
- [ASO Atlas 2.0](https://github.com/barneyhill/aso-atlas-2)
- [OligoAI — ASO efficacy prediction](https://doi.org/10.1016/j.omtn.2026.103004)
- [ASOptimizer — ASO design](https://pmc.ncbi.nlm.nih.gov/articles/PMC11066473/)

**Sequential decision and molecular search precedents**
- [Efficient Nonmyopic Active Search](https://proceedings.mlr.press/v70/jiang17d.html)
- [Nonmyopic Multifidelity Active Search](https://proceedings.mlr.press/v139/nguyen21f.html)
- [OligoRL](https://doi.org/10.1093/bioinformatics/btac073)
- [PPO](https://arxiv.org/abs/1707.06347)

**Representations and measurement semantics**
- [RNA-FM](https://www.nature.com/articles/s41592-024-02487-0)
- [LoRA](https://arxiv.org/abs/2106.09685)
- [How Desirable Are Your IC50s?](https://doi.org/10.1177/1087057110384402)
- [COBALT: Censored Bayesian Learning/Optimization](https://proceedings.mlr.press/v337/karlova26a.html)

**Recommended submission framing:** A dual-environment, decision-centered evaluation paper with a main predictive/acquisition foundation, a substantial chemistry-constrained molecular-search study, and a measured-outcome experimental-allocation study. Clearly separate evidence quality and claim scope. The central scientific message is **when adaptivity and model complexity improve the actual decision made**, not whether a particular agent maximizes its own proxy reward.
