# Experimental selection codebase map

Base `df90bb6`, clean `main` after a fast-forward-only pull. Implementation is
isolated on `codex/experimental-selection-rl`. The working Python 3.11 runtime
uses the repository's pinned Gymnasium/SB3/PyTorch versions and PyArrow 21.

| Responsibility | Existing implementation | Integration |
| --- | --- | --- |
| Public records and splits | `src/oligo_engine/contracts.py` | Reuse stable observation IDs and the label-free/label-bearing boundary. Five experimental partitions need a campaign manifest. |
| Private assay replay | `src/oligo_engine/data/oracle.py` | Reuse `LabelOracle` for each episode. Build its eligibility from seed/pool IDs only. Keep sentinel labels with evaluation. |
| Atlas data | `data/aso_atlas_2/release`, `scripts/clean_aso_atlas.py`, and the checked-in audit | Verify release and fold hashes. Read only necessary assay metadata for cohort construction. |
| Atlas campaign grouping | `codex/atlas-lora-scaling:src/oligo_engine/atlas/{data,splits}.py` | Reuse assay matching and grouped sequence split design; allocate exclusive policy train/dev/test tasks. |
| Chemistry | `src/oligo_engine/reward/chemistry.py` | Reuse the verified Atlas HELM parser and normalized identity. |
| Classical and FM prediction | Atlas branch `atlas/baselines.py` and `models/aso_rnafm.py` | Source-only Ridge with positional chemistry/assay covariates. Historical local checkpoint membership is unavailable. |
| Acquisition | `acquisition/{random,pool_diversity,hybrid,uncertainty}.py` and Atlas branch `atlas/acquisition.py` | Reuse seeded random semantics and the max-min diversity rule; implement compact expert dispatch over array-indexed candidate pools. |
| RL runtime and policy saving | `rl/ppo.py`, `rl/__main__.py` | Reuse runtime checks and maskable algorithm. Implement a different episode, observation, reward, trainer and CLI. |
| Runner and artifacts | `evaluation/runner.py`, `evaluation/metrics.py`, `reporting/artifacts.py` | Reuse label isolation, deterministic pairing, ignored artifacts and runtime provenance conventions. |
| Representation cache | `representations/rnafm.py`, `native_cache.py`, Atlas branch `representations/aso_rnafm.py` | This version uses deterministic CPU classical features and frozen source preprocessing. |
| Checkpoint registry | `reward/bundle.py` verifies explicit artifact bytes; `rl/ppo.py` verifies scorer/policy compatibility | Experimental checkpoint metadata records partition, predictor and policy identities. |

The Atlas branch is at `f197d79` with a completed 240-fit scaling study.
LoRA did not beat classical Ridge on its three development targets. F7, STAT3
and NLRP3 are treated as prior development targets and stay outside the final
test. Neither machine-local FM weights nor reproducible fit memberships for a
usable model artifact are present in this checkout. This implementation trains
a new classical source-only prior against a verified manifest.
