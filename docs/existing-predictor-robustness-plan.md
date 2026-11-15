# Existing frozen predictors: corrective implementation and test plan

November 14, 2026. User authorization: define the implementation plan from the
[zero-coverage correction](updates/2026-11-14-2029-est-robustness-zero-coverage-correction.md)
and test the intended existing predictors. This authorizes the bounded diagnostic
replays below, not replacement fitting, new model selection or automatic gate changes.

## 1. Identify the actual artifacts before testing

Inventory ignored local artifacts with ignore rules disabled. Do not confuse an
absent Git-tracked model with an absent local checkpoint. Hash model/protocol/source
files before loading. Use trusted owner-local joblib artifacts only; a hash binds
identity but does not make arbitrary third-party pickle code safe.

Available:

| Model | Artifact | Identity / endpoint | Permitted test |
| --- | --- | --- | --- |
| Existing GP | `artifacts/rl_design/main_predictors_v1/gp.joblib` | SHA `cc02246146ad20a4a528226fd062fcb1e6ca2158c0e69eb14191e2025eaf4b11`; Huesken siRNA inhibition | Separate siRNA diagnostic; never ASO scoring |
| Existing RF | Same directory, `rf.joblib` | SHA `79891edebeb50bb74d4bee3e205ede0bcb9a63fcb8c7b4abc80ad65f6025f96c`; same Huesken training IDs | Comparable prediction/disagreement diagnostic |
| Existing Atlas pilot Ridge | `artifacts/aso_atlas/first_pilot_final/ridge.joblib` | SHA `36540d896a9f4b54a9aead80d492a64a10e3fafb4afeb5c1bf48d3dbfa28c609`; 20-mer MOE inhibition | Replay its own saved source/partitions; diagnostic-only artifact |
| Existing Atlas pilot HGB | Same directory, `hgb.joblib` | SHA `9e8c4ff1391ee846fb72f0e65bd69aebca3a47b77ac39e98a9037b08006623bd`; same Atlas training IDs | Comparable same-assay diagnostic, not independent biological evaluator |

Main was subsequently pulled to `47b7c1d`; the earlier missing-artifact finding is
superseded. All 287 files in `model_checkpoints/manifest.json` pass byte-count and
SHA-256 verification. The supported JSON efficacy bundle is present and is tested
as its own ASO suite. Atlas frozen/LoRA snapshots are also present, but their
published inventory explicitly requires pinned research code and the separately
downloaded RNA-FM backbone. Snapshot publication alone does not supply the backbone,
original source-cohort manifests, or an inference deployment API. No ASO GP is
identified in this published inventory; the available GP remains a siRNA model.

## 2. Correct the experiment in dependency order

1. **Trusted inventory and runtime.** Verify each checkpoint against its recorded
   hash and pin the associated protocol. GP/RF use pinned OligoGym revision
   `97f5b9f58d9e445a8ecb0218037af7465c3708c0` and sklearn 1.4.0. Atlas pilot artifacts
   identify sklearn 1.7.2; use a separate compatible Python 3.11 runtime with NumPy
   2.2.6, scipy 1.16.3, joblib 1.5.2 and PyArrow 22.0.0. Treat inconsistent sklearn
   serialization versions as errors. Do not mutate shared runtimes or the core lock.
2. **Outcome-free preflight.** Resolve exact fitting/validation/final IDs from the
   historical manifests. Check membership, source hashes, chemical/sequence overlap,
   endpoint/units, assay context and independent group counts. Predict admitted
   counts before fitting or reading evaluation outcomes. There is no fit phase in
   this runner. Zero usable development or final records stops before outcome access.
3. **Freeze the replay.** Persist protocol/artifact/source hashes, eligibility,
   prior exposure, thresholds, budgets and IDs before inference/evaluation. The
   historical partitions are retained; no seed search or outcome-based cohort choice.
4. **Frozen inference parity.** Compare wrapper means with direct estimator means on
   identical frozen features; check row-order/batch invariance. Preserve raw units,
   GP latent SD; RF spread is not a separate selected warning here. Verify checkpoint bytes remain unchanged.
5. **Diagnostics before outcomes.** Compute fitting-only nearest-feature distance,
   named uncertainty and same-endpoint disagreement. Save predictions and query
   traces with no endpoint outcomes. Count full precomputation cost separately.
6. **Development-only policy selection.** Select the fixed diagnostic threshold
   using development outcomes and minimum 50% retention. Preserve the original
   predictor. No test label reaches fitting, transformations, thresholds or selection.
7. **Seal ordinary/guarded ranking.** Use identical query permutations and budgets,
   k=5, seeds 0-4, and exact source-assay candidate IDs. Compare with ordinary
   predicted ranking. A pure uniform-shortlist comparator is a follow-up; random
   query proposals here still rank the queried pool by predicted efficacy.
   Compare partial panels at matched cardinality. Seal before final outcomes.
8. **Deferred evaluation/reporting.** Report raw-unit prediction errors, diagnostic
   risk-coverage versus random/oracle bounds, shortlist measured quality, rejection
   coverage and group counts. All results are internal retrospective replay;
   previously published final rows are not new external confirmation.

## 3. Frozen per-endpoint protocols

### Huesken GP/RF: separate siRNA replay

Retain the saved 1,944 fitting IDs and verify their source hash/lookup. Form the
remaining source holdout without training ID or exact HELM overlap. This is a
within-source sequence holdout, not unseen-target evaluation: fitting already
contains the target identifiers. Partition this historical holdout by deterministic
label-free target/compound components into development and final cohorts. Use seed
1729 and fixed shuffled components, with approximately one third of components for
development; no calibration partition or new interval guarantee is claimed.

Primary warning is existing GP latent SD; GP/RF raw disagreement is
reported separately. Fixed warning thresholds in percentage points:
`[0, 1, 2, 5, 10, 20, 30, 50, 100, 1000000]`. Domain distance is nearest Euclidean
distance in the model's actual frozen 210-column one-hot space, fitted references
only. Do not reuse the single-strand ASO distance contract for duplex siRNA.

### Atlas pilot Ridge/HGB: supported-context ASO replay

Use the existing `first_pilot_final/protocol.json` split: 3,800 training, 700
validation/development, 273 historical final records. Verify training-ID hash via
SHA-256 of the original newline-joined ID list, source parquet hash
`77b5334b21a4fb86f99821852e7e83a50488649f887cad52b3d7c29ff8941285`,
and identical 20-mer MOE/PS/5-methylcytosine tracks.

The metadata-only audit found all three roles share HepG2, human, electroporation,
4,500 nM, 24 hours. Training targets include DGAT2/ATXN2/SERPINA1/DMPK; development
includes CFB and ambiguous exon identifiers; historical final is FGFR4. Preserve
ambiguous target IDs as source metadata; do not relabel them as validated genes.
There are six original connected patent/compound components. Development/final each
occupy one component, so no multi-group generalization claim or confidence interval.

Ridge is the predeclared primary model. The warning is absolute Ridge/HGB
disagreement in percentage points, with fixed grid
`[0, 1, 2, 5, 10, 20, 40, 80, 1000000]`. No uncertainty is invented for Ridge/HGB.
Domain distance is minimum normalized Hamming distance across the 20 base positions;
chemistry is constant and checked separately. Matched full-assay context defines
admission. Any nonzero overlap or unsupported cohort receives a blocking receipt.
No row-level split of the one development patent component is called independent
group calibration. Interval calibration is `not_requested_insufficient_groups`.

## 4. Implementation files and tests

Add an inference-only existing-artifact runner and a small protocol config under
`configs/robustness/`, plus a CLI script and focused tests. Keep the earlier audit
runner and its zero-coverage outputs unchanged. Shared changes, if needed, belong
to the integrator; no workers are assigned by this plan.

Tests must verify hash failure before unpickling, checkpoint/model identity,
training/evaluation overlap rejection, zero-coverage preflight before outcomes,
supported-context admission, no refit calls, identical direct/wrapper predictions,
final-label poisoning invariance of policy/query IDs, immutable seals, and separate
siRNA/ASO scopes. Retain actual model runtime receipts and negative results.

The first output is an inventory/preflight receipt, then frozen predictions and
guardrail decisions, then sealed candidate lists, then evaluator-only outcomes.
Generated artifacts and weights stay ignored. No changes to clinical/safety claims,
dataset rights, source bytes, Gate 1, or the old exact-context policy are implied.

## 5. Published supported ASO bundle: distinct replay

Use `model_checkpoints/supported-aso-v1/efficacy.json`, SHA-256
`44f975ae47c1a073ec52bde1e3403baa21de8a1b0b733e4bcac1a9b236252a84`.
Its JSON loader is on current main. Verify all 2,000 training IDs and corresponding
sequences against the released cleaned Atlas source. Admit only the bundle's exact
20-mer chemistry and five-field assay. Exclude training patents, exact compounds,
Hamming distance <=2 and one-base shifts relative to training. Connect remaining
evaluation records by target, patent and exact compound before splitting. This
reconstructs a new **historical diagnostic cohort**, not the original prepared
cohort/split identified by the bundle's cohort hash. Do not claim reproduction of
the original supported-profile assessment or untouched confirmation.

The initial label-free component allocation produced six development rows and was
stopped by the minimum-ten preflight. Retain that failure receipt. Before reading
outcomes, amend the allocation rule to consume components in the same seed-1729
shuffled order until the minimum row count is met; no alternate seeds are tried.
The resulting allocation has 80 development rows in two components and 1,869 final
rows in two components. Both are limited-group diagnostics. Training target overlap
is allowed and named; this is not unseen-target evaluation. Near-analogue exclusion
is enforced relative to training, not claimed between development and final.

This is one Ridge checkpoint. Do not invent a second predictor, uncertainty or
independent evaluator. The selected diagnostic is normalized nearest-training
Hamming distance, fixed grid `[0,.05,.1,.15,.2,.25,.3,.4,.5,1]`; the other signals
remain undefined. Use the same matched-budget recorded-pool protocol above.

## 6. Remaining neural-predictor implementation

Use compatible loader code at `f197d79` for Atlas scaling and `9fd9f10` for the
earlier Atlas development checkpoints. Reconstruct the original source/target
manifests and exclusion audit from that pinned preparation code and byte-verified
release before exposing outcomes. Verify the external RNA-FM backbone against SHA
`5b5d7d87b37c291ef42c140ef9edf7aea29f255fa2a4fd435f776c52e93d5e99` in its
matching research runtime. The path recorded in the published research runner,
`/private/tmp/oligoal-rnafm-20261114/artifacts/rnafm-checkpoint/RNA-FM_pretrained.pth`,
is absent in this workspace. Do not load custom Torch/pickle snapshots using
invented classes or a mismatched runtime.

Freeze a named checkpoint pair and diagnostic protocol before outcomes; do not
select the best of 287 snapshots using replay results. Verify saved normalization,
context vocabulary, training/adaptation IDs and direct/batched inference parity.
Then run preflight, frozen prediction, development-only thresholds, sealed searches
and deferred measurement evaluation. Neural inference, controlled perturbations,
assay-transfer studies, calibration and prospective guardrail confirmation remain
separate unfinished phases. No end-to-end RL claim is made; main retired the prior
RL scaffold at `07df61d`.

## 7. Original DGAT2 follow-up executed

The subsequent user request authorized resolving compatibility for the original
2,536 DGAT2 records. [The completed metadata recovery and transfer diagnostic](updates/2026-11-14-dgat2-original-cohort-transfer.md)
supersedes the earlier assumption that original assay metadata and classical
source membership could not be recovered locally. A pinned original-source
crosswalk recovers assay fields for every record. Reconstruction matches all twelve
published Atlas classical fitting-ID lists; exclusion of fitting/validation-exposed
sequences leaves a common 2,500-record stress cohort. All twelve frozen models
were evaluated without fitting. DGAT2 is seen by these models, so this is not an
unseen-target study. Chemistry annotation conflicts remain explicit, and LoRA
inference and prospective robustness confirmation remain unfinished.
