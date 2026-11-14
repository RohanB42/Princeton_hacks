# Huesken CNN label-efficiency pilot: frozen protocol

The user explicitly authorizes a subagent to implement and execute this study on
November 14, 2026, after reviewing its fit with the broader specification. This is
the P0 sequential efficacy benchmark and an initial Gate 2 policy comparison.
The seven-dataset reproduction effort remains incomplete numerically; Huesken's
published winning CNN already meets the frozen 0.03 comparison tolerance. This
scoped pilot does not mark historical or all-dataset Gate 1 complete. Retain the
existing explicit diagnostic purpose/status and measured provenance.

## Question and limits

Does sequence-diversity selection improve held-out Huesken efficacy prediction at
the same measured-label budget compared with random acquisition? Inputs are
original HELM strings; y remains the supplied reporter-assay percentage inhibition.
A null or negative result is valid. Diversity is label-blind coverage selection,
not a learned or efficacy-feedback-driven policy. This first study does not test
calibrated uncertainty, hit discovery, unseen-target generalization, ASO safety,
generation, RL, or clinical performance. These remain separate workstreams.

## Frozen methods

Executable declaration: `configs/huesken-learning.toml`. No local outcome informs
its settings. Source pin is 97f5b9f58d9e445a8ecb0218037af7465c3708c0; baseline CNN,
one-hot components and training hyperparameters come from the hash-verified
`configs/gate1-efficacy/Huesken.toml`. Keep CPU/deterministic execution, 100 maximum
epochs, training-internal 20% validation with random_state=42, patience 5, batch 32,
Adam lr=0.001 and weight_decay=0.01. No test-driven tuning or checkpoint selection.
Fit the one-hot encoder only on currently acquired rows, then freeze it for
prediction. Create a fresh CNN at every budget checkpoint.

Use all 2,431 observations and five official nucleobase holdouts corresponding to
the completed native-helper reproduction seeds 0–4. Regenerate these splits with
the pinned source function, NumPy's global RNG seeded immediately before each call,
default eight clusters and 3-mer settings. Dummy labels may be used when calling
the splitter; its grouping is sequence-only. Record full immutable split IDs and
verify exact membership against the existing Huesken baseline artifact when
available. Do not substitute local exact-HELM grouping or target splits. The kmer
split branch considers all strands despite the strand argument.

Within every seed, policies share test/pool membership, random initial 50 IDs,
CNN settings/seed, and checkpoints 50, 100, ..., 500. Use separate acquisition RNG
state. Reveals must be unique, eligible and counted; all labels come from measured
source rows. Retraining fits IDs in the runner's fixed lexicographic order.

Random selection is uniform without replacement. Diversity uses pinned native
KMersCounts(k=[1,2,3], modification_abundance=False), all strands, fit on eligible
training-pool sequences only. This acquisition-only transductive vocabulary uses
no pool labels and no evaluation sequences. Normalize each vector independently
to unit L2 length. Greedily choose the candidate maximizing its minimum Euclidean
distance to already labeled and newly selected batch points. Break exact ties by
immutable sample ID. Do not expose oracle/evaluator capabilities to this policy.

Fit a separate full-eligible-training-pool reference for each split/seed using the
same CNN and lexicographic fit order. Do not reuse the reproduction study's model
predictions or 0.6309/0.6096 averages as reference lines: changing fit order changes
neural validation membership and training randomness. Only reuse a freshly fitted
reference between policies when the runner's complete cache identity matches.
Full-reference labels/predictions never become acquisition inputs. Test scoring
remains deferred until all campaign acquisition decisions have completed.

## Outcomes and interpretation

Primary: paired normalized trapezoidal area under held-out Pearson-versus-labels
curves, diversity minus random, over labels 50–500. Report each seed, mean and
sample SD, with the number of valid paired seeds. Undefined points make that
seed's area undefined, with a reason; do not fill or silently omit seeds.

Secondary: Pearson/RMSE/MAE at every exact budget; mean ± sample SD curves and
per-seed full-pool references. The reporting-only threshold is each seed's positive
full-reference Pearson minus 0.03; report the first observed checkpoint reaching
it or not_reached. Also report its label fraction and the predeclared half-pool
criterion. No interpolation, policy feedback, stopping on test metrics, or savings
ratio when a comparator never reaches the threshold. Show absolute reference
quality; matching a weak model is not strong evidence of useful discovery.

## Ownership, acceptance and execution

Integrator owns this protocol/config and shared contracts, runner, metadata,
lockfiles and documentation. The delegated agent owns new CNN adapter, diversity
policy, Huesken study CLI/reporting code and dedicated tests only; propose any
shared-file changes to the integrator. Existing source/results stay intact.

Acceptance: meaningful leakage/pairing/determinism checks; actual one-seed vertical
slice; then ten campaigns (two policies × five seeds), 100 budget-checkpoint fits
and five independent full-pool references (shared only across matched policies).
Deliver a one-command runner, frozen config, per-run ID/config/environment ledgers,
paired statistics, learning-curve PNG/SVG and an honest outcome. Generated outputs
belong under ignored `artifacts/`; do not commit datasets beyond the authorized
release, weights, PDFs, secrets or generated run artifacts. Do not push changes.

Archive executed source/config hashes before interpreting outcomes. Finish the
experiment without changing policies, budgets or models after seeing curves.
If an implementation bug requires correction, preserve and explicitly supersede
the affected attempt and rerun the fixed protocol consistently.
