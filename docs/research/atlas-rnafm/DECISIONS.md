# Research decision log

## 2026-11-14 — authorization and initial scope

The user authorized a subagent to proceed with the research plan and next steps.
A0/A1 precede expensive modeling. This branch is isolated from main and receives
ownership of new Atlas files, ASO-specific representation/model modules and tests.
No paid compute, public deployment or merge into main is included.

## Frozen invariants

Historical source labels and new-target labels are reported separately. All compared
transfer models receive the same source data. Evaluation target/patent/compound
exclusions apply before source adaptation. All validation labels are budgeted.
Endpoint/chemistry incompatibilities, undefined metrics and negative results remain
visible. No test-driven tuning or surrogate scores presented as measured efficacy.

## Pending decisions before runs

Parser/normalization revision; supported chemistry; assay completeness rules;
compound grouping and campaign split rules; development/final target assignment;
feasible budgets; source label allocations; model search spaces; compute caps;
primary contrast and threshold/censoring analysis. Resolve from source inspection,
label-blind feasibility and training-internal development, then timestamp before
relevant outcomes. Record deviations explicitly instead of overwriting history.

## A0/A1 implementation freeze — before development outcomes

Pinned Atlas source retrieved at bb90c946013f183379da04678340e193088e5f99.
Its native efficacy adapter takes max inhibition across contexts; reproduce only
as an isolated anchor, not as our campaign endpoint. The published native benchmark
JSON is absent from this checkout: no numerical reproduction claim can be made
without that reference. Local classical diagnostics remain permitted.

Strict parser consumes every token, supports explicit monomer maps and preserves
modified bases/linkages/terminal tokens. Primary cohort requires complete campaign
metadata, positive dose, supported DNA/MOE/cEt chemistry with DNA, and selects the
first source row for repeated exact compound/campaign, never the maximum label.
Human campaigns >=400 distinct compounds are allocated by target hash seed20261114;
three development targets F7/STAT3/NLRP3, seven reserved. Target aliases are NOT
externally resolved: report target identifiers, not proven target-gene isolation.
The same-length Hamming<=2 / exact one-base-shift connected groups define campaign
holdouts. Exclude all allocated targets/patents/exact bases/compounds from source.

Development-v1 config freezes source50/200/1000 x seeds510–512; target50/100/200 x
seeds610–612; only three development targets scored. Source models at1000/seed510
are shared transfer priors; historical labels are disclosed. Ridge/XGB select among
three configs with acquired-only grouped CV. Neural head/LoRA use matched fixed
three epochs, lr0.001, rank4/alpha8, batch8, CPU1thread; this is a bounded diagnostic,
not a tuned final comparison. Full matrix wall cap7200s; preserve incomplete work.

## Fixed-geometry follow-up frozen before acquisition outcomes

`acquisition-development-v1.json` isolates acquisition geometry with one fixed
source-Ridge+acquired-residual-Ridge predictor. Source1000 labels are identical for
all arms. Source-trained fusion features from frozen and LoRA encoders are compared
with classical features projected to64 dimensions by fixed random seed920; scaling
uses only source rows, then L2 normalization. Geometry never sees evaluation rows.
Policies: random, classical diversity/uncertainty/MaxDet, frozen-fusion MaxDet and
LoRA-fusion MaxDet. Initial50/batch25/max200, seeds710–712, same three development
campaigns. No target encoder retraining in this cheaper geometry-only ablation.
Reference uses independent full-pool residual fitting; threshold1.10x referenceRMSE
is reporting only. This exploratory stage tests whether representation choice helps
selection even if it fails to improve prediction. It is not independent confirmation.

## 2026-11-14 — post-result development decision

All planned bounded fits and the fixed-geometry follow-up completed. Frozen and
LoRA chemistry models lose to source Ridge + offset on every target's normalized
RMSE-AULC; LoRA geometry also loses to classical MaxDet on the primary macro
contrast. Do not scale this recipe into confirmation or target-adapted acquisition.
This is a scientific no-go for the tested recipe, not an execution failure or a
rejection of the broader pretraining hypothesis. Seven reserved targets stay sealed.

Every acquisition arm meets the frozen 1.10x reference RMSE threshold at initial
50 labels. Preserve this uninformative threshold result; do not choose a tighter
threshold after seeing curves. Label savings have not been demonstrated.

Optional dependency tests use the repository's existing `test_rnafm*` collection
convention so plain core pytest remains usable without pandas/XGBoost/PyTorch.
No shared conftest, dependency lockfile or core runner was changed.
