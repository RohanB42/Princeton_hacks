# Executable contracts

Canonical Python types: `src/oligo_engine/contracts.py`. Schema version: `0.2`.
The integration/evaluation owner coordinates all shared contract/config changes.

| Contract | Ownership and fields | Label boundary |
| --- | --- | --- |
| Observation | data: immutable sample_id, HELM/sequence, target_id, modality, chemistry, assay, optional numeric fixture features and original assay context | no labels |
| Dataset | data: observations, source identity/revision/content hash, endpoint, provenance kind, source/subset metadata | no labels; map by stable ID |
| SplitManifest | evaluation: strategy, seed, train/test IDs, construction parameters | complete partition, no overlap |
| LabelOracle | evaluation: reveal(unique eligible IDs), acquisition log | owns training labels; denies test IDs |
| Predictor | models: fit(observations, revealed labels), predict(observations), config | receives acquired labels only; Prediction has mean and optional uncertainty/type |
| AcquisitionPolicy | acquisition: choose(eligible records, labeled records, budget, RNG, predictor), config | receives neither oracle nor metrics nor candidate labels |
| RunArtifact | evaluation: schema/status, data identity, complete split, config/seed, initial IDs, batches, label counts, metrics, full-pool reference, runtime, environment/code identity, caveats | no serialized row labels or model internals |

The runner validates unique eligible selection independently of policy code. A
fresh predictor is constructed per checkpoint and for the reference. Policies may
request candidate predictions but receive only label-free records and fitted models.
The runner controls label reveal, score evaluation and budget stopping. Optional
uncertainty must have a named type; it must not be advertised as calibrated unless
separate calibration checks support that statement.

## Fixtures and consumers

`data/fixture.py` generates deterministic toy observations/labels in memory with
explicit synthetic provenance. `models/fixture.py` is a simple nearest-neighbor
fixture predictor, not a scientific baseline. `configs/fixture.toml` fixes budgets
and seeds. `python -m oligo_engine --config configs/fixture.toml --output artifacts/fixture`
writes `run-seed-N.json`, `metrics.csv` and `summary.json`. UI work can consume these
artifacts only with a visible synthetic-data badge. The November 14 user-authorized
measured diagnostic runner uses schema 0.2 with explicit measured provenance and
`purpose="diagnostic"`; research mode is still gated. It never replaces fixture
provenance silently. See dataset-pipelines.md for the catalog and CLI.

LoadedDataset retains labels privately and provides separate campaign, evaluation
and full-reference capabilities only after validating a complete split manifest.
Source observations retain row-qualified IDs and extra assay context. Diagnostics
allow an unset Pearson threshold, record effective pool-adapted budgets, and mark
completion as `complete_measured_diagnostic`. Summary outputs remain per dataset
and policy; contributing seed counts reflect exact budgets without interpolation.

Artifacts contain no predictions promoted to measurements. The full-pool reference
budget is a separate field, not added to campaign expenditure. Runtime is measured
wall time and therefore not bitwise reproducible. Scientific outputs need committed
code revision plus a clean/dirty indicator; development artifacts may truthfully be
dirty. Generated artifacts are ignored by Git.
