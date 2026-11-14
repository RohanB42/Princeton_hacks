# Immunomodulation endpoints: TLR7 inhibition and TLR8 potentiation

**Protocol frozen 2026-11-14 before any evaluation seed was run. Results are appended
below the line "Results" only after the runs finish; nothing above that line changes
afterwards.** Third and fourth endpoints, after Huesken efficacy
(`predictor-first-pass.md`) and MOE acute neurotox (`neurotox-moe-predictor.md`).
Predictor studies only: no acquisition, no active-learning claim, no design use.

## The upstream key/assay mismatch, resolved

`open-questions.md` recorded that "TLR7/TLR8 registry descriptions disagree with
their keys" and blocked modelling until the mapping was settled. It is now settled,
from the data and the source paper rather than from the labels:

| Dataset | Assay actually measured | Label scale | Published alias | Upstream key |
| --- | --- | --- | --- | --- |
| `Alharbi_2020_1` | **TLR8 potentiation** | 0.57-5.44, mean 2.18 (resiquimod = 1.0) | `immune_modulation_TLR7` | `TLR7` |
| `Alharbi_2020_2` | **TLR7 inhibition** | 17.5-126.5, mean 49.8 (resiquimod = 100) | `immune_modulation_TLR8` | `TLR8` |

Three independent lines agree that the **assay descriptions are right and the
registry `key` column is wrong**:

1. Each file's `label_desc` states its own normalization — resiquimod = 1.0 for the
   TLR8 assay, resiquimod = 100 for TLR7 — and each file's values sit on exactly
   that scale. The description and the data agree; the key is a bare string with
   nothing corroborating it.
2. The published benchmark rows can be matched to files by RMSE magnitude, which the
   row counts (192 each) cannot do. `immune_modulation_TLR7` has median test RMSE
   0.889 against a label SD of 1.00, so it ran on `Alharbi_2020_1`;
   `immune_modulation_TLR8` has median 23.5 against a label SD of 23.08, so it ran on
   `Alharbi_2020_2`. The aliases therefore follow the swapped key.
3. Alharbi et al., *Nucleic Acids Research* 2020, 48(13):7052-7065
   ([10.1093/nar/gkaa523](https://doi.org/10.1093/nar/gkaa523)) report that these
   2'OMe gapmer ASOs **inhibit TLR7** and **potentiate TLR8** — the direction each
   description implies, and the reason the two assays carry different normalizations.

**Consequence for any write-up:** the published leaderboard row labelled
`immune_modulation_TLR7` (best 0.727) is the **TLR8 potentiation** assay, and
`immune_modulation_TLR8` (best 0.6995) is **TLR7 inhibition**. The v5 plan's
baseline table has these two labels the wrong way round. Report the assay, never the
upstream key, and say which published row a number is being compared against. This
is worth reporting upstream; it is a labelling bug in
`all_datasets_info.csv.gz`, not in the data.

## Design

- Data: 192 ASOs per endpoint, the **same 192 sequences in the same order** for both,
  4 targets (CDKN2B-AS1, CTNNB1, EGFR, LINC-PINT) x 48. Labels unchanged.
- The two endpoints are **separate tasks and are never pooled.** They share
  sequences, not units: one is a fold-potentiation on a resiquimod = 1.0 scale, the
  other a percent-of-resiquimod inhibition. `AGENTS.md` forbids a combined score, and
  a model fitted across both would be fitting two different measurements.
- Split: official OligoGym **`nucleobase`** split per seed (8 k-mer clusters,
  `kmer_max=3`, `strand="RNA1"`, `test_size=0.2`), as for the other endpoints. With
  192 rows this leaves roughly 154 train / 38 test.
- **No random split is run.** These are mutant screens around a few parent
  sequences, so a random split puts near-duplicates on both sides. The published
  random-split numbers for these datasets exist but should be read with that in mind.
- No target split: 4 targets cannot support one, exactly as the v5 plan anticipated.
- Seeds **300-329** (30), fixed before any evaluation, disjoint from Huesken
  (100-129), the acquisition suites (100-149) and MOE neurotox (200-229).
- Representation: one-hot nucleobase only, alphabet (A,C,G,T,U), 20 positions, 100
  features. Sugar and phosphate are **not** encoded here because they are constant —
  every row is a 5-10-5 2'OMe gapmer on a full phosphorothioate backbone, so those
  components can only contribute zero-variance columns. The script asserts the
  constancy and fails if it does not hold, rather than assuming it. (`SUGAR_ALPHABET`
  deliberately still lacks the 2'OMe symbol `m`, so encoding chemistry on these rows
  would raise rather than silently zero it; adding the symbol would change the MOE
  endpoint's feature count and break that result's reproducibility, and there is
  nothing to gain here.) This is the
  opposite decision to `neurotox-moe-predictor.md`, where chemistry varies and
  encoding it gained +0.066; the reason for the difference is the data, not a
  preference. Note the base alphabet still carries the gapmer layout implicitly,
  since the 2'OMe wings use U and the DNA core uses T.
- Models: `OneHotGaussianProcess` with the kernel **frozen on Huesken** (RBF, initial
  length scale 4), not re-selected here; and `OneHotRandomForest` at the Gate 1
  anchor configuration (100 trees, depth 20), which has a published mean for exactly
  this configuration on both datasets.

## Published references (upstream `benchmarks/oligogym_benchmarks.csv`, nucleobase)

| Dataset (assay) | RF one-hot base, depth 20, 100 trees | Fold SD | Best published configuration |
| --- | ---: | ---: | ---: |
| `Alharbi_2020_1` (TLR8 potentiation) | 0.6590 | 0.0501 | 0.727 (RF, base, depth 10, 1000 trees) |
| `Alharbi_2020_2` (TLR7 inhibition) | 0.5896 | 0.0778 | 0.6995 (RF, base+sugar+phosphate, depth 30) |

Two cautions. The published best for `Alharbi_2020_2` encodes sugar and phosphate,
which we have just established are constant on these rows — so that configuration
differs from the base-only one only by zero-variance columns and random seed, and
the 0.0546 gap between them (0.6995 vs 0.6442 for the depth-20 variant) is a
direct measurement of how noisy five folds are here. Second, 38 test rows means a
Pearson r whose standard error is roughly 0.15 even when nothing is wrong.

## Metrics (fixed in advance)

Pearson r (primary, for comparability) and Spearman rho (the dataset metadata
recommends both), plus RMSE, MAE, runtime, the GP uncertainty diagnostics used on
the other endpoints, and the count of seeds whose r is non-positive. Mean over 30
seeds with **sample SD**, never a confidence interval.

## Expectations stated before running

- **Variance will dominate.** 38 test rows per seed is the smallest evaluation in
  the project, and the plan's risk list puts tiny-dataset variance first. Expect a
  seed SD at least as large as the MOE endpoint's 0.11-0.19, and expect some seeds
  near or below zero. A result that is mostly noise is a reportable result.
- The RF anchors should reproduce within noise; the published fold SDs (0.050,
  0.078) are themselves five-draw estimates.
- No expectation is stated about GP versus RF, and none about which assay is easier.

## Non-claims

No wet-lab, therapeutic or clinical safety claim. No target-generalization claim (4
targets, no target split). No combined safety/efficacy score and no pooling of the
two assays. No claim about CpG or other motif mechanisms: this is a sequence-to-
readout regression, and any motif reading would need its own analysis. A predicted
TLR readout is a prediction, not an observation.

## Results

To be appended after the run.
