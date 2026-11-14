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
