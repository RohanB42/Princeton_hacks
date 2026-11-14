# OligoAL — oligonucleotide active-learning research

Can sequential experiment selection improve siRNA efficacy prediction using fewer
measured labels than random acquisition? This HackPrinceton project is building an
open, auditable retrospective benchmark. Current diagnostic comparisons have mixed
results; a consistent active-learning advantage has not been established.

**Current status:** all 12 released datasets are included, with a shared measured-data
diagnostic runner, source integrity checks, and random/uncertainty replay. All 337,593
source rows have been validated. Full-data five-seed experiments now comprise
**180 campaigns**: both policies on all 12 exact-sequence-group datasets, plus both
policies on the six supported target-held-out datasets. Requested budgets are
50/100/…/500 labels, capped by pool size, with a separate full-pool reference.
Uncertainty has higher mean learning-curve area on 5/12 sequence-group tasks and
lower area on 7/12; these are separate tasks, not a combined score.
See [full protocol and results](docs/full-experiment-protocol.md) and
[collection commands and limits](docs/dataset-pipelines.md).

Historical **Gate 1 remains open:** the
published linear configuration reruns at Pearson **0.5848 ± 0.0243 sample SD**, versus
upstream mean **0.6159**. Its 0.0310 gap exceeds the frozen 0.03 tolerance. This is
not reproduction of the winning CNN (upstream mean 0.6309), and it is not an
active-learning comparison. A published Random Forest cross-check also misses the
frozen tolerance (0.5591 versus 0.5910 reference). See
[verification and discrepancies](docs/upstream-verification.md).

## Run the tested vertical slice

Use Python 3.11 and Poetry 2.1.4:

```sh
make setup
make lint format-check import-check test
make fixture
```

For the full collection and cross-dataset diagnostic checks:

```sh
make setup-science
make data-check
make data-smoke
```

The science group supports Python 3.11/3.12. Released data and attribution live in
`data/oligogym/`. Validation scans every row; the smoke command samples 128 rows per
dataset and runs random and uncertainty policies separately. These are engineering
checks, not evidence of generalization or active-learning benefit. Historical
reproduction remains separate; incompatible endpoints are never pooled.

`make fixture` writes five **synthetic** runs (seeds 0–4) to `artifacts/fixture/`:
individual JSON artifacts, `metrics.csv`, and `summary.json`. It reveals 8 initial
labels, then batches of 7, stopping at exactly 32; a separate 36-label full-pool
model is recorded. Summary dispersion is sample standard deviation, not a confidence
interval. The fixture exercises contracts and leakage boundaries; it provides no
biological evidence. An existing output directory is preserved; use a fresh path:

```sh
poetry run python -m oligo_engine --config configs/fixture.toml --output artifacts/fixture-new
```

The fixture needs no scientific packages, external datasets, weights, GPU or service.
Collection validation uses the vendored data and Python standard library. Measured
diagnostics use the optional locked science group; official baseline checks use the
separate pinned upstream environment described in the verification document.

## Structure and next steps

`src/oligo_engine/contracts.py` defines label-free records, predictor/policy contracts
and run artifacts. `data/`, `acquisition/`, `evaluation/`, `models/`, and `reporting/`
implement synthetic and measured diagnostic replay. `collection.py` validates and
runs individual datasets or the complete collection. `audit_upstream.py` verifies
source identity; `reproduce.py` supports dataset-specific upstream baseline reruns.
`design/`, `features/`, and
`app/` remain future work. Runtime package names stay `oligo-design-engine` and
`oligo_engine`. TOML fixture/collection/reproduction configs are executable; YAML examples are
planning templates.

Read [SPEC](docs/SPEC.md), [EVALUATION](docs/EVALUATION.md),
[INTERFACES](docs/interfaces.md), and the
[dependency/ownership plan](docs/IMPLEMENTATION_TASKS.md). Resolve baseline numerical
and historical environment discrepancies before claiming benchmark-comparable acquisition results.
The main study now focuses on efficacy: Huesken first, other siRNA datasets as
independent replications, and ASO efficacy as separate extensions. Existing safety
and immunomodulation diagnostics remain auxiliary.
Then compare random and uncertainty/diversity acquisition at matched budgets and
initial IDs on fixed tests across at least five seeds; report negative results.

Nucleobase cluster holdout is the published comparison; target holdout is separate
new evaluation. Keep evaluation labels out of training, acquisition, feature fitting,
tuning and stopping. Huesken siRNA efficacy and ASO safety are independent tasks:
do not combine incompatible endpoints into a safe/effective label. No wet-lab,
therapeutic efficacy, clinical safety, exclusive novelty or proprietary-engine
equivalence is claimed. Generated molecules would remain unvalidated hypotheses.

Project license and dataset/weight rights still need owner review before publication.
Released datasets are explicitly authorized for this repository with source notices;
generated artifacts, other datasets, PDFs and weights remain ignored.
