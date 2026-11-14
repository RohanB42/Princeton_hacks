# Independent scientific audit: November 14, 2026, 05:45 AM EST checkpoint

The checkpoint describes completed evidence recorded before 05:45 AM EST. This
independent read-only review was completed after that cutoff, at 05:56 AM EST.
The full learning suite completed at 05:43:54 and the paired report was recorded
at 05:44:22. No model, split, policy, configuration, label or run artifact was
changed by this audit. The companion PDF is compiled later from LaTeX.

## Outcome

No ledger or source-consistency violation was found in the ten completed Huesken
CNN campaigns. The independently recomputed primary result is diversity minus
random normalized Pearson learning-curve area **-0.0149663 ± 0.0397593 sample SD**
across five paired holdouts: two positive differences and three negative.
There is no consistent coverage-selection benefit in this pilot. This does not
reject all active-learning strategies or establish significant inferiority.

At 500 measured labels, mean held-out Pearson is **0.537811 ± 0.047960 SD** for
random and **0.428464 ± 0.220677 SD** for diversity. The study-specific full-pool
reference is **0.613164 ± 0.042667 SD**. The high diversity variability remains
visible in the figures. The near-full threshold is reached in 1/5 diversity runs
and 0/5 random runs, so a comparative label-saving ratio is not identified.

## Checks performed

| Check | Result |
| --- | --- |
| Complete cohort | All 2,431 Huesken observations partitioned in each holdout |
| Pairing | Identical initial IDs, split, model, config and budgets within each seed |
| Reveals | Unique eligible training IDs only; exact checkpoints 50,100,...,500 |
| Training-label accounting | Initial labels counted; exactly 500 acquired labels per campaign |
| Model/kernel identity | Same frozen native one-hot CNN and source hashes across all ten campaigns |
| Full reference | Five fresh eligible-pool fits; only matching reference reused for the second policy |
| Metric aggregation | Independent trapezoidal AULC, paired differences, sample SD and terminal means match |
| Source consistency | Executed source hashes match suite and current source for every recorded file |
| Data catalogue | 12 released datasets; 337,593 validated measurement rows; endpoints remain separate |
| Regression checks | Independent recheck: 104 tests passed in 9.17 seconds |

Source inspection confirms that the CNN encoder fits currently acquired sequences
only, the CNN receives acquired labels only, and early stopping uses the training-
internal validation split. The runner defers test scoring until acquisition is
finished. Diversity receives label-free embeddings, not measured efficacy or an
oracle/evaluator capability. These source checks and invariant tests are evidence
for the specified implementation boundaries, not a claim of prospective validation.

The complete raw and aggregate artifacts remain explicitly measured diagnostics;
the scoped Huesken numerical reproduction does not close the unresolved expanded
seven-dataset or exact historical reproduction gate.

## Additional label-free split audit

RNA1 is treated strictly as the source's RNA1 strand, without assuming guide
orientation. Distances compare its 21 base tokens, preserving T and U as distinct
tokens. Each test strand is compared with all equal-length eligible training
strands; no efficacy label is used.

| Seed | Train | Test | Exact HELM overlap | Median nearest RNA1 Hamming distance | Shared target genes |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 1,719 | 712 | 0 | 7/21 | 30/30 |
| 1 | 1,715 | 716 | 0 | 7/21 | 30/30 |
| 2 | 1,757 | 674 | 0 | 7/21 | 30/30 |
| 3 | 1,800 | 631 | 0 | 7/21 | 30/30 |
| 4 | 1,746 | 685 | 0 | 7/21 | 30/30 |

No held-out RNA1 strand is within one or two base-token differences of an
equal-length training RNA1 strand in these five splits. This is a specific
similarity diagnostic, not proof that every leakage or similarity mode is absent.

All 30 target genes appear in both train and test in every holdout; all test rows
therefore have a target already represented in training. This is expected under
the official sequence-cluster split and is not a protocol violation. It does mean
that **unseen-target generalization has not been evaluated**.

## Scientific interpretation and limits

- The predictor's target is measured in-vitro reporter-assay percentage inhibition,
  not probability of therapeutic success. Other ASO/shRNA endpoints stay separate.
- Diversity is label-blind max-min sequence coverage. It tests one selection
  heuristic, not a learned efficacy-feedback acquisition policy.
- The five cluster holdouts may overlap. Sample SD is not a confidence interval;
  this report does not claim significance or a population-wide effect.
- Four of seven independently reproduced best-model means meet the fixed 0.03
  comparison tolerance. Ichihara, OpenASO and ASOptimizer remain outside it. No
  entire-paper or historical bitwise reproduction claim is supported.
- The source/config archive is exact for the executed pilot, but the current
  working implementation is local/uncommitted. No clean-install identity claim
  is added by this audit.

The immediate useful continuation is a separately frozen feedback-aware acquisition
comparison, preserving random/coverage baselines and evaluation boundaries, plus
a separately declared target-held-out study before an unseen-gene claim. Biological
design, multi-endpoint safety and RL are independent future workstreams.

## Audit outputs and reproducibility

- `artifacts/checkpoint-20261114-0545/audit.json`: checks, split diagnostics and all input SHA256 values.
- `artifacts/checkpoint-20261114-0545/audit_checkpoint.py`: read-only audit and figure-generation script.
- `artifacts/checkpoint-20261114-0545/learning_curve.pdf` and `.png`: Pearson-only learning curve.
- `artifacts/checkpoint-20261114-0545/baseline_deltas.pdf` and `.png`: seven-dataset reference differences.
- `artifacts/checkpoint-20261114-0545/paired_deltas.pdf` and `.png`: all five paired AULC differences.
- `docs/checkpoints/2026-11-14-0545.tex`: three-page report source; parent performs compilation/visual QA.

The source is pinned to Roche/OligoGym
`97f5b9f58d9e445a8ecb0218037af7465c3708c0`. Primary inputs are the frozen
`configs/huesken-learning.toml`, the raw pilot suite, its paired report, and the
seven-dataset baseline report. All numerical summary values above were recomputed
from the completed raw ledgers. Figures use real outputs only.

Read-only audit command, from the repository root with the existing upstream environment:

```sh
PYTHONPATH=src MPLCONFIGDIR=/tmp/oligoal-mpl OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  /private/tmp/oligoal-upstream-envs/oligogym-2ScCOzQO-py3.11/bin/python \
  artifacts/checkpoint-20261114-0545/audit_checkpoint.py
```

This script writes regenerated audit/figure outputs only in the checkpoint artifact
directory. It does not train models, alter source inputs or tune policies.
