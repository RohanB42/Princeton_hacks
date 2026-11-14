# Safety endpoint predictor: MOE acute neurotox (ASO)

**Protocol frozen 2026-11-14 before any evaluation seed was run. Results are appended
below the line "Results" only after the runs finish; nothing above that line changes
afterwards.** This mirrors `predictor-first-pass.md` (Huesken efficacy) for the
second endpoint, and it is a *predictor* study: no acquisition, no active-learning
claim, no design or reward use.

## Why this endpoint

`MOE_Neurotox_1` (benchmark alias `acute_neurotox_moe_cleaned`) replaced cytotox LNA
after Dr. Shuying Sun's note that the field runs phosphorothioate/2'-MOE chemistry,
not LNA. It is the only safety endpoint in the collection whose chemistry matches the
chemistry any later design work would be constrained to, and it is in vivo rather
than an in vitro caspase assay.

- 2,437 ASOs, 13 targets, single strand of 15-19 monomers.
- Label: 3h functional observational battery (FOB) score in mice, **rounded to eight
  ordinal categories** (0 safe .. 7 toxic), modelled as regression. `y` equals
  `round(y_raw)` on every row; the raw column correlates 0.996 with it.
- Provenance: scraped from thirteen patents. Expect selection effects — companies
  patent what works. Target mix is dominated by UBE3A-ATS (561), ATXN2 (357) and
  GFAP (340); SOD1 has 2 rows.
- Chemistry: every cytosine is 5-methylcytosine; 19 distinct gapmer patterns, the
  most common being 5 MOE / 10 DNA / 4 MOE; backbone is a mix of phosphorothioate
  (30,386 linkages) and phosphodiester (12,631).

## Design

- Split: official OligoGym **`nucleobase`** split per seed (8 k-mer clusters,
  `kmer_max=3`, `strand="RNA1"`, `test_size=0.2`), the same configuration as the
  published benchmark and as our Huesken work. No target split is run here, and none
  is claimed; 13 targets with that concentration would not support one well.
- Seeds **200-229** (30), fixed before any evaluation, disjoint from the Huesken
  seeds (100-129) and the acquisition seeds (100-149).
- Two featurizations, each crossed with two model families (four arms):
  - **`base`**: one-hot nucleobase only, declared alphabet (A, C, G, T, U, m5C),
    19 positions, 114 features.
  - **`chem`**: base + sugar + phosphate, 228 features — i.e. the encoding that
    spells out the gapmer wing/core pattern and the PS/PO backbone. The published
    leaderboard's best configurations for this dataset use exactly this encoding.
- Models: `OneHotGaussianProcess` and `OneHotRandomForest` behind the unchanged
  `Predictor` contract. The GP kernel is the one **frozen on Huesken** (RBF, initial
  length scale 4, `ConstantKernel * RBF + WhiteKernel`, bounds (1, 100)); it is not
  re-selected on this endpoint, so no selection on this data has taken place. The RF
  is the Gate 1 anchor configuration (100 trees, depth 20).
- Alphabets are module constants in `features/upstream.py`, not inferred from the
  rows being encoded, so the representation cannot depend on which rows are visible.
  Undeclared symbols raise instead of being encoded as all-zeros, which is what
  upstream's `OneHotEncoder` does silently.

## Published references (read from `benchmarks/oligogym_benchmarks.csv`)

Directly comparable, same model configuration, nucleobase split, five unseeded folds:

| Arm | Published mean Pearson r | Published fold SD |
| --- | ---: | ---: |
| RF, one-hot base | 0.4750 | 0.115 |
| RF, one-hot base+sugar+phosphate | 0.5394 | 0.1186 |

Context only, not a target: the dataset's best nucleobase configuration is a
Transformer on base+sugar+phosphate at **0.7025** (fold SD 0.0558), the best of 372
configurations, so it carries selection bias. There is no published GP on this
dataset, so the two GP arms have no reference and are reported as new numbers.

**The published folds on this dataset are extremely noisy.** Across RF one-hot
configurations the five-fold SD runs 0.04-0.32, and the same model family swings
from 0.32 to 0.58 across neighbouring hyperparameters. Any comparison to a single
published mean is therefore weak evidence in both directions. We report the gap in
units of combined standard error, as `gate1-resolution.md` does, rather than against
a fixed tolerance.

## Metrics (fixed in advance)

Pearson r (primary, for comparability with the published table) and Spearman rho
(reported alongside because the label is an eight-level ordinal and the dataset
metadata recommends both), plus RMSE, MAE and runtime. Mean over 30 seeds with
**sample SD**, never a confidence interval. For the GP arms: latent-SD spread, rank
correlation of uncertainty against absolute error and against distance to the
nearest training row, and interval coverage — the same uncertainty diagnostics as
the Huesken pass, since any later acquisition work on this endpoint depends on them.

## Expectations stated before running

- `chem` should beat `base`: the gapmer pattern is a known determinant of ASO
  toxicity, and the published ordering agrees (0.5394 vs 0.4750 for the RF anchor).
- The GP may do poorly. Its kernel was tuned on a different chemistry and a
  different label scale, and an eight-level ordinal is not what an RBF+White GP is
  built for. A null or below-RF result here is a reportable outcome, not a failure.
- Seed-to-seed SD should be large, in line with the published fold SD of about 0.11.

## Non-claims

No wet-lab, therapeutic or clinical safety claim. No target-generalization claim. No
combined safety/efficacy score: this endpoint stays separate from Huesken efficacy,
per `AGENTS.md`. A predicted FOB score is not an observation, and nothing here says
a designed molecule is safe.

## Results

To be appended after the run.
