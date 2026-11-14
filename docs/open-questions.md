# Open questions

- Historical alias `siRNA1` -> Huesken is verified in Analysis.ipynb; pinned downloader
  keys are verified. TLR7/TLR8 registry descriptions disagree with their keys; the
  assay/source mapping needs resolution before either endpoint is modeled.
- What are the MOE assay species, route, dose, outcome direction, and patent provenance?
- Default is separate siRNA and ASO tasks. Any future transfer study needs its own
  evidence; missing endpoints remain missing.
- Which uncertainty type/calibration, acquisition rule, label budgets, confidence-band method, and full-data tolerance will be preregistered?
- What license should this project adopt, and what are each dataset's and weight's usage rights?
- Historical split seeds are absent from upstream training code. Can original split
  manifests or a seed schedule be recovered? Exact reproduction is currently open.
- Why do both frozen linear and RF configurations miss their reference means by
  about 0.032? Validate original split/environment provenance rather than assuming
  solver conditioning explains both or searching for favorable seeds.
- Upstream model imports require catboost/torch-geometric/torchinfo beyond its main
  dependency declaration. Freeze the additional environment before broader experiments.
