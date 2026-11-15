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
