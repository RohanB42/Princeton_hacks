# Data

`oligogym/` contains all 12 released processed datasets from pinned upstream commit
`97f5b9f58d9e445a8ecb0218037af7465c3708c0`: 337,593 measurement rows, about 18 MB
compressed, with the original registry and per-dataset JSON metadata. Inclusion was
explicitly requested by the repository owner on November 14, 2026.

Files are unchanged from upstream. [manifest.json](oligogym/manifest.json) records
source paths, SHA256 and byte counts; [NOTICE.md](oligogym/NOTICE.md) preserves
attribution and source-specific provenance caveats. The upstream license is included.

Run `make data-check` to verify every source file and validate every row. Run
`make setup-science` and `make data-smoke` for sampled cross-dataset pipeline checks.
See [dataset pipelines](../docs/dataset-pipelines.md) for full-data configuration,
split limitations and diagnostic status. Other downloaded data/transcriptomes remain
ignored. Generated metrics and run artifacts belong under ignored `artifacts/`.

## ASO Atlas 2.0

[`aso_atlas_2/`](aso_atlas_2/README.md) contains the separately authorized ASO Atlas
release, four lossless prepared endpoint tables, seven supplied fold files, source
attribution, and checksums. Its **283,521 assay rows** are not the same unit as the
upstream **295,007 assay readouts** (hepatic rows can contain multiple biomarkers).
The endpoint tables are in-vitro inhibition, dose response, hepatotoxicity, and
neurotoxicity. They are not pooled with OligoGym or automatically registered with
the existing training/acquisition runner.

See the [preparation audit](../docs/aso-atlas-data-cleaning-2026-11-14.md) before
designing experiments. Run `.venv/bin/python -m pytest tests/test_aso_atlas_integrity.py`
to verify the committed data/fold checksums without installing a Parquet runtime.
