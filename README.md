# OligoAL — oligonucleotide active-learning research

Can sequential experiment selection improve siRNA efficacy prediction using fewer
measured labels than random acquisition? This HackPrinceton project is building an
open, auditable retrospective benchmark.

**Headline result (2026-11-14).** On Huesken (`Ichihara_2007_1`) with a one-hot
Gaussian-process predictor and the official OligoGym `nucleobase` split,
uncertainty-driven acquisition beats random acquisition at matched label budgets:
normalized AULC +0.0095 [95% CI +0.0043, +0.0146], dz 0.57, paired t-test
p = 0.00095, 28 of 40 seeds above random. The hypothesis and the analysis were
frozen in commit `6a715bc` **before** these 40 seeds (110-149) were run; an earlier
exploratory set (seeds 100-109) is reported separately and is not pooled with it.
What is **not** supported: a significant label saving (mean 72 labels, p about
0.08), superiority of uncertainty over diversity or the hybrid, any target-gene
generalization claim, and any transfer to other endpoints. See
[the four-policy comparison](docs/acquisition-comparison.md) and
[figures](docs/figures/).

**Gate 1 is closed** under a 30-seed noise-aware criterion: the frozen linear and RF
configurations reproduce within noise, not exactly (gaps -0.021 and -0.027, both
inside 2 combined SE). Upstream's published folds are unseeded, so exact
reproduction is unrecoverable and is not claimed. See
[the Gate 1 resolution](docs/gate1-resolution.md), whose reading supersedes the
pass/fail verdict in [upstream-verification.md](docs/upstream-verification.md).

**Collection status:** all 12 released datasets are included, with a shared measured-data
diagnostic runner, source integrity checks, and random/uncertainty replay. All 337,593
source rows have been validated. Full-data five-seed experiments now comprise
**180 campaigns**: both policies on all 12 exact-sequence-group datasets, plus both
policies on the six supported target-held-out datasets. Requested budgets are
50/100/…/500 labels, capped by pool size, with a separate full-pool reference.
Uncertainty has higher mean learning-curve area on 5/12 sequence-group tasks and
lower area on 7/12; these are separate tasks, not a combined score.
See [full protocol and results](docs/full-experiment-protocol.md) and
[collection commands and limits](docs/dataset-pipelines.md).

These 180 campaigns used the hashed-HELM forest on local diagnostic splits (r about
0.25 on Huesken) and are **not** comparable to the baseline-grade result above or to
the published leaderboard. The headline study supersedes them as evidence; they
stand as engineering coverage. See
[verification and discrepancies](docs/upstream-verification.md) for the original
5-seed reproduction misses, which are superseded by `docs/gate1-resolution.md`.

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
