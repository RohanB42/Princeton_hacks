# Molecular generalization: exposure audit and confirmation protocol

November 15, 2026. Executed metadata audit; proposed confirmation design. No new
training, predictor queries, measured-outcome reads or final-group assignments
were performed by this workstream. The separate additional APOC3/ANGPTL3 policy
evaluation is explicitly development work. This document follows the
[final specification](FINAL_MOLECULAR_DESIGN_RL_SPEC.md) and
[scaling plan](molecular-data-scaling-plan.md).

**There are currently zero certified independent final groups for the active
joint chemistry/context profile.** More targets can support computational
development, but the available inventory does not justify announcing twenty
independent biological confirmation groups or treating 134 target names as genes.

## What was executed

`scripts/molecular_generalization_audit.py` writes a protocol with input hashes
before projecting approved metadata columns from the cleaned inhibition release
and the historical Atlas strict cohort. It reads existing membership receipts
for the active efficacy and risk models and the v3 policy configuration. No
`Inhibition_pct`, `FOB_score`, other endpoint values, or fresh predictions are
requested. Existing `analysis_eligible` flags convey previously computed outcome
availability; this limited metadata dependency is disclosed in the protocol.
Hashing source bytes does not decode their outcome columns.

The audit stores a candidate/exposure manifest with `final_assignment: null`, a
summary, transcript identities and planning scenarios in the ignored directory
`artifacts/molecular-generalization-audit-v1/`. It retains historical reserved
roles even where another study also reserved rows from that target. It does not
certify completeness of the cross-project exposure history merely because a
target has zero active-model fitting rows.

Reproduction using the existing owner environment:

```sh
/private/tmp/oligoal-atlas-rnafm-20261114/.venv-atlas/bin/python \
  scripts/molecular_generalization_audit.py \
  --preparation /private/tmp/oligoal-atlas-lora-scaling-20261114/artifacts/atlas-rnafm/preparation-v1 \
  --output artifacts/molecular-generalization-audit-v1
```

The historical preparation artifact is required; missing artifacts are not
replaced with guessed memberships. Six unit tests pass, covering column rejection,
reserved/selection exposure, and the distinct target/seed uncertainty terms.
Ruff lint and formatting checks pass for the new script and tests.

## Counts and exposure findings

| Metadata inventory | Count | Meaning |
|---|---:|---|
| Broad analysis-eligible inhibition rows | 143,646 | Existing eligibility, not active-profile compatibility |
| Raw nonmissing target spellings | 134 | Not verified genes |
| Nonempty strip/uppercase identifiers | 131 | Plus one missing-name bucket; aliases/species unresolved |
| Patent identifiers | 203 | Patent families unresolved |
| Campaigns with at least 100 distinct exact HELMs | 98 | Fixed patent/table/target/assay tuples |
| Identifiers represented by those campaigns | 28 | Not 28 independent human gene families |
| Nonreserved, noninspected identifiers among those 28 | 14 | No independence certification |
| Of those, no active efficacy fit/selection rows | 7 | Does not establish absence from every head |
| Of those seven, represented in the prior strict cohort | 1 | NOX4, 288 strict rows |
| Certified independent final groups | 0 | Exact applicability and independence remain open |

Uppercasing merges APOC3/Apoc3, NR3C1/Nr3c1 and SOD1/Sod1. These are spelling
normalizations only: case can encode species conventions, so they are not certified
human-gene aliases. The manifest has 135 entries including the missing-name bucket
and policy genes absent from the broad release. Its categories are 18 exposed or
designated development entries, seven historically reserved entries, 50 remaining
entries with active efficacy exposure, and 60 still unassigned entries without it.
The latter includes ambiguous names; it is not a count of usable final genes.

The 14 large-campaign identifiers are AGT, APOB, ATXN3, C9ORF72, CD40, COASY,
CRP, F11, HBV, IL4R, NOX4, NR3C1, PTPRU and RAF1. HBV alone illustrates why these
must not be presented as a set of human genes. Seven lack active efficacy fit and
selection exposure: APOB, CD40, CRP, IL4R, NOX4, PTPRU and RAF1. All except NOX4
have zero rows in the historical strict DNA/MOE/cEt cohort. This absence is a
qualification deficit, not proof of unusable chemistry or proof of independence.
No candidate was filtered by model utility, risk-screen success or measured effect.

The historical source manifest contains 95,638 allowable training-pool rows and
14,614 source-validation-pool rows. These are pools, not claims that every row was
used for fitting. The active efficacy export identifies 2,284 actual fitting and
585 selection rows, all successfully joined to strict-cohort metadata. The audit
also counts exact natural-sequence and patent-ID links to active fitting rows;
these checks do not replace a transitive near-sequence/patent-family graph.

### All twelve v3 policy genes

| Gene | v3 policy role | Active efficacy fit / selection rows |
|---|---|---:|
| DGAT2 | Training | 17 / 29 |
| SOD1 | Training | 1 / 59 |
| B2M | Training | 0 / 0 |
| HPRT1 | Training | 0 / 0 |
| PCSK9 | Training | 23 / 0 |
| VEGFA | Training | 0 / 0 |
| CFB | Validation | 50 / 0 |
| F7 | Validation; historical target adaptation/assessment | 0 / 0 |
| FGFR4 | Development evaluation | 15 / 0 |
| F9 | Development evaluation | 0 / 0 |
| F12 | Development evaluation | 185 / 0 |
| TTR | Development evaluation | 0 / 9 |

Every row is development exposure for future experiments. A zero in this table
does not make a target pristine: F7, for example, had measured target adaptation
in the historical RNA-FM study. Selection labels also count as supervised exposure.

Historical Atlas development additionally inspected STAT3 and NLRP3. The separate
supported-profile predictor used ATXN2, CFB, DGAT2 and FGFR4 for fitting and
inspected measured assessment rows for ATXN2, DGAT2 and SERPINA1. All enter the
ledger. APOC3 and ANGPTL3 are newly designated computational development targets
for the requested eight-target table. ANGPTL3 has 45 active efficacy fitting and
three selection rows; APOC3 has neither, but only one historical strict-cohort row.
Neither can subsequently be advertised as fresh confirmation.

Historical reserved campaigns are PTBP1, KCNQ2, DMPK, PLN, SMAD7, PSD3 and DUX4.
The old manifest excludes their names, associated patent IDs and exact molecular
equivalents from its source pools. This is historical evidence, not a new claim
that every downstream study left them untouched. DMPK also occurs in the current
risk model's **sealed final partition**, with 77 metadata rows. ATXN3 has eight
risk fitting rows and 160 sealed final rows. No final outcomes were read. Keep
these reservations intact; overlap is recorded rather than silently reassigned.

Public transcript caches are inventoried by gene, transcript accession, sequence
hash and length. Cached sequence access is not supervised label exposure. No
new transcripts were fetched by this audit. The separate evaluator may add its
two newly designated development caches; rerunning the inventory records them.
No binding coordinates or transcript mapping are supplied by the Atlas table,
so its measured rows cannot automatically be attached to generated windows.

## The experiments must answer separate questions

1. **Computational generalization:** with fixed predictors, chemistry, screens and
   utility normalization, does a frozen search policy improve equal-target mean
   archive quality on previously unqueried policy target groups? Predictor-seen
   targets may be allowed in a separately declared stratum. This supports a claim
   about search under a frozen proxy, not measured efficacy or safety.
2. **Predictor-unseen transfer:** exclude a final group and all connected molecular,
   patent and target identities from every supervised reward head, adaptation,
   calibration and selection procedure. Retraining a clean predictor may be
   necessary. Absence from PPO training is insufficient.
3. **Measured discovery quality:** independently assess selected recorded
   compound-assay observations after selections are sealed. Generated molecules
   without measurements remain hypotheses. An independent model is corroboration,
   not a substitute for compatible observations; efficacy and acute mouse
   tolerability remain separate endpoints.

The full-release applicability audit already found zero verified exact matches
to the current efficacy chemistry/context among parsable rows. Thus the third
experiment cannot be executed honestly on the current profile merely by adding
genes. A qualified supported profile or a separately defined transfer setting
must be established first. Do not silently relax chemistry, species, dose or route.

## Proposed fixed split procedure

Before any new training expansion, freeze a species-qualified alias map with
evidence, patent-family mapping with unresolved identifiers explicitly marked,
and full compound/natural-sequence identity provenance. Include unselected rows
when building links so duplicates cannot hide transitive leakage. Build connected
components from exact chemistry, natural sequence, the declared close-sequence
rule, verified target identity and verified patent-family identity. Record the
component-size distribution; a giant component is a real feasibility constraint.
The old Hamming <=2 / one-base-shift rule is a starting sensitivity analysis, not
proof that all sequence homology is isolated. Exact and near links must also be
audited across endpoints and OligoGym where relevant.

For policy-only confirmation, group homologous targets and shared generated
candidate families before allocating roles. Fixed transcript accessions and
20%/50%/80% 48-nt regions can define three prespecified regions per group; deduplicate
overlapping candidate identities, and average regions within their group. Fix
candidate capacity and all exclusions from metadata before scoring. Do not
replace a target because its risk screen later rejects every design.

Keep the existing inspected panel for development and the seven historical
reserved campaigns quarantined under their existing contracts. Do not repurpose
either as novel training breadth or new final confirmation without an explicit
versioned exposure decision. All remaining audit candidates currently stay
unassigned. After certification, sort eligible component IDs by
SHA256(`molecular-confirmation-v1|component_id`) and allocate the prespecified
final-group count first, then a fixed validation allocation, then training.
Freeze the entire manifest before model queries. If there are too few eligible
components, report the deficit and a narrower estimand; do not fill from previously
inspected targets or change the count after viewing results.

For a 20-group confirmation scenario, the broad seven-name shortlist is at least
13 identifiers short even before certification; its one strict-cohort candidate
is at least 19 short. Neither bound counts the seven existing reserved groups as
newly available. For computational policy-only experiments, transcript metadata
can support additional candidates beyond measured Atlas coverage, but that is a
different eligibility definition and still requires family/exposure checks. A
24-training-gene breadth study and 20-final-group study must budget their disjoint
groups together, rather than consuming future confirmation targets during tuning.

## Estimands, dependence and precision

Choose the strongest conventional comparator on development data, then freeze
one primary pipeline contrast at eight requests. Random and greedy remain reported
even if a different baseline wins development selection. PPO's increment over the
strongest pretrained-only, resource-accounted control is a separate primary
attribution study or a second contrast in a prespecified Holm-controlled family.
The 32-request result and archive-quality AUC are secondary; do not choose the
best budget after final inspection. Count logical queries, physical head calls,
pretraining, PPO and selection costs separately.

Let `d[g,s]` be the paired archive-quality difference after averaging regions
within independent target/family group `g`, for trained-policy seed `s`. Estimate
`mean_g mean_s d[g,s]`, giving groups equal weight. The same trained policy is
evaluated across groups, so seeds and targets are crossed. In a two-way bootstrap,
resample target-group indices and seed indices independently, then use their
Cartesian product, preserving the same sampled seed identities across all groups
and the paired methods. Do not independently resample different policy seeds for
each target. Report seed variability and target-level differences separately.
Crossed-factor resampling is motivated by
[Owen and Eckles](https://arxiv.org/abs/1106.2125); few-run RL interval reporting is
discussed by [Agarwal et al.](https://arxiv.org/abs/2108.13264). Neither paper
guarantees adequate coverage for this small, zero-inflated molecular setting.

Use a proposed meaningful **computational** improvement of 0.03 utility units;
this is not a biological effect threshold. Prespecify it before confirmation.
The executed planning calculation assumes a balanced paired random-effects model
with target SD `sigma_g`, seed SD `sigma_s` and interaction SD `sigma_e`:

`SE² = sigma_g²/G + sigma_s²/S + sigma_e²/(G*S)`.

The following are assumption-based normal approximations, not measured power or
confidence intervals from the current study. Fixing seed SD 0.02, interaction SD
0.05 and ten seeds gives:

| Target SD | Groups | Approx. 95% half-width | Approx. 80% detectable effect versus zero |
|---:|---:|---:|---:|
| 0.05 | 5 | 0.0476 | 0.0681 |
| 0.05 | 20 | 0.0261 | 0.0373 |
| 0.05 | 40 | 0.0204 | 0.0292 |
| 0.10 | 20 | 0.0461 | 0.0659 |
| 0.20 | 20 | 0.0888 | 0.1269 |

Here the detectable-effect approximation is `(1.96 + 0.842)*SE` for an unadjusted
two-sided test. It becomes optimistic with few groups, multiplicity, skew or
boundary masses. Detecting a positive effect and demonstrating an effect exceeding
0.03 are distinct requirements: the latter requires the lower confidence bound
to exceed 0.03. Simulate candidate designs using development-only variance ranges,
crossed correlations, infeasible-target fractions and bounded outcomes before
freezing a final sample count. Never keep adding seeds until significance.
More seeds cannot remove target heterogeneity; the unit tests verify that fact.

At 20 groups × three regions × ten seeds × six methods, the eight-request cap
costs 28,800 requests. Adding a separate 32-request evaluation raises the total
to 144,000 requests, or 288,000 two-head calls before cache savings, training and
validation. These are proposed costs, not runs launched here. A fixed oracle may
allow physical caching, but each method still pays its logical query budget.

## What would justify moving to confirmation

The next actionable step is identity/context qualification and a fixed component
manifest, not an outcome-driven search for favorable genes. Certify a sufficient
cohort, choose pipeline and controls using development only, freeze checkpoints,
inputs and sample counts, then run all preregistered final cells once. Retain
infeasible targets, failures and unfavorable valid results. If independent measured
support remains unavailable, publish the narrower computational finding with the
exposure ledger and its limitations. Current progress supports further disciplined
experiments; it does not establish finalized biological validity or a PPO-specific
scientific advancement.
