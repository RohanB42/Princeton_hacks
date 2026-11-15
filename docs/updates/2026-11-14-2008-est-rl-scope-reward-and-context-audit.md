# RL scope correction, reward ablation and context audit

Recorded November 14, 2026, 20:08 EST / November 15, 01:08 UTC.
This update consolidates the side-conversation experiments and the subsequent
discussion of the intended hackathon deliverable. It clarifies earlier statements
that the molecular-design environment was implemented: **a constrained target-site
search prototype exists; the full proposed ASO molecular-design system does not.**

## Scope and expectation correction

The user supplied a broader specification: chemistry-aware ASO design with
biologically compatible efficacy/risk predictors, constrained design actions,
independent evaluation, and a scientist-facing workflow. Starting with a narrow
prototype was reasonable for verification, but treating that prototype as the
completed environment was an execution and communication failure. The limited
predictor coverage is a dependency to resolve, not an implicit reduction of the
agreed deliverable.

Implemented and tested:

- Gymnasium/MaskablePPO interaction, legality masks, bounded episodes, scoring
  ledgers, frozen inference, reproducible checkpoints and conventional search.
- A fixed-chemistry, 20-nucleotide ASO binding-window search with a real efficacy
  predictor and explicit unknown safety status.
- Matched-cost optimizer diagnostics, a controlled reward-objective ablation and
  a follow-up observation/training-context audit.

Not completed:

- Supported chemistry-editing actions, variable lengths or gap/wing design.
- An integrated, applicable multi-endpoint efficacy/toxicity reward system.
- Independent biological evaluation of generated candidates or demonstrated PPO
  superiority over credible optimizers.
- The complete scientist-facing molecular-design workflow.

The original project distinction remains: molecular design and experimental
selection are different research problems. Standalone candidate-selection RL was
dropped; conventional ranking/shortlisting remains useful. This update concerns
the molecular-design prototype, not a new active-learning or assay-allocation study.

## What the current environment actually does

A fixed target transcript supplies candidate binding windows. The chemistry is a
20-mer MOE 5 / DNA 10 / MOE 5 gapmer with full PS backbone and methylated cytosines.
Choosing a window determines its complementary ASO sequence; the agent does not
independently invent arbitrary bases or modify chemistry.

Actions are STOP, LEFT and RIGHT. LEFT shifts the target window by one nucleotide
toward lower transcript coordinates; RIGHT shifts it toward higher coordinates.
For example, target positions 101–120 become 100–119 or 102–121. These are binding
site changes, not physical rotations or changes in molecular orientation.

The evaluated local spaces have 17 candidate sites, an eight-move horizon and up
to nine unique evaluations including the starting candidate. Conventional jump
proposals pay for every intermediate local move; caches and budgets are separate
per run. Enumerating all 17 sites is a separate, higher-scoring-budget reference.

The frozen position-one-hot Ridge predictor was fitted on 2,000 measured ASOs in
one supported profile: human HepG2, electroporation, 4,500 nM, 24 hours. It predicts
inhibition percentage, converted to utility against a fixed training-prediction
reference. That utility is not measured efficacy, calibrated uncertainty or a
clinical safety score. See the [supported-profile study](../supported-aso-results-2026-11-14.md).

## Predictor ranking evidence is separate from PPO evidence

The model's predicted top 20 achieved mean measured inhibition of 72.35 versus a
random expectation of 61.46 on ATXN2 (74 held-out records), and 64.65 versus 54.77
on DGAT2 (1,828 records). PPO was not involved in this ranking test.

A side-conversation post-hoc analysis sampled 200,000 random panels of 20 without
replacement per target, seed 20261114. One-sided p-values were approximately
0.00470 and 0.02391; Holm-adjusted values were 0.00940 and 0.02391. Two-sided
absolute-centered values were 0.01427 and 0.05525. Each target's pool comes from
one patent, so this is conditional finite-pool ranking evidence, not independent
replication across patents or proof of novel-molecule quality. The statistical
calculation ran in memory; this paragraph records its output, not a committed
standalone statistical test implementation.

## Broader evaluation exposed an objective mismatch

The initial synthetic comparison gave unrestricted proposals to some optimizers
while PPO had to traverse intermediate sites. That confound was corrected before
the subsequent real-surrogate local-search comparisons.

The side-conversation expansion evaluated the three existing frozen policies on
24 additional non-overlapping FGFR4 regions, across budgets 3/6/9 and seven methods:
1,512 runs, not 1,512 independent tasks. All movement and validity checks passed.

At budget nine, mean best-visited utility was PPO 0.637, genetic 0.796, random 0.786,
greedy 0.737, left sweep 0.867 and right sweep 0.819. PPO visited only 2.06 distinct
candidates on average. It lost to genetic search on 22 regions and tied on two.

However, PPO had been trained to maximize **final-position utility**, whereas
search returned the **best candidate visited**. On final-position utility, PPO
averaged 0.540 versus random 0.522, genetic 0.507 and greedy 0.505. All paired
window-bootstrap intervals for those PPO advantages included zero. Furthermore,
the conventional algorithms were not designed to finish physically at their best
site, so changing the reported metric alone did not fully align the comparison.

The useful objective for a design tool that can return any evaluated candidate is
best-discovered quality under budget. This motivated an explicit reward ablation,
rather than interpreting the earlier metric as a general verdict on PPO.
