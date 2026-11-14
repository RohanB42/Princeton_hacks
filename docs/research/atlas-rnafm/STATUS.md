# Atlas RNA-FM execution status

Updated 2026-11-14 during autonomous research execution. Branch
`codex/atlas-rnafm-research`, base42bb9b8; worktree
`/private/tmp/oligoal-atlas-rnafm-20261114`.

## Completed

- Pinned Atlas source bb90c946013f183379da04678340e193088e5f99 inspected.
- Isolated .venv-atlas Python3.11 runtime with read-only upstream/RNAFM package paths;
  only PyArrow21.0.0 newly installed. No shared runtime mutated.
- Strict monomer/strand/terminal parser and cohort preparation implemented.
- Cohort133304 rows,97 target identifiers,157 patents; source training95638 and
  source validation14614 after excluding all allocated targets/patents/base equivalents.
- Ten campaign manifests: development F7,STAT3,NLRP3; seven reserved targets unscored.
- Five-fold native linear anchor: Pearson0.19016, Spearman0.20540, RMSE30.16015.
  All fold joins agree. Published numeric benchmark reference absent; no claim of
  numerical reproduction. Native max-over-context aggregation stays separate.
- Classical development matrix completed:27 source fits and171 target score records.
  At200 target labels, target-only Ridge RMSE19.6256 and source Ridge+offset19.6342.
  No meaningful transfer advantage established by these descriptive numbers.
- Eleven parser/acquired-label/context/sequence-boundary tests passed.

## In progress

Actual single-strand chemistry/LoRA integrity profile completed successfully.
Frozen/LoRA comparison is running: session9807, log
`artifacts/atlas-rnafm/fm-development-v1.log`, progress suite JSON in the matching
output directory. No final/reserved-target evaluation.

## Evidence and commands

All paths relative to worktree; generated evidence remains ignored.

- `artifacts/atlas-rnafm/preparation-v1/{audit,manifests}.json`, `cohort.parquet`
- `artifacts/atlas-rnafm/native-linear-anchor/report.json`
- `artifacts/atlas-rnafm/classical-development-v1/report.json`
- `artifacts/atlas-rnafm/fm-profile-v1.log` (active profile)
- Config: `configs/atlas/development-v1.json` frozen before model outcomes.

Use `PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv-atlas/bin/python`
with `scripts/prepare_atlas_study.py`, `scripts/reproduce_atlas_linear.py`,
`scripts/run_atlas_classical.py`, or `scripts/profile_atlas_fm.py`; see argparse for
required output/upstream paths. Source fits and target measurements are accounted
separately; final target predictions are scored only after fitting decisions.

## Limits

Target names are uppercased source identifiers, not externally resolved aliases.
Campaign sequence groups cover same-length Hamming<=2 and exact one-base shifts,
not all homology. Source exclusions remove exact equivalents, not every neighbor.
Seven reserved target groups are insufficient for the proposed >=8-target final
confirmation. Future extension requires new independent cohorts or a revised,
prospectively justified power plan, not relabeling seeds as independent targets.
