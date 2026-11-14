# Atlas RNA-FM execution status

Updated 2026-11-14 after completed bounded development experiments. Branch
`codex/atlas-rnafm-research`, base `42bb9b8`; isolated worktree
`/private/tmp/oligoal-atlas-rnafm-20261114`.

## Current conclusion

The bounded study is complete; no training process remains active. Chemistry-aware
RNA-FM and actual LoRA work technically, but this recipe does not demonstrate
better target adaptation or acquisition than strong classical controls. Larger
confirmation and target-adaptive acquisition are deferred on this evidence.
Seven reserved targets remain unscored. These are development diagnostics, not
validated therapeutic predictions or a full-paper reproduction.

## Completed evidence

- Strict chemistry parser, measured-label cohort and deterministic campaign manifests:
  133,304 rows, 97 source target identifiers, 157 patents. Source train 95,638 and
  source validation 14,614 after exclusions. Development: F7, STAT3, NLRP3.
- Native five-fold Atlas linear anchor: Pearson 0.19016, Spearman 0.20540,
  RMSE 30.16015. Released/native fold joins agree. The published numeric benchmark
  reference is absent, so numerical reproduction remains unverified.
- Classical study: 27 source fits and 171 target score records. At 200 target labels,
  target-only Ridge RMSE 19.6256; source Ridge + offset 19.6342.
- Real ASO FM integrity profile: exact cached/batched token parity, exact source
  restoration, actual LoRA updates, unchanged base checkpoint. CPU runtime.
- Frozen/LoRA study: 56 fits, 60 score records; all 28 LoRA fits changed adapters;
  all base-weight hashes preserved. Total 357 seconds; peak RSS 1.93 GB. At 200
  labels, frozen RMSE 22.3546 and LoRA 21.9861. Both lose to classical controls.
- Geometry study: 54 campaigns and 378 checkpoints, six policies, three targets,
  three paired seeds, initial 50 / batch 25 / cap 200. Fixed classical predictor.
  LoRA MaxDet RMSE-AULC is 0.108 points worse than classical MaxDet. All methods
  already cross the predeclared reference threshold at the shared initial budget;
  this threshold cannot demonstrate differential label savings.
- Validation: 160 core tests and 21 focused Atlas tests passed (14 overlap);
  repository Ruff lint/format, import and diff checks pass. Receipt audit confirms
  paired labels, no reserved target IDs, frozen-code hashes and source checkpoints.
- Reports, selected-ID ledgers, model receipts and two inspected figures exist
  locally under `artifacts/atlas-rnafm/`; generated artifacts remain ignored.

## Evidence and resumption

See `RESULTS.md` for tables and interpretation, `ENVIRONMENT.md` for execution and
checks, `TASKS.md` for exact completed/deferred gates, and `DECISIONS.md` for frozen
choices and post-result decisions. Artifacts:

- `preparation-v1/{audit,manifests}.json` and `cohort.parquet`
- `native-linear-anchor/report.json`
- `classical-development-v1/report.json`
- `fm-profile-v1/report.json`
- `fm-development-v1/{report,suite}.json`
- `acquisition-development-v1/report.json`
- `summary-v1/{summary.json,audit.json,transfer-curves.png,acquisition-curves.png}`

## Remaining limits

Target names are uppercased source identifiers, not externally resolved aliases.
Sequence grouping covers same-length Hamming <= 2 and exact one-base shifts,
not all homology. Source exclusions remove exact equivalents, not every neighbor.
Only 1,000 source measurements and one source seed were used for FM transfer;
three target seeds are not three independent biological targets. The seven reserved
campaigns cannot satisfy the planned >= 8-target confirmation. Clean-install
portability and published numeric anchor comparison remain unresolved.
