# Open questions

- Historical alias `siRNA1` -> Huesken is verified in Analysis.ipynb; pinned downloader
  keys are verified. **TLR7/TLR8 resolved 2026-11-14**: the registry `key` column is
  swapped relative to the assay descriptions, which are correct. `Alharbi_2020_1` is
  TLR8 potentiation (published as `immune_modulation_TLR7`) and `Alharbi_2020_2` is
  TLR7 inhibition (published as `immune_modulation_TLR8`); established from label
  scales, benchmark RMSE magnitudes and Alharbi et al. NAR 2020. See
  `tlr-immunomodulation-predictors.md`. Worth reporting upstream.
- What are the MOE assay species, route, dose, outcome direction, and patent provenance?
- Default is separate siRNA and ASO tasks. Any future transfer study needs its own
  evidence; missing endpoints remain missing.
- Which uncertainty type/calibration, acquisition rule, label budgets, confidence-band method, and full-data tolerance will be preregistered?
- What license should this project adopt, and what are each dataset's and weight's usage rights?
- Historical split seeds are absent from upstream training code. Can original split
  manifests or a seed schedule be recovered? Exact reproduction is currently open.
- Can original per-run split indices, effective parameters and generating-script
  revision be recovered? Upstream drops RF max_depth; correcting that changes the
  mean by only 0.00137 on the original splits. Native helper execution repeats
  exactly at r=0.559769 but remains 0.031268 below its published reference. Neither
  argument filtering nor linear conditioning explains the whole discrepancy.
- Published best-model runs now cover every efficacy dataset. Why do the fixed
  Ichihara MLP, OpenASO ridge and ASOptimizer CNN comparisons remain outside 0.03?
  Public data blobs and relevant training/feature source match the benchmark-update
  revision; old/new prediction methods agree exactly on the frozen Ichihara seed-0
  diagnostic. Recover historical splits/runtime before attributing the gaps to
  a particular cause or altering models/seeds. See gate1-efficacy-reproduction.md.
- Upstream model imports require catboost/torch-geometric/torchinfo beyond its main
  dependency declaration. Freeze the additional environment before broader experiments.
