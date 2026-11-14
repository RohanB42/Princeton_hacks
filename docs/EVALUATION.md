# Evaluation protocol

## Gate 1: source and baseline reproduction

Pin upstream to `97f5b9f58d9e445a8ecb0218037af7465c3708c0`.
Run `python -m oligo_engine.audit_upstream --checkout PATH --output artifacts/upstream.json`
against a clean checkout. The audit reads registry and benchmark summaries without
publishing datasets. It does not install, train or mark Gate 1 passed.

Verified source behavior:

1. `DatasetDownloader().download("Huesken")` resolves via the packaged registry to
   `Ichihara_2007_1`. `siRNA1` is absent from valid registry keys at this revision;
   Analysis.ipynb's SIRNA_MAP explicitly maps that benchmark alias to Huesken.
2. `nucleobase_split`: fit `KMersCounts(k=[1,2,3])` on all input HELM, L2 normalize,
   fit `KMeans(random_state=seed, n_clusters=8)`, and use the resulting labels as
   **groups** for `GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)`.
   Whole clusters are withheld; the test fraction is a fraction of groups, not a
   guaranteed row fraction. KMeans also depends on sklearn 1.4.0 defaults (`n_init`
   in particular). The `strand` argument affects only the non-kmer branch: the
   kmer branch uses KMersCounts defaults, so do not describe it as RNA1-only.
3. Target splitting also uses GroupShuffleSplit. Log unique targets and achieved
   row fractions; about 30 groups means substantial variance is plausible.
4. The upstream script calls its split without a random seed in each of five
   iterations. These are repeated stochastic holdouts, not a deterministic
   partition into five disjoint folds. Exact historical seed recovery is unresolved.
5. Split docstrings advertise returned cluster labels but the executable no-validation
   branch returns six values, ending in train/test indices. Validation-branch
   indices refer to the temporary subset; never treat them as global row indices.
   Initial integration must use `val_size=None`; create training-only validation
   separately and persist mappings.
6. The CSV has 45,950 rows. Group by dataset, split, featurizer and its arguments,
   model and its arguments, then average valid test Pearson values across folds.
   `siRNA1`'s best mean is 0.6309139529356906: CNN, OneHotEncoder with base/sugar/
   phosphate, depth 1, hidden_dim 64, kernel_size 3, max pooling (five rows).
   This is an upstream reference summary, **not our reproduced score**. Do not
   choose our models or policies using held-out labels to chase this number.

The Python 3.11 upstream environment installs with Poetry; model imports require
three additional packages. A frozen published linear configuration has been rerun
on five seeds. Its mean r=0.584832 versus reference 0.615865 misses the predeclared
0.03 tolerance by 0.001032. An independent published RF configuration also missed
tolerance (0.559096 vs 0.591037). Gate 1 remains open. See upstream-verification.md.
Investigate historical seed/environment identity. Approximate
agreement within 0.03 alone cannot establish an exact historical reproduction.
Do not reinterpret a different model's score as reproduction of the winning CNN.

## Sequential experiment protocol

November 14 scope update: the user authorizes full collection inclusion and generic
measured **diagnostic** replay with Gate 1 open. This enables engineering tests,
not research/benchmark claims. The collection CLI requires explicit diagnostic
purpose, preserves endpoint scales, records source and subset identity, and uses
local exact-sequence or target-group holdout. It never calls these nucleobase
reproduction. See dataset-pipelines.md. Measured research mode remains gated.

Freeze split membership before acquisition. For each split/seed/model pair, all
policies share eligible IDs, initial IDs, feature fitting rules and cumulative
budgets. Initial IDs are sampled uniformly without replacement from the eligible
training pool using a separate RNG from subsequent acquisition. Retrain a fresh
predictor each checkpoint. Reveals are atomic and unique; reject invalid batches
rather than silently replacing them. Clip only the final batch to the declared
maximum budget; reject budgets exceeding pool size.

Model transforms fit only the currently revealed training rows unless a different
training-pool-only transductive protocol is preregistered. Evaluation transforms
only apply a frozen transform. No label scaling, imputation or tuning uses test
or unrevealed pool labels. Persist original row order, IDs, source hashes, split
IDs, duplicate/family audit, and target groups. Exact HELM overlap across partitions
fails closed in the fixture runner; near-duplicate analysis remains an adapter task.

Score test predictions only after all acquisition decisions have completed. Store
predictions privately until then. Train a separate full-training-pool reference
after the campaign; its labels and predictions are never exposed to a policy.
Reference labels are recorded separately from campaign labels. Stop by budget,
never test performance. Collection diagnostics adapt requested caps to eligible
pool sizes, log actual settings, and mark unset thresholds `not_requested`.
Python boundaries prevent accidental access, not malicious
plugin sandbox escapes; reviewers must inspect policy and predictor dependencies.

## Metrics and fixed defaults

- Pearson r, RMSE, MAE at each checkpoint, with exact cumulative label count.
- Pearson is null with an explicit reason for constant predictions/truth or fewer
  than two rows. Never turn undefined correlations into zero.
- Synthetic fixture: seeds 0–4, initial 8, batch 7, maximum 32; final batch is 3.
  These are plumbing defaults, not recommended Huesken budgets.
- Measured study proposal: seeds 0–4, initial 50, batch 50; maximum must be frozen
  after checking eligible pool sizes, before scoring. Do not silently skip seeds.
- Summary bands: mean ± **sample standard deviation**, explicitly not confidence
  intervals. Record contributing seed counts for every metric. Paired policy
  differences require identical split/initial IDs and budget; add at Gate 2.
- Label efficiency: predeclare an absolute Pearson threshold, default proposal 0.60;
  first observed checkpoint at or above it, otherwise `not_reached`. No interpolation.
  The synthetic config uses 0.60 only to test serialization, with no scientific claim.
- Normalized trapezoidal area under the Pearson learning curve uses actual label
  counts over the declared budget interval. Undefined points make area null; no
  last-observation filling or cherry-picked window.
- Future discovery metrics (best activity, top-k/enrichment) need endpoint direction
  verified and a separate predefined objective. They are not substitutes for r.

## Required leakage and integrity checks

Test partition/ID uniqueness, duplicate sequences crossing the split, target-group
disjointness where applicable, invalid/duplicate/over-budget acquisition, oracle
denial for held-out IDs, and nonfinite labels/predictions. Spy predictors verify
every fit sees only revealed IDs. Poison test labels and require identical acquired
IDs/predictions; poison unrevealed pool labels and require an unchanged decision
prefix. Verify deterministic replay, full-pool isolation and exact partial batches.
All fixture outputs must identify synthetic provenance and failed/open Gate 1.

Gate 2 requires at least random and one uncertainty/diversity policy, five matched
seeds, defined uncertainty semantics, paired comparisons, real curves with stated
bands and a separate full-pool reference. Separation from random is not a gate:
an honest negative result passes scientific evaluation.
