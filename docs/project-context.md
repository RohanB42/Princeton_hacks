# Project context

Current direction: November 13, 2026 revised implementation handoff, which supersedes
conflicting claims in the November 11 v5 plan. Canonical specification:
[SPEC.md](SPEC.md), [EVALUATION.md](EVALUATION.md), [interfaces.md](interfaces.md).

Question: can sequential acquisition improve out-of-sample siRNA efficacy prediction
using fewer measured labels than random acquisition? The scientific thesis is not
established under a benchmark-comparable protocol here.
The core is a reproducible select/reveal/retrain/evaluate loop with matched budgets,
fixed evaluation rows and a full-training-pool reference. Negative results count.
Full-data diagnostic comparisons are now complete; see full-experiment-protocol.md.

Default: independent Huesken siRNA efficacy benchmark. ASO activity/safety models,
biological design, RL and a product surface are separate optional workstreams.
The accepted November 14 reporting focus is efficacy: Huesken first, other siRNA
efficacy datasets as replications, and ASO efficacy as separate extensions. Existing
toxicity and immunomodulation diagnostics remain auxiliary. The immediate priority
is trustworthy baseline reproduction before further acquisition-method expansion.
Incompatible siRNA and ASO datasets must not form a shared safety/efficacy claim.
This project neither reproduces Creyon's engine nor establishes proprietary data
unnecessary. Novelty remains provisional. Proposed molecules are hypotheses.

Implemented: typed contracts, protected training oracle, synthetic replay, source audit,
and dataset-specific baseline reruns. The November 14 user instruction additionally
authorizes all 12 released datasets in the repository and measured diagnostic replay
across them. Catalog integrity, duplicate-aware local splits, adaptive budgets,
random/uncertainty policies and isolated artifacts now support every dataset. Full
source rows are validated; sample-capped diagnostic runs are engineering evidence,
not scientific generalization. Full-data five-seed matrices now total 180 campaigns
with mixed acquisition effects; the benchmark reproduction gate remains open. No app
or design agent is implemented. See dataset-pipelines.md for current commands/limits.
See [upstream verification](upstream-verification.md) for actual checks and blockers.
