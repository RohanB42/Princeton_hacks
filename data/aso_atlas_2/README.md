# ASO Atlas 2.0 local release

Source: https://huggingface.co/datasets/barneyhill/aso-atlas-2, `neurips-rebuttal` snapshot, linked from https://github.com/barneyhill/aso-atlas-2 . Source code HEAD inspected for this import: `bb90c946013f183379da04678340e193088e5f99`. The data release is identified by its tag and by the SHA-256 of each downloaded file in `cleaned/audit.json`. The upstream manifest is copied unchanged from that source code checkout; counts were verified against the downloaded release.

License: CC BY 4.0. Copyright 2026 Barney Hill, Nicola Whiffin, Stephan J. Sanders, Carlo Rinaldi. See `release/LICENSE_SOURCE.txt` and the source dataset card. We made derived preparation columns; the original release files are retained byte-for-byte in `release/`.

`release/` contains four endpoint Parquet files, the source dataset card, license, release manifest and the seven provided fold files. `cleaned/` contains one derived Parquet per endpoint plus `audit.json`. No source rows or original columns were removed or rewritten. Derived columns are documented in `docs/aso-atlas-data-cleaning-2026-11-14.md`. Rebuild with `/opt/anaconda3/bin/python scripts/clean_aso_atlas.py` in an environment with pandas and pyarrow. The script checks row counts, upstream eligibility, source-column equality after write/read, stable row IDs and release checksums.

These are patent-reported experimental measurements extracted by the upstream authors; they are not new wet-lab results or validated clinical outcomes. The `analysis_eligible` flag is a conservative convenience filter, not a statement of biological validity or a final model-training cohort. Review assay context and chemistry before fitting.
