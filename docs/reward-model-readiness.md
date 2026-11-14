# Are the endpoint models a usable reward for an RL design layer?

**Exploratory readiness check, 2026-11-14.** Run after the endpoint studies were
frozen, to answer one question the frozen studies do not: those studies hold out
*sequences*, and an RL policy would be asked to design for a *gene the model has
never seen*. `scripts/reward_transfer_check.py` holds out an entire target.

## Leave-one-target-out transfer

GP, same featurization as each deployment model, one fold per target with at least
30 rows.

| Endpoint | Held-out targets | Mean Pearson r | Mean Spearman | Within-distribution reference | Retained | Negative folds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Acute neurotox (MOE) | 10 of 13 | **0.492** | 0.487 | 0.597 | 82% | 1 of 10 |
| ASO knockdown | 5 of 5 | **0.200** | 0.191 | 0.317 | 63% | 0 of 5 |

Per fold:

| Neurotox target | r | | Efficacy target | r |
| --- | ---: | --- | --- | ---: |
| ATXN2 | +0.659 | | HBV | +0.273 |
| GFAP | +0.664 | | DGAT2 | +0.266 |
| UBE3A-ATS | +0.634 | | KLKB1 | +0.217 |
| ATXN3 | +0.636 | | SOD1 | +0.135 |
| LRRK2 | +0.634 | | MALAT1 | +0.109 |
| PRNP | +0.582 | | | |
| C9ORF72 | +0.487 | | | |
| SCN2A | +0.420 | | | |
| APP | +0.413 | | | |
| **SMN2** | **-0.211** | | | |

## Reading

**The safety term transfers; the potency term barely does.** Neurotoxicity keeps 82%
of its within-distribution correlation on a gene it has never seen, and eight of ten
folds sit above 0.41. Knockdown keeps 63% of a much weaker starting point, landing at
r = 0.20 — about 4% of the variance. Every efficacy fold is positive, so the signal
is real, but it is thin.

**That asymmetry is the main design constraint on any reward.** A naive
`predicted_knockdown - predicted_toxicity` reward would be dominated by the term that
works and would chase noise in the term that does not. Potency should enter as a
coarse filter or a rank-space term with a small weight, not as a headline objective,
until an ASO efficacy model with more than five targets exists.

**SMN2 is a warning, not an outlier to drop.** On that target the neurotox model is
*anti-correlated* (-0.211): optimising against it would actively select more toxic
molecules. One gene in ten behaving this way is the single strongest argument for a
novelty trust region rather than free optimisation.

## What else bears on reward validity

- **Uncertainty is a novelty detector, not an error bar.** Across six endpoints the
  GP latent SD correlates with distance to the labelled set at rho 0.67-0.73 and with
  absolute error at roughly zero. Useful for *constraining* a policy, useless as a
  confidence interval on being right.
- **Predictions are unbounded.** On MAPT, 28% of tiled candidates receive a predicted
  FOB outside the measured 0-7 range, with values up to 9.6 before any optimisation
  pressure. A maximiser will find that region immediately.
- **Candidates already start far outside the data.** Median novelty percentile of
  plain tiled candidates is 99.7. RL moves further out by construction.
- **The models did learn real biology.** Predicted neurotox correlates with the
  published guanine-proximity rule (rho -0.35 to -0.39) and with longest G-run
  (+0.60) without ever being given either. A reward that reproduces known chemistry
  is more trustworthy than its r alone suggests.

## Verdict

Usable as a reward **inside a trust region**, not as a free optimisation target.
Concretely, before any RL result is believed:

1. **Constrain by novelty.** Reject or heavily penalise candidates beyond a fixed
   novelty percentile, chosen before the run.
2. **Clip to the measured label range.** Out-of-range predictions earn no extra
   credit, so the policy cannot profit from extrapolation.
3. **Rank-space rewards.** These models order better than they calibrate; Spearman
   tracks Pearson closely on every endpoint.
4. **Ensemble disagreement as a penalty.** A GP and an RF are already fitted for each
   endpoint; where they disagree, the reward is unreliable by construction.
5. **Weight potency below safety**, per the transfer numbers above.
6. **Declare a reward-hacking check in advance**: if the policy's top candidates
   violate the published heuristics the predictors otherwise agree with (G-runs, CpG,
   3' guanine), that is hacking, not discovery.

Nothing here licenses a claim that a designed molecule works or is safe. The RL layer
remains outside the measured result, as the project plan has said since v1.
