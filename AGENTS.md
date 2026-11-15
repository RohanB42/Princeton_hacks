# Agent guidance

Before implementation read `docs/project-context.md`, `docs/evaluation-protocol.md`,
`docs/decisions.md`, `docs/open-questions.md`, then canonical `docs/SPEC.md`,
`docs/EVALUATION.md`, and `docs/interfaces.md`. The November 13 revised handoff
supersedes conflicting v5 claims. Roadmaps alone do not authorize new work.

- Python 3.11, Poetry 2.1.4. `make setup`; `make lint format-check import-check test`.
  `make fixture` runs synthetic plumbing only. Ruff formatting, 88 columns, type
  annotations on public interfaces; meaningful invariant tests for scientific code.
- Preserve measured-label provenance. Test labels never reach fitting, acquisition,
  feature fitting, tuning, stopping, or RL rewards. Predictions are not observations.
- Keep siRNA efficacy separate from incompatible ASO endpoints. Generated molecules
  remain unvalidated hypotheses; no combined clinical safety/efficacy claims.
- Pin/verify OligoGym before API use; never invent handles. Gate 1 reproduction
  precedes novel modeling and measured active-learning claims. Record discrepancies.
- Work only in assigned files. Integrator owns contracts, metadata, configs and
  lockfiles; owners propose changes before merge. Use disjoint branches/worktrees
  and tests; preserve the known-good pipeline. See docs/IMPLEMENTATION_TASKS.md.
- Report actual checks and results, including undefined metrics and negative results.
  The November 14 user instruction authorizes the pinned released datasets under
  data/oligogym/ and general measured-data diagnostic pipelines. Preserve their raw
  bytes, metadata, license and manifest. This supersedes the earlier dataset exclusion
  and permits explicitly labeled diagnostic replays while Gate 1 remains open.
  The subsequent November 14 request also authorizes the ASO Atlas release and
  lossless preparation under data/aso_atlas_2/; keep its separate endpoint contracts
  and audit before model integration. Never commit secrets, other datasets, PDFs,
  weights or generated run artifacts. Do not
  publish or select a project license without owner review of rights.

- November 14 checkpoint-publication exception: the user explicitly requested
  committing/pushing the existing prediction checkpoints listed in
  `model_checkpoints/manifest.json`. Those trained weights and their provenance
  metadata may be versioned under `model_checkpoints/`. This does not authorize
  other generated run artifacts, RL policy weights, new training, or redistribution
  of the separately downloaded RNA-FM backbone; its verified source/hash is recorded.
