# OligoAL scientific specification

Status: implementation handoff accepted 2026-11-13. This document supersedes the
multi-task and commercial claims in the supplied November 11 v5 plan.

## Task and scope

Evaluate retrospective sequential acquisition of **measured siRNA efficacy** on
Roche/OligoGym. Ask whether uncertainty/diversity policies improve prediction at
matched label budgets compared with random acquisition. A null or negative result
is a valid deliverable. Hit discovery is a separate objective and analysis.

The intended first dataset is Huesken / Ichihara_2007_1: the pinned package registry
lists 2,431 rows and 30 targets. Its downloader key is **Huesken**, not `siRNA1`.
The benchmark CSV uses `siRNA1`; the pinned Analysis.ipynb explicitly maps that
historical alias to Huesken. Input is source HELM
and available target/assay/chemistry metadata. Output is an endpoint estimate with
optional explicitly named uncertainty, acquisition IDs, and auditable run artifacts.
The assay metadata describes percentage inhibition relative to control in an
eCFP-eYFP dual reporter assay. Preserve upstream values; verify scaling and direction
from data/source before adding potency-based acquisition.

## Permitted information

- Immutable source-qualified observation IDs and label-free sequence/context records.
- Training labels revealed through the pool oracle, counted from the initial batch.
- Test labels exclusively inside the evaluation owner; no feedback to policies,
  fitting, feature fitting, model selection, tuning, rewards, or stopping.
- Sequence-only split construction on the full sequence collection is an explicit
  exception for reproducing upstream splitting. It never authorizes model feature
  fitting on evaluation rows. See EVALUATION.md.

Independent ASO activity or safety replay requires its own assay and modality
contract. Preserve missing labels. Do not pool siRNA efficacy and ASO safety labels
or emit a combined safe/effective flag. Design, biological scoring, transcript
retrieval, accessibility and RL are independent future tasks.

## Current implementation boundary (updated 2026-11-14)

The first executable slice is a **synthetic, random-acquisition contract fixture**:
controlled pool oracle, fixed split, retraining, deferred test scoring, full-pool
reference, JSON/CSV output and five-seed summaries. Its small fixture predictor is
only for exercising interfaces. It is not an OligoGym baseline or a finding.

Source inspection and a reproducible upstream audit precede any measured-data
adapter. Gate 1 remains open until the baseline rerun discrepancy and historical
split/environment identity are reconciled.

The user's November 14 instruction explicitly authorizes including all 12 released
datasets and generalizing pipelines across them. The source-pinned catalog and
measured diagnostic runner now work independently on each dataset. Explicit
`purpose="diagnostic"` permits engineering replay with the gate open; measured
research mode still fails closed. Local exact-sequence and target-group holdouts,
hash/RF representation, uncalibrated tree spread and capped smoke runs are not
official baseline reproduction or evidence of cross-dataset scientific generalization.
See dataset-pipelines.md. No data are pooled across modalities or endpoint scales.

## Non-claims

No wet-lab validation, therapeutic efficacy, clinical safety, calibrated uncertainty,
cross-modality transfer, proprietary-engine equivalence, active-learning benefit or
exclusive novelty is established. The supplied correspondence is user-provided
context; it is not independent verification of results or novelty. Different ASO
chemistries remain relevant; PS/2'-MOE does not make LNA universally irrelevant.

Existing distribution/import names stay `oligo-design-engine` / `oligo_engine`.
OligoAL is the project name; do not perform a broad package rename during integration.
