# Compatible measured data: executed exposure and cohort experiment

November 15, 2026. This user-requested follow-up goes beyond the previous
applicability audit by recovering additional experiment memberships, checking
cross-source ASO identities and closing near-sequence components. It does not
change the active predictors, chemistry, assay context, risk threshold or policy.

**The completed preflight did not find a defensible larger fitting cohort with
an independent same-context assessment under the preserved data roles.** Among
parsable rows matching any current chemistry pattern, only 298 rows survive the
expanded exclusions. They are all MECP2 from one connected patent component at
HepG2/electroporation/4,000 nM/24 h, which differs from the active 4,500 nM context.
No measured learning curve was launched. Predictor improvement is therefore
**not estimated**, rather than estimated to be zero.

## What ran

Implementation: `scripts/molecular_compatible_data_experiment.py`.
The authoritative outputs are under:

`artifacts/molecular-compatible-data-experiment-v1/corrected-role-recovery/`

The audit completed in **15.45 seconds** and recovered **244 provenance documents
with 888 explicit membership fields**. It read metadata from both full Atlas
inhibition/neurotoxicity releases and seven released OligoGym ASO datasets.
All underlying raw files were hash-verified and left unchanged. There was no
network data download, predictor query, model fitting or active-model replacement.

Positive column projections exclude `Inhibition_pct`, `FOB_score`, `y` and `y_raw`.
The Atlas tables contribute HELM, target, patent and context metadata; OligoGym
contributes only HELM, supplied FASTA and target metadata. Existing JSON training
receipts and reports were deserialized to recover membership IDs; these documents
also contain **historical aggregate performance statistics and training losses**.
They were not treated as new measured observations or used to choose a favorable
cohort. An explicit inventory found no row-level endpoint-like fields in those
244 documents. Thus “no outcomes read” in the result means no newly loaded
row-level endpoint observations, not that no historical aggregate statistic was
present in a parsed provenance file.

## Newly recovered exposure

The prior audit recorded 30,126 protected source-qualified row IDs. This run
recovered 427 additional protected IDs, giving **30,553**. Every recovered
membership ID maps to parsed Atlas metadata; unresolved/unmapped counts are zero.
This mapping success does not certify that the cross-project exposure history is
complete.

Sources include all 240 scaling-study receipts, four earlier RNA-FM/classical/
acquisition provenance documents, and the newly published experimental-selection
partition manifest from the read-only `origin/main` revision pinned in the protocol.
That manifest records **12,000 source-fitting and 2,500 calibration rows** plus
training, development and final campaign memberships. It was read using `git show`;
the working tree was not merged or reset. Its published partition identity is
`aaf7882fa42472f073a5fbed4e5a5a854c44c54b99a084f0a72d2f2755289146`.

Selection, development, assessment, calibration, sentinel and final memberships
stay protected. The seven historical reserved targets remain quarantined even
though another workstream has since evaluated some of them. The **304 risk-final
rows remain preserved**, with no final endpoint access. Experimental-selection
V1/V2 used earlier manifests not fully recovered here; their reserved-target
exposure is known, but full global independence is not claimed from the published
later manifest alone.

Exact-sequence/patent closure protects 138,681 Atlas rows under the old ledger
and 138,683 under the expanded ledger. The small change after closure is expected:
many newly recovered IDs already belong to protected components. Adding
conservative OligoGym cross-source quarantine raises this to 148,919. Adding
near-sequence links raises it to **154,781 of 178,103 parsable Atlas rows**.
There are 1,211 inhibition and 45 neurotoxicity parser rejections. Those rows remain
unknown and unusable in this experiment; they are not evidence that measurements
or useful chemistry do not exist.

## Why apparent extra rows do not yield an independent experiment

The table shows row counts for selected complete contexts. The full machine-readable
result includes all 41 active-pattern/context combinations, including incomplete
contexts that cannot define an assay. Counts are records, not independent targets.

| Pattern and efficacy context | Raw rows | Prior exact exclusions | Recovered exact exclusions | Cross-source exact exclusions | Plus near-family exclusions |
|---|---:|---:|---:|---:|---:|
| 20-0, A431/gymnosis/3,000 nM/48 h | 2,475 | 2,012 | 2,012 | 2,012 | **0** |
| 20-0, A431/gymnosis/4,000 nM/48 h | 8,295 | 1,689 | 1,687 | 1,687 | **0** |
| 20-1, HepG2/electroporation/4,000 nM/24 h | 618 | 298 | 298 | 298 | **298** |
| 20-1, ReproNeuro Neurons/gymnosis/8,000 nM/120 h | 309 | 309 | 309 | 0 | **0** |
| 20-1, iCell GABANeurons/gymnosis/7,000 nM/144 h | 1,274 | 1,274 | 1,274 | 0 | **0** |
| 20-1, iCell GABANeurons/gymnosis/8,000 nM/144 h | 806 | 806 | 806 | 0 | **0** |

Every exclusion column gives the **remaining** rows after that cumulative rule.
The A431 pools initially appeared promising; transitive local sequence-family
links eliminate their claimed independence. The neuronal UBE3A-ATS pools overlap
previously available OligoGym ASO sequence metadata and are conservatively
quarantined. The remaining **298 MECP2 rows all belong to patent
US20200078389A1 and one connected component**. Splitting that component into fitting
and assessment would defeat the declared independence rule. They also cover only
one of three active patterns and a different dose.

The active HepG2/electroporation/4,500 nM/24 h context still has **zero verified
exact current-pattern matches among parsable records**. There is no basis here to
interpolate across doses or rename 4,000 nM measurements as 4,500 nM evidence.

## What the graph checks establish and what they do not

The metadata graph links rows through exact natural sequence and patent identifier.
It then joins equal-length sequences with Hamming distance at most two or an exact
one-base shift, using all parsed metadata rows as possible intermediate bridges.
Thus two selected rows can share a component through an unselected third row.
Near links are streamed by length and position pair rather than materializing a
quadratic distance matrix. Numeric context formatting is normalized, but biological
aliases, species equivalence and patent-family equivalence are not invented.

This is a conservative study-design rule, not proof that every sequence in a
component has the same biological activity. Unresolved patent families and more
remote homology could add links. The audit does not split a large component merely
to create favorable sample counts.

The OligoGym quarantine covers all **41,929 ASO metadata rows**, not just a verified
list of acquired labels. Prior broad project studies made these datasets available
for fitting and assessment; complete per-row exposure recovery was not available
for every historical run. Consequently this is an explicitly conservative
quarantine, **not a claim that every counterpart's label was inspected**. If a
later complete exposure audit proves some counterpart rows were never used, a
separately versioned feasibility analysis could revisit those exclusions without
claiming this run established eligibility.

The strict chemistry parser rejects LNA and other unsupported representations;
where a valid supplied natural-base FASTA exists, it can still provide a
conservative sequence-overlap exclusion. That never supplies chemical compatibility
or an efficacy/risk label. ASO and siRNA endpoints were not pooled.

A new representation discrepancy also needs resolution: for **all 2,437 OligoGym
MOE_Neurotox rows**, supplied FASTA differs from the sequence parsed from HELM.
A metadata-only follow-up found that FASTA is the parsed sequence followed by one
additional base (C:764, T:711, A:621, G:341). This is an unresolved representation
or conversion convention; it is not a claim that 2,437 underlying molecules are
wrong. The audit conservatively uses both strings for quarantine, preserves the
raw bytes, and does not assert that conflicting strings define one canonical
molecule or silently repair the measurements.

## Could we at least run a nested curve on existing fitting rows?

The requested fallback was examined: subsample the existing supported-profile
2,000 fitting rows and retain its fixed 1,924 previously inspected assessment rows.
That profile is an efficacy-only, fully PS 20-mer study, separate from the current
mixed-linkage molecular grammar.

| Existing role | Rows | Explicit protected-role overlaps | Published calibration overlaps | Published fitting overlaps |
|---|---:|---:|---:|---:|
| Supported-profile fitting | 2,000 | **126** | 51 | 74 |
| Supported-profile assessment | 1,924 | 1,924 | **253** | 0 |

The 126 are a union of overlapping roles, not a count to add to the 51. All 2,000
fitting rows belong to protected exact-sequence/patent components under the expanded
ledger. The assessment rows correctly remain assessment data; being protected is
not itself a problem for evaluating them. The problem is that the proposed fitting
side cannot be certified under the current cross-study exclusion rule. Reusing the
original entire fitting set would also put 126 explicitly protected rows into a
new fit. Removing only those 126 would still leave component-level concerns.

A within-study historical replay can be conceptually different from a new
independent data-expansion experiment, but it requires an explicit exposure-aware
contract and a narrower claim. This audit did not quietly relabel the existing
assessment as fresh confirmation, weaken component exclusions, or fit a curve
that would answer a different question. **No new model performance result exists.**

## Decision and next concrete experiment

For the current exact three-pattern/assay profile, the data-expansion fitting gate
fails before outcome access. For the closest candidate context, 298 rows in one
component cannot support independently grouped fitting and assessment. The
supported-profile fallback also fails the preserved cross-study role gate.
There is therefore no valid 2k/4k/8k compatible-data curve to launch from this audit.

The next successful experiment needs one of the following, declared before fitting:

1. New compatible measurements from additional independent components at the
   intended chemistry/assay context, with fixed fitting, development and final roles.
2. A separately approved transfer/development estimand and a complete exposure
   manifest that admits enough groups without moving protected labels into fitting.
   It must retain endpoint/context distinctions and cannot promote itself as a
   validated replacement of the current profile.
3. A deliberately historical within-study sensitivity analysis with its own
   restrictions and acknowledged cross-study exposure. Its result would concern
   that fixed historical data allocation, not newly independent biological support.

If a suitable cohort becomes available, the small classical experiment remains
straightforward: prespecified nested fitting subsets, fixed Ridge configuration
or training-only tuning, identical fixed assessment rows, and both prediction
error and within-campaign ranking. Sample sizes must come from the audited cohort;
more records, more independent groups and better assay coverage are different
experimental factors. Final outcomes cannot determine which factor or model wins.

## Reproduction and correction record

```sh
PYTHONPATH=src /private/tmp/oligoal-atlas-rnafm-20261114/.venv-atlas/bin/python \
  scripts/molecular_compatible_data_experiment.py \
  --output artifacts/molecular-compatible-data-experiment-v1/corrected-role-recovery
```

Use a new output directory to rerun; existing outputs refuse overwrite. The pinned
historical worktree receipts and fetched published Git object are required. The
protocol records source hashes, all receipt hashes, exact Git revision/blob hash,
metadata projections, quarantine rules and script hash before the full audit.

An initial metadata run is retained in the parent artifact directory and marked
superseded. Its membership keys inadvertently included file paths: a directory
named `development` could cause a fitting role to be over-protected. This was
caught before any fitting, corrected by separating semantic roles from path
provenance, and covered by an added invariant test. `superseded.json` seals the
reason and corrected script hash. **Only the corrected child-directory counts
above are authoritative.** No outcomes, model parameters or scientific threshold
were altered to obtain the corrected counts.

Corrected protocol seal:
`3651983d4d380f41824a0a1a607315a0cce74bf46d2dab843a5d3c3adf322b32`.
Corrected result seal:
`b177ae92b39d1370a86f21114bd4948d9c71460dfc23a2edb1ad0107f02d84b5`.

Twelve new invariant tests pass. They cover positive metadata projections,
protected-role classification, transitive near-family exclusions, one-base shifts,
length separation, numeric-metric isolation and path/role separation. Ruff lint,
formatting and whitespace checks pass for the new code. The integrator reports
full-repository checks separately. No generated artifacts, raw data or weights
were committed.
