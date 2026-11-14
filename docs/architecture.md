# Architecture and implementation status

`contracts.py` defines shared immutable records and Predictor/AcquisitionPolicy
protocols. `data` owns the synthetic fixture and restricted training oracle.
`acquisition` implements random selection. `evaluation` owns budget replay, deferred
test scoring, full-pool reference and metrics. `reporting` writes JSON/CSV and sample
standard deviation summaries. `models/fixture.py` is test plumbing only.

`audit_upstream.py` verifies a clean pinned checkout and records source hashes.
`reproduce.py` runs frozen published linear and RF configurations using upstream APIs in
its separately installed environment. The core fixture requires no scientific
dependencies; the measured-baseline tool intentionally requires the upstream stack.

November 14: `data/catalog.py` loads the entire vendored collection by source name,
key or benchmark alias, validates hashes/rows, preserves metadata and creates label
capabilities. `data/splits.py` provides local exact-sequence/target diagnostic
holdouts. `models/forest.py` is a fixed-dimension HELM character-hash RF diagnostic;
`acquisition/uncertainty.py` uses explicitly uncalibrated tree spread. `collection.py`
runs isolated per-dataset/per-policy campaigns with pool-adapted budgets and a
failure/unsupported ledger. No temporary upstream install is needed for this path.

Future: benchmark-validated production predictors/uncertainty, more policies,
plots and artifact-reading UI. `features` and `design` remain placeholders. Optional
chemistry-aware generation stays outside empirical acquisition evaluation.

OneHotEncoder is a proposed measured-model starting point, not a requirement for
reproducing a different published configuration. GP/TabPFN remain candidates;
upstream's GP wrapper does not expose a standard-deviation return argument and GP
intervals are not empirically calibrated by default. ViennaRNA/transcripts are
optional design work. Boltz is outside the inner loop.
