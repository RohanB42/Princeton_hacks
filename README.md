# OligoAL — oligonucleotide active-learning research

Can sequential experiment selection improve siRNA efficacy prediction using fewer
measured labels than random acquisition? This HackPrinceton project is building an
open, auditable retrospective benchmark.

**ASO design diagnostic (November 14, 19:10 EST).** A supported 20-mer MOE efficacy
model now connects to the design environment. Its preselected top 20 ranked held-out
recorded assays above random by 10.89 and 9.88 inhibition percentage points on two
development targets. Three real-predictor PPO runs did not improve over the starting
candidate on the final window; the expansion gate stopped larger runs. This is
efficacy-only computational evidence, with safety and generated molecules unvalidated.
See the [protocol, results and reproduction instructions](docs/supported-aso-results-2026-11-14.md).

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

**Second endpoint (safety), 2026-11-14.** On MOE acute neurotox (`MOE_Neurotox_1`,
2,437 PS/2'-MOE gapmer ASOs, rounded 3h mouse FOB score), a one-hot GP that encodes
sugar and phosphate reaches Pearson r 0.597 +- 0.112 and Spearman 0.580 over 30 seeds
on the official `nucleobase` split. Both comparable published RF anchors reproduce
within noise, and encoding the gapmer wing/core pattern beats nucleobases alone in 28
of 30 paired seeds. This endpoint stays strictly separate from siRNA efficacy: no
combined safety/efficacy score exists and none is claimed. See
[the endpoint study](docs/neurotox-moe-predictor.md).

**Immunomodulation endpoints, 2026-11-14.** Both Alharbi 2020 TLR assays, 192 ASOs
each, 30 seeds on the official `nucleobase` split: TLR8 potentiation at Pearson
r 0.666 +- 0.115 (GP) and TLR7 inhibition at 0.598 +- 0.097 (RF). Both published RF
anchors reproduce within 0.01, the closest reproductions in the project. Resolving
these endpoints required fixing an upstream labelling bug: the registry's `key`
column is swapped relative to the assay descriptions, so the published row labelled
`immune_modulation_TLR7` is in fact the TLR8 assay. See
[the endpoint study](docs/tlr-immunomodulation-predictors.md).

**ASO efficacy, 2026-11-14.** ASOptimizer (`Hwang_2024_1`, 32,602 gapmers,
percentage knockdown): the published RF anchor reproduces at 0.4326 +- 0.0594 against
0.4094 (z +0.67). Within the PS/2'-MOE design space the surface designs in (5,586
chemistry-matched rows, 5 targets), a GP reaches r 0.317 +- 0.061 over 30 seeds --
a weak signal, about a tenth of the variance in knockdown, and the page labels it as
such. The siRNA efficacy model (Huesken, r 0.616) is deliberately **not** applied to
ASO candidates. See [the endpoint study](docs/aso-efficacy-predictor.md).

**Initial Huesken baseline reassessment:** the separate 30-seed linear/RF study
reports agreement under its noise-aware criterion (gaps -0.021 and -0.027).
Its criterion was revised after the original five-seed results. This does not
close the expanded seven-dataset reproduction requirement described below.
Exact historical folds and runtime identity remain unavailable. See
[the reassessment](docs/gate1-resolution.md) and
[original discrepancies](docs/upstream-verification.md).

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

These 180 campaigns used the hashed-HELM forest on local diagnostic splits and
remain engineering coverage, separate from the official-split studies above.

The expanded [published-best efficacy study](docs/gate1-efficacy-reproduction.md)
completed **35 full-data fits across all seven efficacy datasets**. Four meet
the original 0.03 Pearson tolerance: Huesken, Shmushkovich, siRNAmod and Sherwood.
Huesken's winning CNN reaches **0.6096 versus 0.6309** published. Ichihara, OpenASO
and ASOptimizer remain outside tolerance. Full seven-dataset numerical and exact
historical reproduction are therefore unresolved.

The [native-helper study](docs/gate1-reproducibility-study.md) also identifies an
RF argument-filter difference: the upstream factory drops max_depth. Preserve
requested versus effective parameters when interpreting the separate 30-seed
linear/RF reassessment. Approximate numerical agreement is not exact reproduction.

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
`features/` provides predictor representations; `design/` and `app/` now contain
a separate hypothesis-ranking demonstration. See [the app guide](app/README.md). Runtime package names stay `oligo-design-engine` and
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

### Model-informed Huesken active learning

The four-policy GP development runner compares random, diversity, model uncertainty
and a fixed hybrid with initial-label-only kernel selection. See
[the protocol and run commands](docs/active-learning-development.md). It writes
paired reports and learning curves from measured replay; it does not establish
label savings merely by running. The completed CNN diversity pilot remains separate.

### RNA-FM representation and adaptation studies

[Verified frozen embeddings](docs/rnafm-provenance.md), matched
[prediction/geometry studies](docs/rnafm-study.md), and a bounded
[LoRA proof](docs/rnafm-lora.md) are implemented. Frozen strand-mean embeddings
underperformed one-hot Ridge and did not consistently improve diversity acquisition.
The [multi-seed LoRA comparison](docs/rnafm-lora-comparison.md) is implemented;
its full experiment is still running separately. These studies do not establish
therapeutic benefit or a general foundation-model advantage. Research runtimes
are documented separately and are not included in the core dependency lock.

The five-seed GP development study in active-learning-development.md uses a
half-uncertainty/half-coverage hybrid and initial-label-only kernel selection.
It differs from acquisition-comparison.md's uncertainty-prefiltered diversity
policy and predictor protocol. Their outcomes must not be pooled.
