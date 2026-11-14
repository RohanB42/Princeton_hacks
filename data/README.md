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
