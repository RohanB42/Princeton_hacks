# OLIGARCH: priority additions to Related Work

Prepared November 16, 2026, for the current dual-environment manuscript.

This shortlist prioritizes direct predecessors for molecular design, experimental
selection, and potency measurement. It supplements the existing citations to
OligoGym, ASO Atlas 2.0, RNA-FM, LoRA, PPO, action masking, and nonmyopic and
multifidelity active search. Numbers in parentheses refer to the supplied long
literature review. These are editorial recommendations, not a completed audit of
every paper's numerical results or bibliographic fields.

## Ten priority sources

### 1. OligoAI — ASO prediction and model-guided screening (#12)

Hill et al. (2026). **Accurately modeling RNase H-mediated antisense
oligonucleotide efficacy.** *Molecular Therapy Nucleic Acids*.
[Paper](https://doi.org/10.1016/j.omtn.2026.103004)

Include as a direct ASO prediction predecessor that incorporates molecular and
experimental context and reports experimental validation. It helps explain the
transition from predicting efficacy to evaluating budgeted decisions. Distinguish
this publication from the separately versioned Atlas 2.0 release; avoid importing
its experimental performance into our retrospective results.

### 2. ASOptimizer — chemistry-aware ASO modeling (#9)

Hwang et al. (2024). **ASOptimizer: Optimizing antisense oligonucleotides through
deep learning for IDO1 gene regulation.** *Molecular Therapy Nucleic Acids*.
[Paper](https://doi.org/10.1016/j.omtn.2024.102186)

Include when introducing chemistry-aware prediction and design. It provides
domain-specific context for our molecular construction choices and endpoint
models. Describe our contribution as evaluating constrained search and acquisition
decisions, rather than introducing chemistry-aware ASO prediction itself.

### 3. OligoFormer — RNA representations for oligonucleotide activity (#6)

Bai et al. (2024). **OligoFormer: an accurate and robust prediction method for
siRNA design.** *Bioinformatics*.
[Paper](https://doi.org/10.1093/bioinformatics/btae577)

Include as a close application of RNA-FM representations to siRNA efficacy.
It motivates our representation comparisons while keeping siRNA and ASO outcomes
distinct. Discuss architecture and endpoint differences rather than constructing
a leaderboard from incompatible published correlations.

### 4. OligoRL — constrained oligonucleotide design with RL

David et al. (2022). **A reinforcement learning framework for pooled
oligonucleotide design.** *Bioinformatics*.
[Paper](https://doi.org/10.1093/bioinformatics/btac073)

Include as a direct methodological predecessor for the molecular environment.
OligoRL addresses constrained barcode, degenerate-oligo, and primer-pool design.
Our distinction is transcript-anchored ASO construction, chemistry-aware surrogate
scoring, and attribution of search performance to supervised initialization versus
PPO refinement under explicit query budgets.

### 5. GeneDisco — experimental-acquisition benchmark

Mehrjou et al. (2022). **GeneDisco: A Benchmark for Experimental Design in Drug
Discovery.** *ICLR*.
[Paper](https://arxiv.org/abs/2110.11875)

Include as a close benchmark precedent for comparing acquisition policies using
biological experimental data. Position OLIGARCH through its oligonucleotide
modality, linked assay eligibility, and concentration-level decisions. Do not
claim that benchmarking active experimental design is itself new.

### 6. PMO — molecular optimization under limited predictor queries (#45)

Gao et al. (2022). **Sample Efficiency Matters: A Benchmark for Practical
Molecular Optimization.** *NeurIPS Datasets and Benchmarks*.
[Paper](https://arxiv.org/abs/2206.12411)

Include to motivate strong conventional search baselines and explicit oracle-call
accounting. Its emphasis on sample efficiency connects directly to our molecular
search evaluation. Explain both deployment queries and offline policy-training
queries; equal deployment budgets do not imply equal total computational cost.

### 7. Task-specific molecular active learning (#21)

Ghosh et al. (2025). **Active learning of molecular data for task-specific
objectives.** *The Journal of Chemical Physics*.
[Paper](https://doi.org/10.1063/5.0229834)

Include to distinguish improving prediction across a distribution from finding
high-value candidates. This is a useful conceptual link between the Huesken
learning-curve study and the assay-selection hit-discovery studies. Acquisition
benefits should be described relative to their specific objective and protocol.

### 8. IC50 estimation guidelines (#61)

Sebaugh (2011). **Guidelines for accurate EC50/IC50 estimation.**
*Pharmaceutical Statistics*.
[Paper](https://doi.org/10.1002/pst.426)

Include when defining absolute versus relative half-maximal concentrations and
the evidence needed to report a numerical estimate. This is foundational for
distinguishing in-range estimates, threshold-qualified bounds, and unresolved
curves. It does not independently validate our particular adjudication thresholds
or early-stopping rules.

### 9. Optimal concentration-grid design

Donev and Tobias (2011). **Optimal Serial Dilutions Designs for Drug Discovery
Experiments.** *Journal of Biopharmaceutical Statistics*.
[Paper](https://doi.org/10.1080/10543406.2010.481801)

Include as a direct experimental-design precedent for choosing concentrations,
replication, and dose ranges. Contrast its potency-estimation objective with our
sequential decision about whether potency meets a threshold. This establishes
why concentration selection is a scientific design problem, not merely another
generic acquisition heuristic.

### 10. COBALT — learning and acquisition with censored observations (#63)

Karlova et al. (2026). **COBALT: Censored Optimization and Bayesian Active
Learning Techniques.** *UAI*, PMLR 337:2713–2743.
[Official proceedings](https://proceedings.mlr.press/v337/karlova26a.html)

Include as a recent censor-aware learning and optimization precedent. It separates
our empirical question—how bounds affect potency decisions and credited
discoveries—from methodological work on censored likelihoods and information-based
acquisition. Do not imply that OLIGARCH implements COBALT or introduces censored
Bayesian optimization.

## Additional citations with specific roles

- **Huesken et al. (2005), #2:** cite the original measurements in the dataset
  subsection, alongside OligoGym's redistribution and evaluation protocol.
  [Paper](https://doi.org/10.1038/nbt1118)
- **PFRED, Sciabola et al. (2021), #8:** add if the design paragraph discusses
  transcript-oriented enumeration and practical filtering.
  [Paper](https://doi.org/10.1371/journal.pone.0238753)
- **Olivecrona et al. (2017), #42:** add if explaining the lineage of pretrained
  molecular generation followed by RL refinement.
  [Paper](https://doi.org/10.1186/s13321-017-0235-x)
- **Holzmüller et al. (2023), #20:** add if the active-learning paragraph needs
  a regression-specific acquisition benchmark.
  [Paper](https://jmlr.org/papers/v24/22-0937.html)

## Priority manuscript comparison before finalizing novelty

Read the **Atlas 2.0 manuscript** as well as citing the dataset. Its official
repository describes a preclinical pipeline cost model and strategy comparisons,
which may overlap with our experimental-selection framing. Compare exact tasks,
information access, decisions, and evaluation units before finalizing novelty
language. Confirm publication status from a primary record.
[Atlas 2.0 repository](https://github.com/barneyhill/aso-atlas-2)

## Suggested Related Work organization

1. **Oligonucleotide prediction and design:** existing OligoGym/Atlas/RNA-FM
   citations plus OligoAI, ASOptimizer, and OligoFormer.
2. **Budgeted molecular optimization:** OligoRL and PMO; optionally Olivecrona.
3. **Experimental acquisition and planning:** GeneDisco and Ghosh, alongside
   the already-cited nonmyopic and multifidelity active-search papers.
4. **Potency interpretation and concentration selection:** Sebaugh, Donev and
   Tobias, and COBALT.

Keep this section focused on what prior work establishes and what OLIGARCH
evaluates differently. The completed LoRA studies and both decision environments
should remain part of the current framing; the earlier Huesken-only positioning
is no longer the manuscript's scope.
