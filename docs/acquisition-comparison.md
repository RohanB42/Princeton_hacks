# Four-policy acquisition comparison on Huesken (I4/I5)

**Protocol frozen 2026-11-14 before any run. Results are appended below the line
"Results" only after the runs finish; nothing above that line changes afterwards.**

## Question

At matched label budgets, does choosing which siRNAs to label by (a) predictor
uncertainty, (b) sequence diversity, or (c) both reach better held-out accuracy than
random choice? A flat or negative answer is a valid result and will be reported as is.

## Design

- Data/endpoint: Huesken, `Ichihara_2007_1`, 2,431 siRNAs, percentage inhibition,
  labels unchanged (including 134 values above 100).
- Split: official OligoGym **`nucleobase`** split (8 k-mer clusters, test_size 0.2)
  per seed. Not a target split; no target-split claim is made.
- Seeds 100-109 (ten), each with one split and one initial set shared by all arms.
  Initial 50 labels drawn uniformly (runner default); batches of 50; maximum 1,000
  labels (about 55% of the smallest training pool, 1,713 rows), so 20 checkpoints.
- Arms (primary predictor: one-hot GP, `gp_latent_sd_uncalibrated`):
  1. `random`: uniform without replacement.
  2. `uncertainty`: top-50 predictor uncertainty (existing policy).
  3. `diversity`: greedy farthest point in one-hot space, label-free, no predictor.
  4. `uncertainty_then_diversity`: top 200 (4x batch) by uncertainty, then greedy
     farthest point inside that pool measured against labeled and chosen rows.
  The 4x pool multiplier is fixed now and will not be tuned.
- Secondary predictor (same four arms, same seeds): one-hot RF with
  `rf_tree_prediction_sd_uncalibrated`. Reported separately, not pooled with the GP.
- Kernel and RF settings are those frozen in `predictor-first-pass.md`.
- Runner: unchanged `run_campaign`, `purpose="diagnostic"` (the runner's research
  guard still reads "pending Gate 1 integration" although Gate 1 is closed in
  `gate1-resolution.md`; updating it is an integrator task).

## Metrics (all fixed in advance)

- Pearson r on the held-out `nucleobase` test partition at each checkpoint
  (RMSE, MAE recorded too), plus a separate full-training-pool reference per seed.
- Primary statistic: normalized trapezoidal area under the Pearson curve over
  [50, 1000] labels, paired per seed against `random`. Report every seed, the mean
  difference and sample SD (not a confidence interval) and how many seeds favor each
  arm. n = 10 is small; no significance claim is made.
- Label efficiency: first checkpoint whose r is at least that seed's own full-pool
  reference r minus 0.03; `not_reached` otherwise. Also the runner's absolute 0.60
  threshold. No interpolation.
- Context for every curve: the full-pool reference r (mean +- SD across seeds).

## Expectations stated before running

- The GP latent SD is almost flat but tracks distance to the labeled set (rank
  correlation 0.54), so arms 2 and 3 may behave alike. The hybrid may not separate
  from either. All arms may sit within noise of random; that would be reported.
- The 1,000-label cap may not reach the full-pool reference; if so the figure says so.

## Non-claims

No wet-lab, therapeutic, or target-generalization claim. Retrospective replay on an
existing labeled pool only. Seeds, arms, budgets and the hybrid pool size are not
changed after seeing results; failed runs are recorded, never dropped.

## Results

(pending)
