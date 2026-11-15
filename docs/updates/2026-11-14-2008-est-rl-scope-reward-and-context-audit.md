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
