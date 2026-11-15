# Experimental-selection RL

This environment selects which already recorded ASO efficacy assay to reveal at
each step of a retrospective campaign. It is separate from the ASO molecular
designer and uses the Atlas 2.0 measured in-vitro inhibition table. The order
of revelation is simulated. See the [codebase map](CODEBASE_MAP.md) and
[measured replay results](RESULTS.md).

## Reproduce

From the Princeton_hacks repo root on Python 3.11:

```sh
poetry sync --with science,rl,reporting
poetry run python -m pip install --no-deps pyarrow==21.0.0
poetry run python -m pytest -q tests/test_experimental_selection.py
poetry run python -m oligo_engine.experimental_rl prepare \
  --output artifacts/experimental-selection-manifest.json
poetry run python -m oligo_engine.experimental_rl v1 \
  --output artifacts/experimental-selection-v1
poetry run python -m oligo_engine.experimental_rl v2 \
  --v1-report artifacts/experimental-selection-v1/report.json \
  --output artifacts/experimental-selection-v2
poetry run python -m oligo_engine.experimental_rl plot \
  --output artifacts/experimental-selection-v1
poetry run python -m oligo_engine.experimental_rl plot \
  --output artifacts/experimental-selection-v2
poetry run python -m oligo_engine.experimental_rl linkage \
  --output artifacts/experimental-selection-linkage.json
```

`uv pip install --python "$(poetry env info --executable)" pyarrow==21.0.0`
is an alternative where the Poetry environment omits pip. Both versions use
the same `configs/experimental_rl/atlas_v1_v2.toml`, feature hash and source-only
Ridge prior. Runs refuse an existing output directory. V2 verifies the V1
gate, partition digest, and prior identity before starting. For comparable CPU
timing, set `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1`.

Each run saves the partition manifest, source prior receipt and numeric
parameters, policy checkpoint/manifest, `episodes.json`, and `report.json`.
An assay ledger records measured outcome, unit-cost purchase, chosen expert,
pre-action model statistics, fit-set hash, remaining budget, and reward.
The assay stratum is stored at the episode level. Output artifacts remain local
under the repository's ignored `artifacts/` directory.

## Scientific boundaries

- A replayable action is one previously recorded single-dose inhibition result
  at a fixed patent-table, target, cell line, transfection, species, dose and
  duration. Each campaign uses its own assay context.
- Only the oracle sees the unrevealed pool labels. Source training and
  calibration, policy training, checkpoint development, and final campaign
  evaluation are separate roles. Final sentinel outcomes enter metrics after
  every optimization decision. This boundary protects against accidental access
  by the implemented policies, rather than hostile Python introspection.
- Both versions optimize new measured hit discovery. V1 keeps the predictor
  fixed; V2 updates a Bayesian residual predictor on acquired labels.
  Sentinel learning is evaluated separately. The spec's separate optional
  learning-reward policy was not run.
- The V3 command is a metadata-only feasibility audit. A multi-assay
  simulator remains gated on curve validation, independent assay verification,
  bias and partition audit, and explicit sign-off.
