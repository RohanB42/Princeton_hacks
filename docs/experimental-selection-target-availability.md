# Available ASO target identifiers: metadata-only audit

November 15, 2026. This audit reads target, chemistry and assay metadata, not
measured inhibition values. Atlas release/cleaned/fold hashes were verified.
No new predictor fitting, policy training or measured outcome evaluation occurred.

## Counts relevant to the efficacy replay

| Stage | Target identifier count |
|---|---:|
| Raw Atlas in-vitro inhibition table | 385 |
| After current complete-context and DNA/MOE/cEt chemistry filters, all species | 97 |
| Human, excluding HBV/HCV/HIV under the existing cohort rule | 85 |
| Human targets with a compatible campaign of at least 100 distinct compounds, before holdout | 17 |
| Human targets with at least one campaign supporting 50 pool purchases plus 20 sentinel records under the existing grouped split | 28 |
| Evaluation targets in the latest completed PPO run | 2 |

Counts use stripped, uppercase recorded identifiers. The raw file includes
unresolved or ambiguous labels, so 385 is not a count of curated independent genes.
The 85 filtered identifiers also require alias verification; ambiguous EXON labels
do not appear among the 28 grouped-capacity candidates.

The practical 28-target count applies the existing same-length near-sequence
grouping and GroupShuffleSplit with test_size=0.2 and seed 20261114. Candidate
campaigns are considered in descending metadata-only compound count, with stable
campaign-ID tie breaking. For a target, accept the first campaign with at least
50 pool IDs and 20 disjoint sentinel IDs. No alternate seeds or labels are used.
The 17-target threshold is a simpler pre-holdout size count; it is not the same
criterion, since some smaller campaigns can still satisfy the 50+20 split.

## Twenty-eight targets passing the individual grouped-capacity check

AGT, ANGPTL3, ATXN3, C9ORF72, DGAT2, DMPK, DUX4, EZH2, F11, F12, F7,
FGFR4, GHR, IRF4, IRF5, KCNQ2, KRAS, MAPT, NLRP3, PLN, PRKDC, PSD3,
PTBP1, SMAD7, SNCA, SOD1, STAT3 and TTR.

This supplies candidate targets for expanding the research protocol, not automatic
admission to a new final test. Cross-role patent/compound/sequence overlap, target
aliases, broader homology, campaign compatibility and prior label exposure still
require audit. Some targets already appear in prior source-model fitting or
calibration, and several were used in older policy/robustness studies. Freeze
new roles and refit a source prior with the required target exclusions before
claiming held-out target evaluation. Repeated campaigns or seeds on one gene do
not create additional independent target genes.

For other Atlas endpoints, raw target-name counts are 127 (dose response), 43
(hepatotoxicity) and 15 (neurotoxicity); their cross-endpoint union with inhibition
has 434 identifiers. These endpoints have different roles and are not pooled into
the inhibition replay or a combined safety/efficacy claim.

## Local receipts

`artifacts/experimental-selection-target-availability/audit.json` contains raw
and filtered counts, candidate-capacity thresholds, target lists and previous
source-role membership. `grouped-capacity.json` contains the selected campaign,
pool/sentinel sizes, sequence group count and source-exposure flags for every
one of the 28 candidates. The receipts are generated artifacts and remain ignored.
