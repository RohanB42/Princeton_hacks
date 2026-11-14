# Gate 1 reproducibility study — November 14, 2026

## Question and scope

Explain the existing Huesken Random Forest baseline discrepancy before extending
acquisition experiments. Preserve the original five seeds, reference, tolerance,
and failed attempt. No new model family, favorable-seed search or tolerance change.

The unchanged upstream checkout at
`97f5b9f58d9e445a8ecb0218037af7465c3708c0` passes the source audit, including the
released data. Runtime inspection of `benchmarks/train_model.py:prepare_model`
finds a concrete mismatch: its signature filter removes `max_depth=20` from the
requested RandomForestModel arguments. The effective estimator has `max_depth=None`,
`random_state=None`, and `n_jobs=None`. The previous local rerun instead used
`max_depth=20`, `random_state=seed`, and `n_jobs=2`. CSV configuration strings alone
therefore do not establish effective-model equivalence. This finding does not prove
which historical execution produced the released benchmark CSV.

## Frozen checks, defined before executing the new reruns

1. `configs/gate1-rf-factory.toml`: same explicit split and estimator seeds 0–4 as
   the original RF attempt. Call upstream `prepare_model`, then restore only the
   previous estimator seed and two jobs. This isolates the effective depth change.
   Require identical ordered train/test row indices to the old attempt.
2. `configs/gate1-rf-benchmark.toml`: execute native downloader, `prepare_data`,
   `prepare_featurizer`, `featurize`, and `prepare_model`. Seed Python/NumPy with
   0–4 before each repeated holdout; let the upstream split and RF consume the
   shared RNG without estimator overrides. This matches executable helpers while
   declaring a new reproducible seed schedule; historical RNG states are unknown.
3. Repeat check 2 unchanged in a second process. Require exact ordered split IDs,
   effective parameters, feature shapes, prediction hashes, and metrics per seed.
   Runtime and process/environment bookkeeping are not equality criteria.

All runs use Huesken/siRNA1, OneHotEncoder base-only, 100 trees, the official
nucleobase split, and the same five published matching rows with mean Pearson
0.5910367239114824. Preserve the absolute 0.03 comparison tolerance. The script
still requests max_depth=20, as the published configuration does, but its factory
drops it; report both requested and effective parameters. No result here is the
winning CNN's 0.6309 score, an active-learning comparison, or a clinical finding.

Record every seed, Pearson/RMSE/MAE, data/source identity, exact split IDs, effective
estimator parameters, prediction hashes and the installed package-version inventory.
An inventory is not a portable dependency lock. Sample SD describes variation
across these repeated holdouts, not a confidence interval. A tolerance match alone
does not recover the historical experiment or close the exact-reproduction gate.

## Commands

Use the previously audited upstream Python environment; `UPSTREAM_PYTHON` below is
the path printed by the upstream Poetry environment. No new package installation
is required for these checks. From the project root:

```sh
PYTHONPATH=src MPLCONFIGDIR=/tmp/oligoal-mpl LOKY_MAX_CPU_COUNT=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  "$UPSTREAM_PYTHON" -m oligo_engine.reproduce \
  --checkout /tmp/oligoal-upstream-97f5b9f \
  --config configs/gate1-rf-factory.toml \
  --output artifacts/gate1-rf-factory-20261114.json
PYTHONPATH=src MPLCONFIGDIR=/tmp/oligoal-mpl LOKY_MAX_CPU_COUNT=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  "$UPSTREAM_PYTHON" -m oligo_engine.reproduce \
  --checkout /tmp/oligoal-upstream-97f5b9f \
  --config configs/gate1-rf-benchmark.toml \
  --output artifacts/gate1-rf-benchmark-20261114.json
```

Repeat the second command with a fresh output path ending in `-repeat.json`.
Existing results are never overwritten. The original `configs/reproduce-rf.toml`
retains direct-wrapper execution for reproducing the earlier failed attempt.

```sh
poetry run python scripts/check_baseline_repeat.py \
  --first artifacts/gate1-rf-benchmark-20261114.json \
  --repeat artifacts/gate1-rf-benchmark-20261114-repeat.json \
  --output artifacts/gate1-rf-repeat-check-20261114.json
```

## Results

All 15 new RF fits completed: five controlled factory runs, five benchmark-helper
runs, and an unchanged five-run repeat in another process. The reference's five
published values have mean 0.591036724 and sample SD 0.009126780.

| Execution | Mean test Pearson | Sample SD | Difference from reference | Within frozen 0.03? |
| --- | ---: | ---: | ---: | --- |
| Original direct-wrapper attempt, retained | 0.559096163 | 0.035515152 | -0.031940561 | No |
| Upstream factory, original explicit split/RF seeds | 0.560465806 | 0.035736056 | -0.030570918 | No |
| Upstream downloader/split/features/model helpers | 0.559768862 | 0.022574004 | -0.031267862 | No |
| Unchanged helper repeat, separate process | 0.559768862 | 0.022574004 | -0.031267862 | No |

The controlled factory check matches all five original ordered train/test row-ID
lists, frozen settings other than execution mode, and all 14 source hashes in the
original audit. Correcting the effective depth changes mean Pearson by only
+0.001369644 (paired sample SD 0.002544056). The mismatch is established, but it
does not explain the whole discrepancy. It does not justify changing the tolerance.

| Seed | Controlled factory test rows | Controlled factory r | Native helper test rows | Native helper r |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 535 | 0.540490641 | 712 | 0.588621818 |
| 1 | 783 | 0.512680496 | 716 | 0.537485413 |
| 2 | 567 | 0.559109344 | 674 | 0.560630365 |
| 3 | 541 | 0.590816894 | 631 | 0.574505256 |
| 4 | 677 | 0.599231656 | 685 | 0.537601456 |

The two modes generate different holdouts despite the same seed numbers: the
explicit-split protocol passes an integer separately to KMeans/GroupShuffleSplit;
the native helper passes neither and consumes the global NumPy RNG sequentially.
The difference between these modes cannot be attributed solely to model depth.

The strict repeat checker passes: exact ordered split IDs, effective parameters,
feature shapes, prediction SHA256, metrics, upstream source identity, local source
hashes, package inventory and aggregate statistics match. Runtime is excluded.
This establishes repeatability of our declared helper protocol in this environment,
not historical or cross-platform reproduction. `pip check` reports no broken
requirements; the existing three supplemental imports remain declared deviations.

Raw local artifacts are the three JSON files named in the commands, the repeated
helper file, and `artifacts/gate1-source-audit-20261114.json`. Generated artifacts
remain ignored. New tests protect parameter filtering, explicit RNG overrides,
split-config validation, repeat provenance and prediction equality.
Final local checks: 77 tests pass; Ruff lint, formatting and Git whitespace checks
pass. Source/data auditing and upstream dependency consistency checks also pass.

**Gate 1 remains open.** Next evidence needed is the original per-run
`train_indices.csv`/`test_indices.csv`, original effective estimator parameters,
generating-script revision, and environment/RNG state. The pinned training script
writes split indices, but these historical files are not included in the checkout.
Do not search for favorable seeds or introduce a different predictor to pass.
