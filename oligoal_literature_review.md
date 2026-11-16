# OligoAL literature review

**Your strongest contribution is a carefully bounded empirical result: uncertainty-based acquisition improves average predictive performance over a specified label-budget range, under one benchmark protocol, without establishing label savings or superiority over diversity.** The literature supports treating those as separate claims.

Below is a thematic review of **64 sources**, followed by methodological implications, suggested discussion language, reviewer challenges, and BibTeX. I prioritized primary research and read accessible abstracts and relevant full-text sections; detailed numerical comparisons below come from the reported experiments, not secondary summaries. This is a focused literature review, not a formally systematic review.

I treat your reported effect and confidence interval as supplied results, not as independently verified repository findings. Preprints are marked explicitly.

## 1. Oligonucleotide efficacy prediction: what the field already establishes

The historical progression is from sequence and thermodynamic rules, to statistical sequence models, to neural architectures and pretrained representations. Across that progression, **assay context, chemistry, dataset provenance, and the evaluation split remain central determinants of what a reported score means**.

### Foundational siRNA models

**1. Reynolds et al. (2004), Nature Biotechnology — [“Rational siRNA design for RNA interference”](https://doi.org/10.1038/nbt936).**  
Reynolds and colleagues analyzed 180 siRNAs targeting two genes and derived eight sequence and thermodynamic criteria associated with silencing activity. This establishes the importance of inexpensive biological and sequence-based baselines, while its limited target coverage illustrates why success within an experimental collection does not establish broad target-gene generalization.

**2. Huesken et al. (2005), Nature Biotechnology — [“Design of a genome-wide siRNA library using an artificial neural network”](https://doi.org/10.1038/nbt1118).**  
BIOPREDsi was trained on 2,182 siRNAs and evaluated on 249 independent test siRNAs, reporting Pearson correlation of approximately 0.66; the underlying collection involved 34 mRNA species. This is the primary experimental provenance for the widely reused Huesken collection, so your paper should distinguish the original experimental source from the later `Ichihara_2007_1` benchmark identifier.

**3. Vert, Foveau, Lajaunie and Vandenbrouck (2006), BMC Bioinformatics — [“An accurate and interpretable model for siRNA efficacy prediction”](https://doi.org/10.1186/1471-2105-7-520).**  
The DSIR model used regularized linear regression with positional nucleotide and sequence-motif features, obtaining approximately 0.67 Pearson correlation on the Huesken 2,182/249 split. Its competitiveness with BIOPREDsi is directly relevant to your use of a comparatively simple one-hot GP: sophisticated representations are not a prerequisite for a scientifically useful acquisition benchmark.

**4. Ichihara et al. (2007), Nucleic Acids Research — [“Thermodynamic instability of siRNA duplex is a prerequisite for dependable prediction of siRNA activities”](https://doi.org/10.1093/nar/gkm699).**  
Ichihara and colleagues developed i-Score using linear regression and examined how duplex thermodynamics affected prediction reliability, using a 2,431-sequence training collection and a 419-sequence validation collection. The paper supports including thermodynamic context in the discussion, but it should not be interpreted as evidence that the dataset subsequently bearing its name was an independently generated Huesken replacement.

### Deep learning, chemical modifications, and practical design

**5. Han, He, Chen, Liu and Yu (2018), BMC Genomics — [“SiRNA silencing efficacy prediction based on a deep architecture”](https://doi.org/10.1186/s12864-018-5028-8).**  
This model combined CNN-derived sequence information with additional contextual and thermodynamic features, reporting Pearson correlation 0.725 on a random 3,660/407 split of 4,067 pooled examples. It is a relevant example of “DeepSirna-style” modeling, but this random pooled-data result is not directly comparable with target holdout or a different released benchmark split.

**6. Bai, Zhong, Wang and Lu (2024), Bioinformatics — [“OligoFormer: an accurate and robust prediction method for siRNA design”](https://doi.org/10.1093/bioinformatics/btae577).**  
OligoFormer combines RNA-FM representations, thermodynamic features, and a transformer-based architecture, with both within-dataset and cross-dataset evaluations. It reports Huesken cross-validation Pearson correlation 0.7114 and cross-dataset Mixset correlation 0.5879; removing sequences above an identity threshold strengthens that evaluation, but cross-dataset testing still should not automatically be described as target-gene holdout.

**7. Dar, Thakur, Qureshi and Kumar (2016), Scientific Reports — [“siRNAmod: A database of experimentally validated chemically modified siRNAs”](https://doi.org/10.1038/srep20031).**  
siRNAmod assembled 4,894 entries covering 128 chemical modifications from 96 publications, together with experimental annotations. Its relevance is that nucleotide sequence alone does not define the experimental intervention: chemical modifications and assay conditions can change both activity and the meaning of apparently duplicated sequences.

**8. Sciabola et al. (2021), PLOS ONE — [“PFRED: A computational platform for siRNA and antisense oligonucleotides design”](https://doi.org/10.1371/journal.pone.0238753).**  
PFRED integrates transcript-oriented design with practical filters such as sequence specificity, SNPs, and problematic sequence patterns. It provides a useful precedent for evaluating a molecular-design environment against transparent design heuristics rather than treating a learned reward score as a complete measure of candidate quality.

### ASO models and benchmark infrastructure

**9. Hwang et al. (2024), Molecular Therapy Nucleic Acids — [“ASOptimizer: Optimizing antisense oligonucleotides through deep learning for IDO1 gene regulation”](https://doi.org/10.1016/j.omtn.2024.102186).**  
ASOptimizer combines sequence-oriented modeling with a chemistry-aware graph transformer and pairwise ranking, reporting 73.39% held-out pairwise accuracy and experimental evaluation of six IDO1 candidates. That accuracy is a ranking metric under its own evaluation protocol, not an efficacy-regression correlation or evidence of generalization to unseen genes.

**10. Kang et al. (2025), Nucleic Acids Research — [“ASOptimizer: optimizing chemical diversity of antisense oligonucleotides through deep learning”](https://doi.org/10.1093/nar/gkaf392).**  
This web-server paper operationalizes prediction and ranking of chemical modifications for supplied ASO sequences. Cite it separately from the 2024 research paper and distinguish both from any curated dataset named “ASOptimizer”; the tool, model, and benchmark dataset are related but are not interchangeable objects.

**11. Rotrattanadumrong and De Donno (2025), NeurIPS Datasets and Benchmarks — [“OligoGym: Curated Datasets and Benchmarks for Oligonucleotide Drug Discovery”](https://proceedings.neurips.cc/paper_files/paper/2025/file/4927dd556ff6e49671e3a77ac1f12487-Paper-Datasets_and_Benchmarks_Track.pdf).**  
OligoGym standardizes 12 datasets and chemistry-aware representations, making it the most directly relevant benchmark reference. Its description of the nucleobase procedure uses k-mer clustering to **stratify** splitting; therefore, cite the released assignments and implementation rather than assuming that “nucleobase split” necessarily means cluster-disjoint or target-disjoint evaluation.

**12. Hill et al. (2026), Molecular Therapy Nucleic Acids — [“Accurately modeling RNase H-mediated antisense oligonucleotide efficacy”](https://doi.org/10.1016/j.omtn.2026.103004).**  
OligoAI combines a large RNA language model with chemistry and experimental context using a collection of 188,521 gapmers across 334 genes. The paper reports median Spearman correlation 0.419 across 299 held-out test screens, illustrating both the value of contextual information and the difficulty of comparing screen-level ASO evaluation with sequence-level siRNA benchmarks.

### Reported performance: preserve the split beside every number

These values are **contextual reference points, not a common leaderboard**.

| Study | Reported setting | Reported result | Interpretation limit |
|---|---|---:|---|
| Huesken 2005 | 2,182 training / 249 test siRNAs | Pearson ≈0.66 | Original fixed test set |
| Vert 2006 | Same Huesken split | Pearson ≈0.67 | Strong simple-model baseline |
| Han 2018 | Random 3,660/407 split of pooled data | Pearson 0.725 | Not target holdout |
| OligoFormer 2024 | Huesken five-fold evaluation | Pearson 0.7114 | Within-dataset evaluation |
| OligoFormer 2024 | Huesken training → Mixset testing | Pearson 0.5879 | Cross-dataset, not automatically target-disjoint |
| ASOptimizer 2024 | Held-out pairwise comparisons | Accuracy 73.39% | Different prediction task and metric |
| OligoGym 2025 | Huesken CNN, repeated nucleobase split | Pearson 0.63 ± 0.03 | Released benchmark protocol |
| OligoAI 2026 | 299 held-out screens | Median Spearman 0.419 | Screen-level ASO endpoint |

Sources: [Huesken](https://doi.org/10.1038/nbt1118), [Vert](https://doi.org/10.1186/1471-2105-7-520), [Han](https://doi.org/10.1186/s12864-018-5028-8), [OligoFormer](https://doi.org/10.1093/bioinformatics/btae577), [ASOptimizer](https://doi.org/10.1016/j.omtn.2024.102186), [OligoGym](https://proceedings.neurips.cc/paper_files/paper/2025/file/4927dd556ff6e49671e3a77ac1f12487-Paper-Datasets_and_Benchmarks_Track.pdf), [OligoAI](https://doi.org/10.1016/j.omtn.2026.103004).

### Dataset inconsistencies that matter for your manuscript

**Dataset names are not sufficient provenance.** A benchmark may use a later paper’s name for measurements originating in an earlier publication. Record the original experiment, redistribution source, version, row identifiers, and transformations. Huesken and Ichihara should consequently appear as different stages of provenance, not as automatically independent datasets. [Huesken](https://doi.org/10.1038/nbt1118), [Ichihara](https://doi.org/10.1093/nar/gkm699).

**An entry is not necessarily an independent molecule or experiment.** Chemical variants, multiple doses, repeated measurements, and overlapping literature collections can inflate apparent sample size if treated as independent sequences. Preserve these distinctions when deduplicating or grouping data. [siRNAmod](https://doi.org/10.1038/srep20031), [ASOptimizer](https://doi.org/10.1016/j.omtn.2024.102186).

**Endpoint direction and scale require explicit contracts.** Residual expression, percentage inhibition, pairwise efficacy rankings, concentration-response potency, and toxicity scores cannot be pooled merely because all involve oligonucleotides. Your separation of siRNA efficacy, ASO efficacy, neurotoxicity, and TLR endpoints is scientifically appropriate.

**A high correlation can describe interpolation within one collection.** It does not by itself establish performance on a new gene, new chemistry, new cell type, or new experimental laboratory. [OligoFormer](https://doi.org/10.1093/bioinformatics/btae577), [OligoAI](https://doi.org/10.1016/j.omtn.2026.103004).

## 2. Active learning: uncertainty, diversity, and when random acquisition remains competitive

The most important distinction is between **learning an accurate predictor over a distribution** and **finding a small number of high-value candidates**. The literature contains successful examples of both, but evidence for one objective does not establish the other.

### Foundations and acquisition strategies

**13. Rasmussen and Williams (2006), MIT Press — [Gaussian Processes for Machine Learning](https://gaussianprocess.org/gpml/chapters/).**  
This provides the standard GP regression framework and posterior uncertainty equations underlying your model. For fixed kernel and noise hyperparameters, posterior variance depends on input locations rather than observed response values, making geometric coverage a plausible explanation for similarities between GP uncertainty acquisition and diversity selection.

**14. Houlsby, Huszár, Ghahramani and Lengyel (2011), arXiv preprint — [“Bayesian Active Learning for Classification and Preference Learning”](https://arxiv.org/abs/1112.5745).**  
BALD selects observations expected to reduce uncertainty about model parameters, distinguishing epistemic information from overall predictive uncertainty. It is a conceptual foundation for uncertainty-driven acquisition, but its classification formulation should not be presented as identical to maximizing GP regression variance.

**15. Sener and Savarese (2018), ICLR — [“Active Learning for Convolutional Neural Networks: A Core-Set Approach”](https://arxiv.org/abs/1708.00489).**  
The authors formulate batch acquisition as selecting a subset that covers the geometry of the remaining data and report that several earlier heuristics perform poorly in the batch CNN setting. This supports diversity as a serious comparator, although their image-classification experiments do not directly establish its effectiveness for siRNA regression.

**16. Kirsch, van Amersfoort and Gal (2019), NeurIPS — [“BatchBALD: Efficient and Diverse Batch Acquisition for Deep Bayesian Active Learning”](https://arxiv.org/abs/1906.08158).**  
BatchBALD maximizes joint information across a batch instead of independently taking the most uncertain points. Its central relevance is batch redundancy: multiple individually uncertain examples can provide nearly the same information, so uncertainty-only top-\(k\) selection is not necessarily a strong batch strategy.

**17. Ash, Zhang, Krishnamurthy, Langford and Agarwal (2020), ICLR — [“Deep Batch Active Learning by Diverse, Uncertain Gradient Lower Bounds”](https://arxiv.org/abs/1906.03671).**  
BADGE combines uncertainty and diversity through gradient embeddings and diverse sampling in that space. It motivates hybrid acquisition baselines, but adapting it to your GP regression setting requires a justified formulation rather than importing a classification implementation unchanged.

**18. Hacohen, Dekel and Weinshall (2022), ICML — [“Active Learning on a Budget: Opposite Strategies Suit High and Low Budgets”](https://proceedings.mlr.press/v162/hacohen22a.html).**  
This paper shows that acquisition behavior can reverse across label-budget regimes, with representative sampling particularly useful in very small-data settings. It provides a strong explanation for cold-start sensitivity and supports reporting budget-resolved differences rather than only an aggregate winner.

**19. Kirsch et al. (2021), arXiv preprint — [“Stochastic Batch Acquisition: A Simple Baseline for Deep Active Learning”](https://arxiv.org/abs/2106.12059).**  
The authors use stochastic sampling from acquisition scores to obtain more varied batches and report competitive performance against more elaborate batch methods. For your project, this motivates a relatively inexpensive additional baseline if deterministic uncertainty selection produces redundant batches.

**20. Holzmüller, Zaverkin, Kästner and Steinwart (2023), Journal of Machine Learning Research — [“A Framework and Benchmark for Deep Batch Active Learning for Regression”](https://jmlr.org/papers/v24/22-0937.html).**  
This study develops a kernel-based framework for regression acquisition and benchmarks combinations of representations, kernel transformations, and batch-selection rules. It is more directly applicable to your continuous efficacy outcome than many classification-centered active-learning papers, and it supports treating representation and acquisition as separate experimental factors.

### Molecular evidence for—and against—gains over random

**21. Ghosh, Todorović, Vehtari and Rinke (2025), Journal of Chemical Physics — [“Active learning of molecular data for task-specific objectives”](https://doi.org/10.1063/5.0229834).**  
Across three molecular datasets, the authors compare GP acquisition strategies for general prediction and targeted search: uncertainty combined with clustering performs well, but at optimized GP noise settings active learning does not outperform random for general predictive learning. Targeted search can nevertheless save substantial queries, making this one of the strongest references for separating your positive AULC result from an unestablished label-saving or discovery claim.

**22. Yin, Panapitiya, Coda and Saldanha (2023), Journal of Cheminformatics — [“Evaluating uncertainty-based active learning for accelerating the generalization of molecular property prediction”](https://doi.org/10.1186/s13321-023-00753-5).**  
The authors find statistically significant but modest improvements under some conditions and identify the importance of sufficiently informative initial training data. Their results align with a small positive effect in your benchmark while warning that unreliable uncertainty, especially outside familiar regions, can limit acquisition benefits.

**23. Gorantla, Kubincová, Suutari, Cossins and Mey (2024), Journal of Chemical Information and Modeling — [“Benchmarking Active Learning Protocols for Ligand-Binding Affinity Prediction”](https://doi.org/10.1021/acs.jcim.4c00220).**  
This benchmark varies predictive models and acquisition protocols across four targets and evaluates both global prediction quality and recovery of strong binders. Its main relevance is methodological: global RMSE or correlation and top-candidate retrieval answer different questions and can favor different acquisition behavior.

**24. van Tilborg and Grisoni (2024), Nature Computational Science — [“Traversing chemical space with active deep learning for low-data drug discovery”](https://doi.org/10.1038/s43588-024-00697-2).**  
The authors compare acquisition strategies, architectures, and libraries, reporting substantial gains in hit retrieval in their evaluated settings. This supports the practical potential of active learning, but hit-discovery enrichment should not be cited as direct evidence that a prediction learning curve must improve or that fewer labels will reach a specified correlation.

### Reliability, bias, and biological transfer

**25. Hirschfeld, Swanson, Yang, Barzilay and Coley (2020), Journal of Chemical Information and Modeling — [“Uncertainty Quantification Using Neural Networks for Molecular Property Prediction”](https://doi.org/10.1021/acs.jcim.0c00502).**  
Across five molecular regression datasets and complementary uncertainty metrics, no evaluated method was uniformly best, and error rankings were not consistently reliable. This undermines any assumption that an uncertainty estimate is automatically a dependable acquisition signal and supports directly evaluating its relationship to subsequent prediction errors.

**26. Scalia, Grambow, Pernici, Li and Green (2020), Journal of Chemical Information and Modeling — [“Evaluating Scalable Uncertainty Estimation Methods for Deep Learning-Based Molecular Property Prediction”](https://doi.org/10.1021/acs.jcim.9b00975).**  
The study compares dropout, ensembles, and bootstrapping while distinguishing epistemic and aleatoric uncertainty, finding advantages for ensembles and bootstrapping in the investigated setting. It emphasizes that uncertainty performance is context-dependent and that out-of-domain uncertainty remains difficult.

**27. Farquhar, Gal and Rainforth (2021), ICLR — [“On Statistical Bias in Active Learning: How and When To Fix It”](https://arxiv.org/abs/2101.11665).**  
Active acquisition changes the distribution of labeled training examples, which can bias estimates based on that acquired sample. The paper develops corrections and explains why their usefulness depends on the setting; for your study, the immediate implication is to evaluate on an untouched test set rather than treating acquired-pool performance as an unbiased estimate of generalization.

**28. Biswas, Khimulya, Alley, Esvelt and Church (2021), Nature Methods — [“Low-N protein engineering with data-efficient deep learning”](https://doi.org/10.1038/s41592-021-01100-y).**  
This work combines pretrained representations with small experimental training sets to guide protein engineering, including examples with only 24 measured variants. It establishes the biological plausibility of useful low-data prediction, but it is not a direct randomized comparison of uncertainty acquisition against random selection for oligonucleotide efficacy.

### Implications for your acquisition experiment

Three mechanisms deserve separate treatment:

| Mechanism | What to measure | Why it matters |
|---|---|---|
| Cold start | Effects by initial labeled-set size; sensitivity to initialization | An initially poor model may give poor acquisition rankings |
| Batch redundancy | Within-batch sequence similarity and covariance; unique coverage | High uncertainty can repeatedly select near-equivalent examples |
| Uncertainty reliability | Held-out error versus predicted uncertainty; interval coverage where applicable | Uncertainty can be miscalibrated or rank errors poorly |
| Distribution shift | Performance by distance to training sequences and by target | Good interpolation does not establish reliable extrapolation |
| Objective mismatch | Prediction AULC separately from hit retrieval and threshold attainment | An acquisition strategy can improve one objective without improving another |

These are supported by [Hacohen et al.](https://proceedings.mlr.press/v162/hacohen22a.html), [BatchBALD](https://arxiv.org/abs/1906.08158), [Hirschfeld et al.](https://doi.org/10.1021/acs.jcim.0c00502), and [Ghosh et al.](https://doi.org/10.1063/5.0229834).

**A particularly useful mechanistic analysis for your GP:** compare selected-sequence coverage under uncertainty and diversity, along with their acquisition-rank agreement. For a fixed Gaussian-likelihood GP,

\[
\operatorname{Var}[f(x)\mid X,y]
=
k(x,x)-k(x,X)\bigl(K(X,X)+\sigma^2I\bigr)^{-1}k(X,x).
\]

The response vector \(y\) does not appear directly. Hyperparameters fitted using labels can introduce indirect dependence, but with fixed hyperparameters an uncertainty–diversity similarity is mathematically unsurprising. This is an interpretation to test, not an established explanation of your observed result. [Rasmussen and Williams, Chapter 2](https://gaussianprocess.org/gpml/chapters/RW2.pdf).

## 3. Evaluation methodology: what makes your positive result credible

### Preregistration, variance, and statistical comparisons

**29. Nosek, Ebersole, DeHaven and Mellor (2018), PNAS — [“The preregistration revolution”](https://doi.org/10.1073/pnas.1708274114).**  
Preregistration separates predictions and planned analyses from decisions made after observing results. For your retrospective benchmark, the relevant distinction is that measurements already existed but the confirmatory acquisition comparison and analysis could still have been specified before running or inspecting the final experiment.

**30. Lüth, Bungert, Klein and Jaeger (2023), NeurIPS — [“Navigating the Pitfalls of Active Learning Evaluation: A Systematic Framework for Meaningful Performance Assessment”](https://arxiv.org/abs/2301.10625).**  
This paper identifies evaluation choices that can distort active-learning conclusions, including initialization, data composition, and validation-related decisions. It is especially relevant to your claim because acquisition gains can be smaller than the effects of seemingly routine protocol choices.

**31. Bouthillier et al. (2021), MLSys — [“Accounting for Variance in Machine Learning Benchmarks”](https://proceedings.mlsys.org/paper_files/paper/2021/hash/0184b0cd3cfb185989f858a1d9f5c1eb-Abstract.html).**  
The authors examine variation from data sampling, optimization, and hyperparameter choices and show why benchmark conclusions need an explicit account of variability. Forty acquisition seeds strengthen estimation conditional on your protocol, but do not automatically quantify uncertainty across datasets, targets, or alternative train/test partitions.

**32. Agarwal, Schwarzer, Castro, Courville and Bellemare (2021), NeurIPS — [“Deep Reinforcement Learning at the Edge of the Statistical Precipice”](https://arxiv.org/abs/2108.13264).**  
This work demonstrates how a small number of runs and unstable aggregate statistics can produce misleading RL comparisons, advocating interval estimates and more informative summaries. Its relevance extends to your PPO experiments and to reporting the distribution of paired acquisition effects rather than only mean curves.

**33. Demšar (2006), Journal of Machine Learning Research — [“Statistical Comparisons of Classifiers over Multiple Data Sets”](https://jmlr.org/papers/v7/demsar06a.html).**  
Demšar provides methods for paired algorithm comparisons across multiple datasets, including nonparametric tests and multiple-method comparisons. The important limitation for your paper is that 40 seeds on one dataset are not 40 independent biological datasets and should not be treated as such.

**34. Cawley and Talbot (2010), Journal of Machine Learning Research — [“On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation”](https://jmlr.org/papers/v11/cawley10a.html).**  
The paper shows that repeated model selection can overfit the evaluation procedure and produce apparent differences comparable to genuine algorithmic gains. This supports locking hyperparameter selection, budget ranges, and acquisition variants before the confirmatory comparison, especially when the observed effect is modest.

### Leakage and split design

**35. Kapoor and Narayanan (2023), Patterns — [“Leakage and the reproducibility crisis in machine-learning-based science”](https://doi.org/10.1016/j.patter.2023.100804).**  
This analysis catalogs leakage mechanisms across scientific ML and explains how they lead to irreproducible performance estimates. In your setting, test labels must be excluded from fitting, acquisition, tuning, early stopping, representation selection, and RL rewards—not merely from the final regression fit.

**36. Wu et al. (2018), Chemical Science — [“MoleculeNet: a benchmark for molecular machine learning”](https://doi.org/10.1039/C7SC02664A).**  
MoleculeNet standardized molecular datasets and emphasized different evaluation partitions, including random, scaffold, and temporal splits. The transferable lesson is that the split should represent the intended deployment question; for oligonucleotides, sequence novelty and target novelty are distinct axes.

**37. Yang et al. (2019), Journal of Chemical Information and Modeling — [“Analyzing Learned Molecular Representations for Property Prediction”](https://doi.org/10.1021/acs.jcim.9b00237).**  
This large evaluation examines learned molecular representations across public and industrial datasets and different splitting strategies. It supports the need to assess model improvements under realistic partitions and cautions against interpreting random-split success as broad prospective generalization.

**38. Joeres, Blumenthal and Kalinina (2025), Nature Communications — [“Data splitting to avoid information leakage with DataSAIL”](https://doi.org/10.1038/s41467-025-58606-8).**  
DataSAIL constructs partitions that reduce similarity-related information leakage while accounting for dataset constraints. It is relevant to sequence-aware splitting, although its comparative claims should be read alongside the authors’ [2026 addendum](https://doi.org/10.1038/s41467-025-67495-w), which clarifies aspects of the benchmark comparisons.

**39. Saravanan, Berman and Sober (2020), Neurons, Behavior, Data Analysis, and Theory — [“Application of the hierarchical bootstrap to multi-level data in neuroscience”](https://pmc.ncbi.nlm.nih.gov/articles/PMC7906290/).**  
This paper demonstrates how treating nested observations as independent can inflate false-positive rates and discusses hierarchical resampling. For your study, the general lesson is to match resampling units to the inferential claim; seeds, targets, assay groups, and individual molecules should not be indiscriminately pooled as independent replicates.

**40. Lakens (2017), Social Psychological and Personality Science — [“Equivalence Tests: A Practical Primer for t Tests, Correlations, and Meta-Analyses”](https://doi.org/10.1177/1948550617697177).**  
Equivalence testing evaluates whether effects are sufficiently small relative to a prespecified practical margin. This is essential for wording your null comparisons: failure to establish uncertainty superiority over diversity does not demonstrate that the methods are equivalent.

### A defensible statistical analysis for your paper

**Primary estimand.** Define the acquisition comparison as the mean paired difference in normalized learning-curve area over a prespecified budget interval. If \(m_s(b_j)\) is the performance for seed \(s\) at budget \(b_j\), a transparent trapezoidal definition is

\[
A_s =
\frac{1}{b_K-b_0}
\sum_{j=0}^{K-1}
(b_{j+1}-b_j)
\frac{m_s(b_j)+m_s(b_{j+1})}{2},
\]

followed by

\[
\Delta_s=A_s^{\mathrm{uncertainty}}-A_s^{\mathrm{random}}.
\]

This formula normalizes the budget axis only. If your implementation also normalizes the metric, uses a logarithmic budget axis, or subtracts a baseline, state that explicitly. Evaluation design and budget choice can change the conclusion. [Lüth et al.](https://arxiv.org/abs/2301.10625).

**Pair complete trajectories.** Use the same initial labeled set and outer test set for each paired comparison, and resample whole paired trajectories rather than treating budget checkpoints as independent observations. The latter repeatedly counts observations from the same run. Report the actual confidence-interval method used; do not retrofit a different method into the confirmatory result without marking it as a sensitivity analysis. [Bouthillier et al.](https://proceedings.mlsys.org/paper_files/paper/2021/hash/0184b0cd3cfb185989f858a1d9f5c1eb-Abstract.html), [Saravanan et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC7906290/).

**Explain the unit of inference.** Your 40-seed interval describes variation under the fixed benchmark design. Generalization across target genes or studies requires additional held-out groups and an analysis that respects those groups. A narrow seed interval can coexist with substantial uncertainty about transfer to a new biological setting.

**Treat threshold-based label savings as a different estimand.** A positive average curve difference does not guarantee an earlier crossing of a chosen performance threshold. Report threshold attainment, non-attainment, and uncertainty separately rather than converting \(+0.0095\) AULC into a percentage label saving.

**Describe preregistration precisely.** A registered seed list alone is weaker than a registered primary endpoint, budget interval, comparison, exclusion rule, hyperparameter protocol, and analysis. If any of those were selected after exploratory runs, distinguish the exploratory stage from the locked confirmatory experiment. [Nosek et al.](https://doi.org/10.1073/pnas.1708274114).

## 4. RL and generative design: comparison with heuristics and surrogate limitations

### RL methods and benchmark results

**41. Schulman, Wolski, Dhariwal, Radford and Klimov (2017), arXiv preprint — [“Proximal Policy Optimization Algorithms”](https://arxiv.org/abs/1707.06347).**  
PPO introduces a practical policy-gradient training objective that constrains updates through a clipped surrogate. It is the correct algorithmic citation for your environment, but PPO’s success on its original control benchmarks provides no evidence of superiority for oligonucleotide design.

**42. Olivecrona, Blaschke, Engkvist and Chen (2017), Journal of Cheminformatics — [“Molecular de-novo design through deep reinforcement learning”](https://doi.org/10.1186/s13321-017-0235-x).**  
This work adapts a pretrained molecular sequence model through reinforcement learning to favor desired properties, including predicted biological activity. It established a widely used approach to model-guided molecular generation, while also illustrating the distinction between optimizing predicted activity and validating activity experimentally.

**43. Zhou, Kearnes, Li, Zare and Riley (2019), Scientific Reports — [“Optimization of Molecules via Deep Reinforcement Learning”](https://doi.org/10.1038/s41598-019-47148-x).**  
MolDQN performs chemically valid graph edits using deep Q-learning and evaluates objectives involving molecular properties and similarity. It is a useful precedent for an explicit edit-based environment, but its reward functions and chemical space differ from those of oligonucleotide efficacy prediction.

**44. Brown, Fiscato, Segler and Vaucher (2019), Journal of Chemical Information and Modeling — [“GuacaMol: Benchmarking Models for de Novo Molecular Design”](https://doi.org/10.1021/acs.jcim.8b00839).**  
GuacaMol distinguishes distribution-learning and goal-directed molecular-generation tasks and includes classical optimization baselines. It supports evaluating validity, diversity, and task performance separately rather than using one favorable reward statistic to characterize an entire design system.

**45. Gao, Fu, Sun and Coley (2022), NeurIPS Datasets and Benchmarks — [“Sample Efficiency Matters: A Benchmark for Practical Molecular Optimization”](https://arxiv.org/abs/2206.12411).**  
The PMO benchmark compares 25 methods across 23 tasks under restricted oracle budgets and finds that many newer methods fail to outperform earlier approaches consistently. This directly supports your decision to retain heuristic baselines and report mixed PPO outcomes without implying algorithmic superiority.

**46. Tripp and Hernández-Lobato (2023), arXiv preprint — [“Genetic algorithms are strong baselines for molecule generation”](https://arxiv.org/abs/2310.09267).**  
The authors show that genetic algorithms remain competitive with, and can outperform, more elaborate molecular-generation methods. This is particularly useful when reviewers ask why your learned policy does not consistently beat simpler search: such outcomes are already part of the molecular-design literature.

### Surrogate exploitation and applicability

**47. Renz, Van Rompaey, Wegner, Hochreiter and Klambauer (2019 issue; online 2020), Drug Discovery Today: Technologies — [“On failure modes in molecule generation and optimization”](https://doi.org/10.1016/j.ddtec.2020.09.003).**  
This paper highlights cases where optimization improves a model’s score without corresponding agreement from control models, raising concerns about model- and data-specific biases. It motivates independent evaluation of generated candidates, although the cause of model disagreement requires further investigation rather than an automatic diagnosis of reward exploitation.

**48. Langevin, Vuilleumier and Bianciotto (2022), Journal of Cheminformatics — [“Explaining and avoiding failure modes in goal-directed generation of small molecules”](https://doi.org/10.1186/s13321-022-00601-y).**  
This study revisits such failure modes and shows that problems in the predictive models can explain optimization–control disagreement, including disagreement already present on the original distribution. It provides an important counterbalance: an independent predictor is a useful diagnostic, but disagreement alone does not prove that an optimizer generated biologically invalid candidates.

**49. Brookes, Park and Listgarten (2019), ICML — [“Conditioning by adaptive sampling for robust design”](https://proceedings.mlr.press/v97/brookes19a.html).**  
Conditioning by adaptive sampling addresses model-based design when predictive models become unreliable away from observed data. It motivates conservative search and attention to the relationship between generated candidates and the training distribution.

**50. Trabucco, Kumar, Geng and Levine (2021), ICML — [“Conservative Objective Models for Effective Offline Model-Based Optimization”](https://proceedings.mlr.press/v139/trabucco21a.html).**  
Conservative objective models penalize predictions that could encourage optimization toward unsupported regions of the design space. This offers a plausible future extension for your environment, but it would require a separate comparison and would not itself establish the true efficacy of generated oligos.

**51. Gao and Coley (2020), Journal of Chemical Information and Modeling — [“The Synthesizability of Molecules Proposed by Generative Models”](https://doi.org/10.1021/acs.jcim.0c00174).**  
The authors show that strong benchmark optimization scores can coexist with poor synthetic feasibility, and investigate ways to account for synthesizability. The corresponding lesson for oligos is to distinguish syntactic validity, allowed chemistry, sequence constraints, predicted efficacy, and experimentally supported activity.

### How to present your PPO component

A suitable interpretation is:

> The design environment evaluates optimization behavior under a fixed computational surrogate. Mixed comparisons with heuristics do not establish PPO superiority, and generated candidates remain unvalidated hypotheses.

Your most informative comparisons are **matched oracle-call budgets**, matched starting candidates, and matched validity constraints. Include random mutation, greedy local search, and a population-based heuristic if available; report both final score and score-versus-query area. This recommendation follows the evaluation concerns in [PMO](https://arxiv.org/abs/2206.12411) and the competitive heuristic results in [Tripp and Hernández-Lobato](https://arxiv.org/abs/2310.09267).

An independent predictor, sequence-distance analysis, and constraint checks can reveal weaknesses. They should be called **computational diagnostics**, not substitute experimental validation. [Langevin et al.](https://doi.org/10.1186/s13321-022-00601-y), [Gao and Coley](https://doi.org/10.1021/acs.jcim.0c00174).

## 5. RNA foundation models: promising representations, task-dependent benefits

**52. Chen et al. (2022), arXiv/bioRxiv preprint — [“Interpretable RNA Foundation Model from Unannotated Data for Highly Accurate RNA Structure and Function Predictions”](https://arxiv.org/abs/2204.00300).**  
RNA-FM learns representations from large collections of unannotated RNA sequences and evaluates their usefulness for structural and functional tasks. This establishes the representation’s origin, but does not establish that frozen RNA-FM features must improve short, chemically modified oligonucleotide efficacy prediction.

**53. Penić, Vlašić, Huber, Wan and Šikić (2025), Nature Communications — [“RiNALMo: general-purpose RNA language models can generalize well on structure prediction tasks”](https://doi.org/10.1038/s41467-025-60872-5).**  
RiNALMo is a 650-million-parameter RNA model trained on approximately 36 million sequences and evaluated on RNA structure and other downstream tasks. Its generalization results motivate testing stronger representations, but transfer from RNA structure learning to experimental oligo activity remains an empirical question.

**54. Ren et al. (2024), NeurIPS Datasets and Benchmarks — [“BEACON: Benchmark for Comprehensive RNA Tasks and Language Models”](https://arxiv.org/abs/2406.10391).**  
BEACON evaluates RNA language models across 13 tasks and examines methodological choices such as tokenization and positional representations. Its relevance is the task dependence of representation quality: a model should be evaluated on the intended endpoint rather than selected solely because it performs well on an unrelated RNA benchmark.

**55. Chu et al. (2024), Nature Machine Intelligence — [“A 5′ UTR language model for decoding untranslated regions of mRNA and function predictions”](https://doi.org/10.1038/s42256-024-00823-9).**  
UTR-LM combines sequence pretraining and structural information for untranslated-region function prediction and includes experimental evaluation of designed sequences. This is strong evidence that RNA representation learning can support functional design, while its translation-related endpoint and biological context differ substantially from siRNA-mediated knockdown.

**56. Hu et al. (2022), ICLR — [“LoRA: Low-Rank Adaptation of Large Language Models”](https://openreview.net/forum?id=nZeVKeeFYf9).**  
LoRA adapts pretrained models through trainable low-rank updates while keeping the original weights frozen. It is the appropriate methodological reference for a parameter-efficient adaptation experiment, but the original paper does not establish an advantage for RNA-FM, siRNA efficacy, or chemically modified ASOs.

### What the negative evidence actually supports

OligoGym provides directly relevant negative evidence for **frozen RNA-FM representations under its evaluated architectures**: one appendix comparison reports Huesken Pearson correlation of 0.63 ± 0.02 with one-hot input versus 0.59 ± 0.04 with RNA-FM. That supports retaining one-hot baselines; it does not establish that RNA foundation models generally fail, especially after adaptation. [OligoGym](https://proceedings.neurips.cc/paper_files/paper/2025/file/4927dd556ff6e49671e3a77ac1f12487-Paper-Datasets_and_Benchmarks_Track.pdf).

Conversely, OligoFormer reports useful contributions from RNA-FM within a larger architecture, and OligoAI integrates RiNALMo with chemistry and assay context. Those results suggest that integration and task context matter, rather than resolving a universal “one-hot versus foundation model” contest. [OligoFormer](https://doi.org/10.1093/bioinformatics/btae577), [OligoAI](https://doi.org/10.1016/j.omtn.2026.103004).

**I did not verify a paper establishing a direct RNA-FM-plus-LoRA advantage—or a robust negative result—for your exact siRNA active-learning setting.** Describe LoRA as a proposed experiment, not an established improvement.

A reasonable comparison would hold the acquisition protocol fixed and distinguish:

- One-hot representation with the existing predictor.
- Frozen RNA embeddings with a comparably tuned prediction head.
- LoRA adaptation using only labels available at the current budget.

Pretraining data, adaptation costs, tuning labels, and any sequence overlap with evaluation material should be disclosed. If a representation was chosen using final test outcomes, that comparison belongs in exploratory analysis.

## 6. Experimental validation and censored outcomes

### What experimental validation would need to establish

**57. Jackson et al. (2003), Nature Biotechnology — [“Expression profiling reveals off-target gene regulation by RNAi”](https://doi.org/10.1038/nbt831).**  
The authors demonstrate sequence-dependent off-target changes in gene expression following RNA interference. This is foundational evidence that successful intended-target knockdown does not establish molecular specificity or biological safety.

**58. Echeverri et al. (2006), Nature Methods — [“Minimizing the risk of reporting false positives in large-scale RNAi screens”](https://doi.org/10.1038/nmeth1006-777).**  
This standards-oriented commentary emphasizes validation approaches such as independent targeting reagents and rescue experiments, alongside appropriate controls. It provides support for distinguishing computational candidate ranking from experimentally substantiated biological mechanism.

**59. Hagedorn et al. (2022), Nucleic Acid Therapeutics — [“Acute Neurotoxicity of Antisense Oligonucleotides After Intracerebroventricular Injection Into Mouse Brain Can Be Predicted from Sequence Features”](https://doi.org/10.1089/nat.2021.0071).**  
This study connects ASO sequence features with acute effects in a specific mouse administration setting using experimental and computational analyses. Its endpoint is route-, species-, and assay-specific acute neurotoxicity, so it should not be generalized to a universal clinical safety score.

**60. Alharbi et al. (2020), Nucleic Acids Research — [“Rational design of antisense oligonucleotides modulating the activity of TLR7/8 agonists”](https://doi.org/10.1093/nar/gkaa523).**  
The authors show that ASO sequence and chemical modifications can produce opposing effects on TLR7 and TLR8, including TLR7 suppression and TLR8 potentiation. This strongly supports keeping these outcomes distinct rather than collapsing them into a single immune-safety or toxicity label.

### Dose-response and censoring

**61. Sebaugh (2011), Pharmaceutical Statistics — [“Guidelines for accurate EC50/IC50 estimation”](https://doi.org/10.1002/pst.426).**  
Sebaugh distinguishes relative and absolute half-maximal concentrations and explains the experimental conditions required for defensible estimation. If a concentration-response curve does not establish the relevant crossing or plateaus, forcing a precise potency estimate can create misleading labels.

**62. La, Nicholson, Haneef, Kang and Minh (2023), Journal of Medicinal Chemistry — [“Inclusion of Control Data in Fits to Concentration–Response Curves Improves Estimates of Half-Maximal Concentrations”](https://doi.org/10.1021/acs.jmedchem.3c00107).**  
The authors jointly model control and concentration-response data to improve estimation of half-maximal concentrations, especially for incomplete curves. This supports retaining raw controls and curve information when available rather than treating a derived IC50 as an error-free observation.

**63. Karlova, Kabra, de Souza and Paige (2026), UAI — [“COBALT: Censored Optimization and Bayesian Active Learning Techniques”](https://proceedings.mlr.press/v337/karlova26a.html).**  
COBALT develops Bayesian active learning and optimization for censored observations using an appropriate likelihood and information-based acquisition. It is a relevant extension if your source assays genuinely contain detection limits or clipped outcomes, but censor-aware acquisition is unnecessary merely because an efficacy variable is expressed between 0 and 100%.

**64. Kaplan and Meier (1958), Journal of the American Statistical Association — [“Nonparametric Estimation from Incomplete Observations”](https://doi.org/10.1080/01621459.1958.10501452).**  
This foundational paper estimates event-time distributions in the presence of censoring. Its relevance to your label-saving analysis is conceptual: a run that never reaches a performance threshold within the allowed budget has an unobserved attainment budget, not a known attainment at the final checkpoint.

### Keep four different problems separate

| Situation | Statistical interpretation | Appropriate treatment |
|---|---|---|
| Activity reported as “below detection limit” | Left-censored measurement | Preserve the limit and use a censored likelihood if modeling it |
| IC50 reported as “greater than maximum tested concentration” | Right-censored potency | Preserve the inequality; do not replace it with an exact IC50 |
| Acquisition run never reaches the target score | Budget-to-attainment censored at the final budget | Report non-attainment and use a clearly defined censored/restricted analysis |
| Measurement absent because of QC failure | Missing outcome; mechanism may be informative | Record the reason; do not silently reinterpret as low efficacy |

For threshold attainment, report the fraction reaching the threshold and the budget distribution among all runs with appropriate treatment of non-attainment. If scores are observed only at discrete checkpoints, define whether the event is **first observed crossing** or an unobserved continuous-budget crossing; those are different estimands. Survival-analysis terminology can help, but its assumptions and the pairing between acquisition methods still need to be respected. [Kaplan and Meier](https://doi.org/10.1080/01621459.1958.10501452).

A future wet-lab study would need prespecified candidates and comparators, biological replication, appropriate negative and positive controls, dose and timing specifications, and separate measurements of intended activity and undesirable effects. Independent reagents or rescue experiments would be needed for stronger mechanism claims. These are requirements for a future validation study, **not missing evidence that your current retrospective benchmark should pretend to supply**. [Echeverri et al.](https://doi.org/10.1038/nmeth1006-777), [Jackson et al.](https://doi.org/10.1038/nbt831).

## 7. How your results align with the literature

### A. Where the evidence agrees

**A modest positive acquisition effect is plausible.** Your reported normalized AULC difference, \(+0.0095\) with 95% CI \([+0.0043,+0.0146]\), is consistent with literature showing conditional, sometimes modest benefits from uncertainty-based molecular acquisition. The contribution is strengthened by reporting effect size and uncertainty rather than only a winner. [Yin et al.](https://doi.org/10.1186/s13321-023-00753-5).

**No established label saving is not a contradiction.** Average predictive performance, threshold attainment, and high-value candidate discovery are different objectives. Published molecular work finds that gains depend on the objective, and general prediction can remain competitive under random acquisition even when targeted search benefits substantially. [Ghosh et al.](https://doi.org/10.1063/5.0229834), [Gorantla et al.](https://doi.org/10.1021/acs.jcim.4c00220).

**No established uncertainty advantage over diversity is informative.** Diversity has a substantial methodological basis, and the geometry of GP posterior uncertainty can overlap with coverage objectives. Your result is compatible with that explanation, although a mechanistic analysis is needed before attributing the outcome to it. [Sener and Savarese](https://arxiv.org/abs/1708.00489), [Rasmussen and Williams](https://gaussianprocess.org/gpml/chapters/RW2.pdf).

**Mixed PPO comparisons are credible.** Molecular optimization benchmarks repeatedly show that algorithmic complexity does not guarantee superiority over established search methods. A well-controlled mixed result is more informative than presenting a favorable reward trajectory without matched heuristic comparisons. [PMO](https://arxiv.org/abs/2206.12411), [Tripp and Hernández-Lobato](https://arxiv.org/abs/2310.09267).

### B. Where your results qualify broader optimism

Your findings would qualify broad statements such as “uncertainty sampling reduces experimental cost” or “RNA foundation models solve low-data oligo prediction.” The published evidence is more conditional: acquisition depends on initialization and uncertainty quality, while representation improvements depend on architecture, endpoint, and adaptation. [Hacohen et al.](https://proceedings.mlr.press/v162/hacohen22a.html), [Hirschfeld et al.](https://doi.org/10.1021/acs.jcim.0c00502), [OligoFormer](https://doi.org/10.1093/bioinformatics/btae577).

Your lack of demonstrated target-gene generalization also restricts the deployment interpretation. It does not invalidate the within-protocol acquisition result; it means that the result concerns the tested pool and split rather than a general ability to design effective siRNAs for unseen genes. Split-dependent interpretation is standard in molecular benchmarking. [MoleculeNet](https://doi.org/10.1039/C7SC02664A), [Yang et al.](https://doi.org/10.1021/acs.jcim.9b00237).

## 8. Literature gaps your work can reasonably address

I would frame these as **contributions of your evaluation**, not unverified “first-ever” claims.

1. **A controlled oligonucleotide acquisition comparison.** Much of the oligo literature evaluates predictive models, while your primary question concerns which measured labels to reveal sequentially under a fixed budget.

2. **Separation of three commonly conflated outcomes.** You distinguish improvement over random in integrated prediction performance, improvement over diversity, and evidence of fewer labels to reach a target.

3. **A reproducible negative-result boundary.** Reporting where the method does not establish an advantage—label savings, diversity comparisons, and target-gene generalization—helps delimit the positive result.

4. **An auditable retrospective protocol.** Versioned measurements, fixed split assignments, explicit acquisition histories, and restricted access to unrevealed labels can make the experimental claim inspectable.

5. **Endpoint-specific secondary evaluation.** Separate efficacy, neurotoxicity, and immune endpoints avoid presenting heterogeneous assays as a single therapeutic utility.

6. **A design-environment evaluation with honest heuristic comparisons.** The PPO component can contribute an environment and comparative analysis without being used as evidence of experimentally validated molecular improvement.

The first four are the strongest basis for the paper’s central story. The secondary endpoints and PPO environment should remain clearly subordinate unless they have equally strong experimental support.

## 9. Claims reviewers may challenge

| Potential claim | Likely objection | Defensible wording and relevant sources |
|---|---|---|
| “Active learning reduces the labels needed for siRNA prediction.” | Your label-saving analysis is not significant | “Uncertainty acquisition improved normalized AULC at matched budgets; label savings were not established.” [Ghosh](https://doi.org/10.1063/5.0229834) |
| “Uncertainty is better than diversity.” | Your direct comparison does not establish this | Report the effect and interval; avoid superiority or equivalence claims. [Lakens](https://doi.org/10.1177/1948550617697177) |
| “The method generalizes to new targets.” | Sequence-oriented splitting is not target holdout | Restrict the claim to the tested protocol; report target holdout separately. [MoleculeNet](https://doi.org/10.1039/C7SC02664A), [DataSAIL](https://doi.org/10.1038/s41467-025-58606-8) |
| “Forty seeds establish robustness.” | Seeds do not sample all sources of biological variation | “Robust across the tested acquisition initializations,” with conditional uncertainty stated. [Bouthillier](https://proceedings.mlsys.org/paper_files/paper/2021/hash/0184b0cd3cfb185989f858a1d9f5c1eb-Abstract.html) |
| “The whole study was preregistered.” | Only seeds or some analyses may have been locked | Identify exactly what was registered and when. [Nosek](https://doi.org/10.1073/pnas.1708274114) |
| “A foundation model should outperform one-hot.” | Representation benefits are task-dependent | Treat this as a tested hypothesis; distinguish frozen from adapted models. [BEACON](https://arxiv.org/abs/2406.10391), [OligoFormer](https://doi.org/10.1093/bioinformatics/btae577) |
| “PPO discovers better molecules.” | Higher surrogate reward is not measured efficacy | “PPO optimizes the specified computational objective, with mixed heuristic comparisons.” [PMO](https://arxiv.org/abs/2206.12411), [Brookes](https://proceedings.mlr.press/v97/brookes19a.html) |
| “Control-model disagreement proves exploitation.” | Predictors can disagree even before optimization | Present disagreement as a diagnostic and inspect baseline agreement. [Langevin](https://doi.org/10.1186/s13321-022-00601-y) |
| “Toxicity and TLR results establish safety.” | Assays measure different, context-specific outcomes | Name each endpoint, assay, and direction independently. [Hagedorn](https://doi.org/10.1089/nat.2021.0071), [Alharbi](https://doi.org/10.1093/nar/gkaa523) |
| “Non-significance shows no meaningful difference.” | Absence of evidence is not equivalence | Report uncertainty; use a prespecified equivalence margin only if justified. [Lakens](https://doi.org/10.1177/1948550617697177) |

## 10. The most worthwhile additions to your current analysis

These are ordered by how much they would clarify the existing result, rather than by architectural novelty.

**First: make the paired effect visible.** Include paired per-seed AULC differences, the aggregate interval, and budget-specific difference curves. This reveals whether the mean gain is consistent or driven by a subset of favorable initializations.

**Second: quantify how conditional the result is.** Clearly separate acquisition-seed variability from outer-split variability. If feasible, add a limited, explicitly exploratory sensitivity analysis over additional outer splits or target holdouts without changing the registered primary result.

**Third: test the uncertainty-versus-coverage explanation.** Report acquisition-rank agreement, selected-set overlap, sequence coverage, and within-batch redundancy for uncertainty and diversity. This can turn an inconclusive superiority comparison into a useful mechanistic observation.

**Fourth: audit GP noise and hyperparameter handling.** The closest GP molecular benchmark shows that noise settings can change the comparison with random. Document which labels inform each fit and whether hyperparameters are fixed or re-estimated; a restrained sensitivity analysis is more informative here than adding a large model solely for novelty. [Ghosh et al.](https://doi.org/10.1063/5.0229834).

**Fifth: make threshold non-attainment explicit.** Report the fraction of runs reaching each prespecified threshold and avoid calculating label savings only among successful runs. A failure-aware analysis is particularly important because your current evidence does not establish label savings.

**Sixth: keep any new representation or hybrid acquisition experiment exploratory.** Frozen embeddings, LoRA, or a diversity-adjusted uncertainty rule are reasonable extensions, but they should not displace the clean confirmatory comparison or be selected using the final test set.

### Manuscript-ready related-work paragraph

> Oligonucleotide efficacy prediction has progressed from sequence and thermodynamic rules to regularized statistical models, neural architectures, and pretrained RNA representations. Early work demonstrated that sequence-based predictors could estimate siRNA silencing activity, while subsequent studies incorporated chemical modifications and contextual information. However, reported performance depends on experimental provenance, endpoint definition, and evaluation partition, limiting direct comparisons across datasets and models. Our study addresses a complementary question: whether sequential selection of measured labels improves predictive performance relative to random acquisition under a fixed retrospective benchmark protocol. [Reynolds et al.](https://doi.org/10.1038/nbt936), [Huesken et al.](https://doi.org/10.1038/nbt1118), [Vert et al.](https://doi.org/10.1186/1471-2105-7-520), [OligoFormer](https://doi.org/10.1093/bioinformatics/btae577).

### Manuscript-ready discussion paragraph

> Under the evaluated Huesken protocol, uncertainty-based acquisition improved normalized learning-curve area relative to random acquisition by 0.0095, with a 95% confidence interval of 0.0043–0.0146 across 40 preregistered seeds. This result supports a modest improvement in predictive performance over the evaluated budget range, but does not establish a reduction in labels required to reach a target performance, superiority over diversity-based acquisition, or generalization to unseen target genes. These distinctions are consistent with molecular active-learning studies showing that acquisition benefits depend on the learning objective, initialization, and uncertainty model. The secondary design experiments similarly characterize optimization under computational surrogates and do not establish experimentally validated efficacy or PPO superiority. [Ghosh et al.](https://doi.org/10.1063/5.0229834), [Yin et al.](https://doi.org/10.1186/s13321-023-00753-5), [PMO](https://arxiv.org/abs/2206.12411).

## 11. BibTeX

The entries below cover all 64 numbered sources. Long author lists use BibTeX’s `and others`; replace those with publisher-exported full lists if your venue requires them. Preprints are explicitly identified. Renz’s record has a 2019 issue year and 2020 online publication, noted in its entry.

```bibtex
@article{reynolds2004rational,
  author = {Reynolds, Angela and Leake, Devin and Boese, Queta and Scaringe, Stephen and Marshall, William S. and Khvorova, Anastasia},
  title = {Rational siRNA design for RNA interference},
  journal = {Nature Biotechnology},
  year = {2004},
  volume = {22},
  pages = {326--330},
  doi = {10.1038/nbt936}
}

@article{huesken2005design,
  author = {Huesken, Dieter and Lange, Joerg and Mickanin, Craig and others},
  title = {Design of a genome-wide siRNA library using an artificial neural network},
  journal = {Nature Biotechnology},
  year = {2005},
  volume = {23},
  pages = {995--1001},
  doi = {10.1038/nbt1118}
}

@article{vert2006accurate,
  author = {Vert, Jean-Philippe and Foveau, Nicolas and Lajaunie, Christian and Vandenbrouck, Yves},
  title = {An accurate and interpretable model for siRNA efficacy prediction},
  journal = {BMC Bioinformatics},
  year = {2006},
  volume = {7},
  pages = {520},
  doi = {10.1186/1471-2105-7-520}
}

@article{ichihara2007thermodynamic,
  author = {Ichihara, Masatoshi and Murakumo, Yoshiki and Masuda, Akio and others},
  title = {Thermodynamic instability of siRNA duplex is a prerequisite for dependable prediction of siRNA activities},
  journal = {Nucleic Acids Research},
  year = {2007},
  volume = {35},
  pages = {e123},
  doi = {10.1093/nar/gkm699}
}

@article{han2018sirna,
  author = {Han, Ye and He, Fei and Chen, Yongbing and Liu, Yuanning and Yu, Helong},
  title = {SiRNA silencing efficacy prediction based on a deep architecture},
  journal = {BMC Genomics},
  year = {2018},
  volume = {19},
  pages = {669},
  doi = {10.1186/s12864-018-5028-8}
}

@article{bai2024oligoformer,
  author = {Bai, Yilan and Zhong, Haochen and Wang, Taiwei and Lu, Zhi John},
  title = {{OligoFormer}: an accurate and robust prediction method for siRNA design},
  journal = {Bioinformatics},
  year = {2024},
  volume = {40},
  number = {10},
  pages = {btae577},
  doi = {10.1093/bioinformatics/btae577}
}

@article{dar2016sirnamod,
  author = {Dar, Showkat Ahmad and Thakur, Anamika and Qureshi, Abid and Kumar, Manoj},
  title = {siRNAmod: A database of experimentally validated chemically modified siRNAs},
  journal = {Scientific Reports},
  year = {2016},
  volume = {6},
  pages = {20031},
  doi = {10.1038/srep20031}
}

@article{sciabola2021pfred,
  author = {Sciabola, Simone and Xi, Hualin and Cruz, Dario and others},
  title = {{PFRED}: A computational platform for siRNA and antisense oligonucleotides design},
  journal = {PLOS ONE},
  year = {2021},
  volume = {16},
  pages = {e0238753},
  doi = {10.1371/journal.pone.0238753}
}

@article{hwang2024asoptimizer,
  author = {Hwang, Gyeongjo and Kwon, Mincheol and Seo, Dongjin and others},
  title = {{ASOptimizer}: Optimizing antisense oligonucleotides through deep learning for {IDO1} gene regulation},
  journal = {Molecular Therapy Nucleic Acids},
  year = {2024},
  volume = {35},
  number = {2},
  pages = {102186},
  doi = {10.1016/j.omtn.2024.102186}
}

@article{kang2025asoptimizer,
  author = {Kang, Seokjun and Lee, Daehwan and Hwang, Gyeongjo and Lee, Kiwon and Kang, Mingeun},
  title = {{ASOptimizer}: optimizing chemical diversity of antisense oligonucleotides through deep learning},
  journal = {Nucleic Acids Research},
  year = {2025},
  volume = {53},
  number = {W1},
  pages = {W39--W44},
  doi = {10.1093/nar/gkaf392}
}

@inproceedings{rotrattanadumrong2025oligogym,
  author = {Rotrattanadumrong, Rachapun and De Donno, Carlo},
  title = {{OligoGym}: Curated Datasets and Benchmarks for Oligonucleotide Drug Discovery},
  booktitle = {Advances in Neural Information Processing Systems, Datasets and Benchmarks Track},
  year = {2025},
  url = {https://proceedings.neurips.cc/paper_files/paper/2025/file/4927dd556ff6e49671e3a77ac1f12487-Paper-Datasets_and_Benchmarks_Track.pdf}
}

@article{hill2026accurately,
  author = {Hill, Barney and Jaques, Maisie R. and Nair, Remya R. and Whiffin, Nicola and Wood, Matthew J. A. and Sanders, Stephan J. and Oliver, Peter L. and Hill, Alyssa C. and Rinaldi, Carlo},
  title = {Accurately modeling {RNase H}-mediated antisense oligonucleotide efficacy},
  journal = {Molecular Therapy Nucleic Acids},
  year = {2026},
  volume = {37},
  number = {3},
  pages = {103004},
  doi = {10.1016/j.omtn.2026.103004}
}

@book{rasmussen2006gpml,
  author = {Rasmussen, Carl Edward and Williams, Christopher K. I.},
  title = {Gaussian Processes for Machine Learning},
  publisher = {MIT Press},
  year = {2006},
  url = {https://gaussianprocess.org/gpml/}
}

@misc{houlsby2011bald,
  author = {Houlsby, Neil and Husz{\'a}r, Ferenc and Ghahramani, Zoubin and Lengyel, M{\'a}t{\'e}},
  title = {Bayesian Active Learning for Classification and Preference Learning},
  year = {2011},
  eprint = {1112.5745},
  archivePrefix = {arXiv},
  note = {Preprint},
  url = {https://arxiv.org/abs/1112.5745}
}

@inproceedings{sener2018coreset,
  author = {Sener, Ozan and Savarese, Silvio},
  title = {Active Learning for Convolutional Neural Networks: A Core-Set Approach},
  booktitle = {International Conference on Learning Representations},
  year = {2018},
  url = {https://arxiv.org/abs/1708.00489}
}

@inproceedings{kirsch2019batchbald,
  author = {Kirsch, Andreas and van Amersfoort, Joost and Gal, Yarin},
  title = {{BatchBALD}: Efficient and Diverse Batch Acquisition for Deep Bayesian Active Learning},
  booktitle = {Advances in Neural Information Processing Systems},
  year = {2019},
  url = {https://arxiv.org/abs/1906.08158}
}

@inproceedings{ash2020badge,
  author = {Ash, Jordan T. and Zhang, Chicheng and Krishnamurthy, Akshay and Langford, John and Agarwal, Alekh},
  title = {Deep Batch Active Learning by Diverse, Uncertain Gradient Lower Bounds},
  booktitle = {International Conference on Learning Representations},
  year = {2020},
  url = {https://arxiv.org/abs/1906.03671}
}

@inproceedings{hacohen2022budget,
  author = {Hacohen, Guy and Dekel, Avihu and Weinshall, Daphna},
  title = {Active Learning on a Budget: Opposite Strategies Suit High and Low Budgets},
  booktitle = {International Conference on Machine Learning},
  year = {2022},
  url = {https://proceedings.mlr.press/v162/hacohen22a.html}
}

@misc{kirsch2021stochastic,
  author = {Kirsch, Andreas and Farquhar, Sebastian and Atighehchian, Parmida and Jesson, Andrew and Branchaud-Charron, Frederic and Gal, Yarin},
  title = {Stochastic Batch Acquisition: A Simple Baseline for Deep Active Learning},
  year = {2021},
  eprint = {2106.12059},
  archivePrefix = {arXiv},
  note = {Preprint},
  url = {https://arxiv.org/abs/2106.12059}
}

@article{holzmueller2023framework,
  author = {Holzm{\"u}ller, David and Zaverkin, Viktor and K{\"a}stner, Johannes and Steinwart, Ingo},
  title = {A Framework and Benchmark for Deep Batch Active Learning for Regression},
  journal = {Journal of Machine Learning Research},
  year = {2023},
  volume = {24},
  number = {164},
  pages = {1--81},
  url = {https://jmlr.org/papers/v24/22-0937.html}
}

@article{ghosh2025active,
  author = {Ghosh, Kunal and Todorovi{\'c}, Milica and Vehtari, Aki and Rinke, Patrick},
  title = {Active learning of molecular data for task-specific objectives},
  journal = {Journal of Chemical Physics},
  year = {2025},
  volume = {162},
  pages = {014103},
  doi = {10.1063/5.0229834}
}

@article{yin2023evaluating,
  author = {Yin, Tianzhixi and Panapitiya, Gihan and Coda, Elizabeth D. and Saldanha, Emily G.},
  title = {Evaluating uncertainty-based active learning for accelerating the generalization of molecular property prediction},
  journal = {Journal of Cheminformatics},
  year = {2023},
  volume = {15},
  pages = {105},
  doi = {10.1186/s13321-023-00753-5}
}

@article{gorantla2024benchmarking,
  author = {Gorantla, Rohan and Kubincov{\'a}, Al{\v z}beta and Suutari, Benjamin and Cossins, Benjamin P. and Mey, Antonia S. J. S.},
  title = {Benchmarking Active Learning Protocols for Ligand-Binding Affinity Prediction},
  journal = {Journal of Chemical Information and Modeling},
  year = {2024},
  volume = {64},
  pages = {1955--1965},
  doi = {10.1021/acs.jcim.4c00220}
}

@article{vantilborg2024traversing,
  author = {van Tilborg, Derek and Grisoni, Francesca},
  title = {Traversing chemical space with active deep learning for low-data drug discovery},
  journal = {Nature Computational Science},
  year = {2024},
  volume = {4},
  pages = {786--796},
  doi = {10.1038/s43588-024-00697-2}
}

@article{hirschfeld2020uncertainty,
  author = {Hirschfeld, Lior and Swanson, Kyle and Yang, Kevin and Barzilay, Regina and Coley, Connor W.},
  title = {Uncertainty Quantification Using Neural Networks for Molecular Property Prediction},
  journal = {Journal of Chemical Information and Modeling},
  year = {2020},
  volume = {60},
  pages = {3770--3780},
  doi = {10.1021/acs.jcim.0c00502}
}

@article{scalia2020evaluating,
  author = {Scalia, Gabriele and Grambow, Colin A. and Pernici, Barbara and Li, Yi-Pei and Green, William H.},
  title = {Evaluating Scalable Uncertainty Estimation Methods for Deep Learning-Based Molecular Property Prediction},
  journal = {Journal of Chemical Information and Modeling},
  year = {2020},
  volume = {60},
  pages = {2697--2717},
  doi = {10.1021/acs.jcim.9b00975}
}

@inproceedings{farquhar2021bias,
  author = {Farquhar, Sebastian and Gal, Yarin and Rainforth, Tom},
  title = {On Statistical Bias in Active Learning: How and When To Fix It},
  booktitle = {International Conference on Learning Representations},
  year = {2021},
  url = {https://arxiv.org/abs/2101.11665}
}

@article{biswas2021lown,
  author = {Biswas, Surojit and Khimulya, Grigory and Alley, Ethan C. and Esvelt, Kevin M. and Church, George M.},
  title = {Low-N protein engineering with data-efficient deep learning},
  journal = {Nature Methods},
  year = {2021},
  volume = {18},
  pages = {389--396},
  doi = {10.1038/s41592-021-01100-y}
}

@article{nosek2018preregistration,
  author = {Nosek, Brian A. and Ebersole, Charles R. and DeHaven, Alexander C. and Mellor, David T.},
  title = {The preregistration revolution},
  journal = {Proceedings of the National Academy of Sciences},
  year = {2018},
  volume = {115},
  pages = {2600--2606},
  doi = {10.1073/pnas.1708274114}
}

@inproceedings{lueth2023pitfalls,
  author = {L{\"u}th, Carsten T. and Bungert, Till J. and Klein, Lukas and Jaeger, Paul F.},
  title = {Navigating the Pitfalls of Active Learning Evaluation: A Systematic Framework for Meaningful Performance Assessment},
  booktitle = {Advances in Neural Information Processing Systems},
  year = {2023},
  url = {https://arxiv.org/abs/2301.10625}
}

@inproceedings{bouthillier2021variance,
  author = {Bouthillier, Xavier and others},
  title = {Accounting for Variance in Machine Learning Benchmarks},
  booktitle = {Proceedings of Machine Learning and Systems},
  year = {2021},
  volume = {3},
  url = {https://proceedings.mlsys.org/paper_files/paper/2021/hash/0184b0cd3cfb185989f858a1d9f5c1eb-Abstract.html}
}

@inproceedings{agarwal2021precipice,
  author = {Agarwal, Rishabh and Schwarzer, Max and Castro, Pablo Samuel and Courville, Aaron and Bellemare, Marc G.},
  title = {Deep Reinforcement Learning at the Edge of the Statistical Precipice},
  booktitle = {Advances in Neural Information Processing Systems},
  year = {2021},
  url = {https://arxiv.org/abs/2108.13264}
}

@article{demsar2006comparisons,
  author = {Dem{\v s}ar, Janez},
  title = {Statistical Comparisons of Classifiers over Multiple Data Sets},
  journal = {Journal of Machine Learning Research},
  year = {2006},
  volume = {7},
  pages = {1--30},
  url = {https://jmlr.org/papers/v7/demsar06a.html}
}

@article{cawley2010overfitting,
  author = {Cawley, Gavin C. and Talbot, Nicola L. C.},
  title = {On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation},
  journal = {Journal of Machine Learning Research},
  year = {2010},
  volume = {11},
  pages = {2079--2107},
  url = {https://jmlr.org/papers/v11/cawley10a.html}
}

@article{kapoor2023leakage,
  author = {Kapoor, Sayash and Narayanan, Arvind},
  title = {Leakage and the reproducibility crisis in machine-learning-based science},
  journal = {Patterns},
  year = {2023},
  volume = {4},
  pages = {100804},
  doi = {10.1016/j.patter.2023.100804}
}

@article{wu2018moleculenet,
  author = {Wu, Zhenqin and Ramsundar, Bharath and Feinberg, Evan N. and others},
  title = {{MoleculeNet}: a benchmark for molecular machine learning},
  journal = {Chemical Science},
  year = {2018},
  volume = {9},
  pages = {513--530},
  doi = {10.1039/C7SC02664A}
}

@article{yang2019representations,
  author = {Yang, Kevin and Swanson, Kyle and Jin, Wengong and others},
  title = {Analyzing Learned Molecular Representations for Property Prediction},
  journal = {Journal of Chemical Information and Modeling},
  year = {2019},
  volume = {59},
  pages = {3370--3388},
  doi = {10.1021/acs.jcim.9b00237}
}

@article{joeres2025datasail,
  author = {Joeres, Roman and Blumenthal, David B. and Kalinina, Olga V.},
  title = {Data splitting to avoid information leakage with {DataSAIL}},
  journal = {Nature Communications},
  year = {2025},
  volume = {16},
  pages = {3337},
  doi = {10.1038/s41467-025-58606-8},
  note = {See also the 2026 addendum, doi:10.1038/s41467-025-67495-w}
}

@article{saravanan2020bootstrap,
  author = {Saravanan, Varun and Berman, Gordon J. and Sober, Samuel J.},
  title = {Application of the hierarchical bootstrap to multi-level data in neuroscience},
  journal = {Neurons, Behavior, Data Analysis, and Theory},
  year = {2020},
  volume = {3},
  url = {https://pmc.ncbi.nlm.nih.gov/articles/PMC7906290/}
}

@article{lakens2017equivalence,
  author = {Lakens, Dani{\"e}l},
  title = {Equivalence Tests: A Practical Primer for t Tests, Correlations, and Meta-Analyses},
  journal = {Social Psychological and Personality Science},
  year = {2017},
  volume = {8},
  pages = {355--362},
  doi = {10.1177/1948550617697177}
}

@misc{schulman2017ppo,
  author = {Schulman, John and Wolski, Filip and Dhariwal, Prafulla and Radford, Alec and Klimov, Oleg},
  title = {Proximal Policy Optimization Algorithms},
  year = {2017},
  eprint = {1707.06347},
  archivePrefix = {arXiv},
  note = {Preprint},
  url = {https://arxiv.org/abs/1707.06347}
}

@article{olivecrona2017molecular,
  author = {Olivecrona, Marcus and Blaschke, Thomas and Engkvist, Ola and Chen, Hongming},
  title = {Molecular de-novo design through deep reinforcement learning},
  journal = {Journal of Cheminformatics},
  year = {2017},
  volume = {9},
  pages = {48},
  doi = {10.1186/s13321-017-0235-x}
}

@article{zhou2019optimization,
  author = {Zhou, Zhenpeng and Kearnes, Steven and Li, Li and Zare, Richard N. and Riley, Patrick},
  title = {Optimization of Molecules via Deep Reinforcement Learning},
  journal = {Scientific Reports},
  year = {2019},
  volume = {9},
  pages = {10752},
  doi = {10.1038/s41598-019-47148-x},
  note = {See also the 2020 correction, doi:10.1038/s41598-020-66840-x}
}

@article{brown2019guacamol,
  author = {Brown, Nathan and Fiscato, Marco and Segler, Marwin H. S. and Vaucher, Alain C.},
  title = {{GuacaMol}: Benchmarking Models for de Novo Molecular Design},
  journal = {Journal of Chemical Information and Modeling},
  year = {2019},
  volume = {59},
  pages = {1096--1108},
  doi = {10.1021/acs.jcim.8b00839}
}

@inproceedings{gao2022sample,
  author = {Gao, Wenhao and Fu, Tianfan and Sun, Jimeng and Coley, Connor W.},
  title = {Sample Efficiency Matters: A Benchmark for Practical Molecular Optimization},
  booktitle = {Advances in Neural Information Processing Systems, Datasets and Benchmarks Track},
  year = {2022},
  url = {https://arxiv.org/abs/2206.12411}
}

@misc{tripp2023genetic,
  author = {Tripp, Austin and Hern{\'a}ndez-Lobato, Jos{\'e} Miguel},
  title = {Genetic algorithms are strong baselines for molecule generation},
  year = {2023},
  eprint = {2310.09267},
  archivePrefix = {arXiv},
  note = {Preprint},
  url = {https://arxiv.org/abs/2310.09267}
}

@article{renz2019failure,
  author = {Renz, Philipp and Van Rompaey, Dries and Wegner, J{\"o}rg Kurt and Hochreiter, Sepp and Klambauer, G{\"u}nter},
  title = {On failure modes in molecule generation and optimization},
  journal = {Drug Discovery Today: Technologies},
  year = {2019},
  volume = {32--33},
  pages = {55--63},
  doi = {10.1016/j.ddtec.2020.09.003},
  note = {Issue year 2019; published online 2020}
}

@article{langevin2022explaining,
  author = {Langevin, Maxime and Vuilleumier, Rodolphe and Bianciotto, Marc},
  title = {Explaining and avoiding failure modes in goal-directed generation of small molecules},
  journal = {Journal of Cheminformatics},
  year = {2022},
  volume = {14},
  pages = {20},
  doi = {10.1186/s13321-022-00601-y}
}

@inproceedings{brookes2019conditioning,
  author = {Brookes, David and Park, Hahnbeom and Listgarten, Jennifer},
  title = {Conditioning by adaptive sampling for robust design},
  booktitle = {International Conference on Machine Learning},
  year = {2019},
  url = {https://proceedings.mlr.press/v97/brookes19a.html}
}

@inproceedings{trabucco2021conservative,
  author = {Trabucco, Brandon and Kumar, Aviral and Geng, Xinyang and Levine, Sergey},
  title = {Conservative Objective Models for Effective Offline Model-Based Optimization},
  booktitle = {International Conference on Machine Learning},
  year = {2021},
  url = {https://proceedings.mlr.press/v139/trabucco21a.html}
}

@article{gao2020synthesizability,
  author = {Gao, Wenhao and Coley, Connor W.},
  title = {The Synthesizability of Molecules Proposed by Generative Models},
  journal = {Journal of Chemical Information and Modeling},
  year = {2020},
  volume = {60},
  pages = {5714--5723},
  doi = {10.1021/acs.jcim.0c00174}
}

@misc{chen2022rnafm,
  author = {Chen, Jiayang and Hu, Zhihang and Sun, Siqi and others},
  title = {Interpretable {RNA} Foundation Model from Unannotated Data for Highly Accurate {RNA} Structure and Function Predictions},
  year = {2022},
  eprint = {2204.00300},
  archivePrefix = {arXiv},
  note = {Preprint},
  url = {https://arxiv.org/abs/2204.00300}
}

@article{penic2025rinalmo,
  author = {Peni{\'c}, Rafael Josip and Vla{\v s}i{\'c}, Tin and Huber, Roland G. and Wan, Yue and {\v S}iki{\'c}, Mile},
  title = {{RiNALMo}: general-purpose {RNA} language models can generalize well on structure prediction tasks},
  journal = {Nature Communications},
  year = {2025},
  volume = {16},
  pages = {5671},
  doi = {10.1038/s41467-025-60872-5}
}

@inproceedings{ren2024beacon,
  author = {Ren, Yuchen and Chen, Zhiyuan and Qiao, Lifeng and others},
  title = {{BEACON}: Benchmark for Comprehensive {RNA} Tasks and Language Models},
  booktitle = {Advances in Neural Information Processing Systems, Datasets and Benchmarks Track},
  year = {2024},
  url = {https://arxiv.org/abs/2406.10391}
}

@article{chu2024utr,
  author = {Chu, Yanyi and Yu, Dan and Li, Yupeng and Huang, Kaixuan and Shen, Yue and Cong, Le and Zhang, Jason and Wang, Mengdi},
  title = {A 5-prime {UTR} language model for decoding untranslated regions of {mRNA} and function predictions},
  journal = {Nature Machine Intelligence},
  year = {2024},
  volume = {6},
  pages = {449--460},
  doi = {10.1038/s42256-024-00823-9}
}

@inproceedings{hu2022lora,
  author = {Hu, Edward J. and Shen, Yelong and Wallis, Phillip and Allen-Zhu, Zeyuan and Li, Yuanzhi and Wang, Shean and Wang, Lu and Chen, Weizhu},
  title = {{LoRA}: Low-Rank Adaptation of Large Language Models},
  booktitle = {International Conference on Learning Representations},
  year = {2022},
  url = {https://openreview.net/forum?id=nZeVKeeFYf9}
}

@article{jackson2003offtarget,
  author = {Jackson, Aimee L. and Bartz, Steven R. and Schelter, Janell and others},
  title = {Expression profiling reveals off-target gene regulation by {RNAi}},
  journal = {Nature Biotechnology},
  year = {2003},
  volume = {21},
  pages = {635--637},
  doi = {10.1038/nbt831}
}

@article{echeverri2006falsepositives,
  author = {Echeverri, Christophe J. and others},
  title = {Minimizing the risk of reporting false positives in large-scale {RNAi} screens},
  journal = {Nature Methods},
  year = {2006},
  volume = {3},
  pages = {777--779},
  doi = {10.1038/nmeth1006-777},
  note = {Commentary}
}

@article{hagedorn2022neurotoxicity,
  author = {Hagedorn, Peter H. and Brown, Jeffrey M. and Easton, Amy and others},
  title = {Acute Neurotoxicity of Antisense Oligonucleotides After Intracerebroventricular Injection Into Mouse Brain Can Be Predicted from Sequence Features},
  journal = {Nucleic Acid Therapeutics},
  year = {2022},
  volume = {32},
  pages = {151--162},
  doi = {10.1089/nat.2021.0071}
}

@article{alharbi2020tlr,
  author = {Alharbi, Arwaf S. and Garcin, Aur{\'e}lie J. and Lennox, Kim A. and others},
  title = {Rational design of antisense oligonucleotides modulating the activity of {TLR7/8} agonists},
  journal = {Nucleic Acids Research},
  year = {2020},
  volume = {48},
  pages = {7052--7065},
  doi = {10.1093/nar/gkaa523}
}

@article{sebaugh2011guidelines,
  author = {Sebaugh, J. L.},
  title = {Guidelines for accurate {EC50/IC50} estimation},
  journal = {Pharmaceutical Statistics},
  year = {2011},
  volume = {10},
  pages = {128--134},
  doi = {10.1002/pst.426}
}

@article{la2023control,
  author = {La, Van Ngoc Thuy and Nicholson, Stanley and Haneef, Amna and Kang, Lulu and Minh, David D. L.},
  title = {Inclusion of Control Data in Fits to Concentration--Response Curves Improves Estimates of Half-Maximal Concentrations},
  journal = {Journal of Medicinal Chemistry},
  year = {2023},
  volume = {66},
  pages = {12751--12761},
  doi = {10.1021/acs.jmedchem.3c00107}
}

@inproceedings{karlova2026cobalt,
  author = {Karlova, Andrea and Kabra, Rishabh and de Souza, Daniel Augusto and Paige, Brooks},
  title = {{COBALT}: Censored Optimization and Bayesian Active Learning Techniques},
  booktitle = {Proceedings of the 42nd Conference on Uncertainty in Artificial Intelligence},
  series = {Proceedings of Machine Learning Research},
  volume = {337},
  pages = {2713--2743},
  year = {2026},
  url = {https://proceedings.mlr.press/v337/karlova26a.html}
}

@article{kaplan1958nonparametric,
  author = {Kaplan, E. L. and Meier, Paul},
  title = {Nonparametric Estimation from Incomplete Observations},
  journal = {Journal of the American Statistical Association},
  year = {1958},
  volume = {53},
  pages = {457--481},
  doi = {10.1080/01621459.1958.10501452}
}
```

## Addendum: additional precedent and methodology (November 16, 2026)

This addendum extends the review with papers identified in the OligoAL Bedrock
note. It is deliberately appended so the original review text and its existing
claims remain unchanged. The references below sharpen the positioning of OligoAL:
the benchmark form, retrospective replay, policy-comparison statistics, and
selective-label limitations already have substantial precedent. The defensible
OligoAL contribution is therefore narrower: an ASO-specific decision environment
with linked assay structure, concentration-level choices, explicit eligibility,
and (if recovered and verified) an exact-planning reference.

### Additional benchmark precedent

**GeneDisco: A Benchmark for Experimental Design in Drug Discovery** (Mehrjou et
al., ICLR 2022) is the closest missing benchmark citation. GeneDisco evaluates
batch active-learning policies on real interventional genetic experiments, with
curated tasks, common metrics, and baseline implementations. OligoAL should not
claim to be the first benchmark for active experimental design in drug discovery.
Its narrower distinction is the oligonucleotide modality, linked assay choices,
dose-level decisions, and assay-eligibility/provenance contract.

**LabBench: Can AI Agents Decide What Experiment to Run Next?** (Reilly, Damon,
and McKinnon, 2026 preprint) is a relevant retrospective decision benchmark. It
constructs held-out tasks from real wet-lab records, withholds the historical
decision, and scores an agent against a rubric tied to the recorded experiment.
OligoAL differs in its measured-hit and budgeted-acquisition estimands, but should
not claim that retrospective replay with hidden outcomes is unprecedented. The
current Qwen comparison is an interface study unless all policies receive the
same information and legal action set.

**DiscoBAX**, **Neural Design for Genetic Perturbation Experiments**, and later
work on temporal-difference acquisition for perturbation discovery extend the
GeneDisco line. They are useful evidence that learned acquisition and intervention
set discovery are established methodological areas rather than OligoAL's algorithmic
novelty.

### Active-search and policy-comparison foundations

**Efficient Nonmyopic Active Search** (Jiang et al., ICML 2017, PMLR 70:
1714--1723) proves a worst-case hardness result for active search and introduces
a budget-aware nonmyopic policy. The theorem supports describing exact dynamic
programming as a planning-headroom reference; it does not by itself predict that
greedy will win on an ASO task. Report modeled headroom as a domain-specific
measurement, not as a new theorem.

**Bayesian Optimal Active Search and Surveying** (Garnett et al., 2012) provides
the Bayesian decision-theoretic foundation for rare-hit search under a label
budget. **Nonmyopic Multifidelity Active Search** (Nguyen, Modiri, and Garnett,
ICML 2021, PMLR 139:8109--8118) is especially close to OligoAL's source-prior
plus measured-assay structure: it formalizes cheap noisy surrogates alongside an
expensive oracle and derives a budget-aware policy. These papers make the
prediction-versus-assay distinction part of an established lineage.

**Amortized Nonmyopic Active Search via Deep Imitation Learning** and related
learned-policy work weaken any claim that PPO or a learned acquisition policy is
itself novel. OligoAL's contribution should be the biological task and audit
contract, followed by an empirical comparison against strong simple controls.

### Statistical reporting for stochastic policy comparisons

**Deep Reinforcement Learning at the Edge of the Statistical Precipice**
(Agarwal et al., NeurIPS 2021) and the accompanying `rliable` library show that
point estimates over a small number of runs can reverse algorithm rankings.
For OligoAL, add individual-run records, per-target paired effects, an
interquartile mean as a robustness summary, stratified bootstrap intervals, and
probability-of-improvement plots. These summaries complement the predeclared
target-macro mean; they do not create independent targets from repeated seeds.

**Ji et al.** (WACV 2023) document hardware and initialization effects in deep
active-learning comparisons. **CDALBench** (Werner et al., 2024) uses repeated
evaluations to examine whether an acquisition method is consistently best. These
references support freezing hardware, software, policy seeds, replay seeds,
checkpoint selection, and action spaces before final evaluation.

The OligoAL comparison must separate policies with different observation or
action menus. A Qwen policy given six choices cannot be placed in the same
algorithm leaderboard as a policy selecting from the full eligible pool. Keep
that result as an interface or agent study and report matched-action comparisons
separately.

### Retrospective replay, support, and selective labels

Offline-policy-evaluation terminology makes the central limitation precise.
**Doubly Robust Policy Evaluation and Learning** (Dudik, Langford, and Li,
ICML 2011) combines an outcome model with logged action propensities. It is
relevant only when logging probabilities and action support are available. Patent
screening records are often close to deterministic expert logs, so actions never
performed have no recoverable outcomes. No estimator can repair absent support.

**The Selective Labels Problem** (Lakkaraju et al., 2017/2018) provides the
broader missing-outcome framing: labels are observed conditional on an earlier
decision. OligoAL should state that its direct replay estimand is identifiable
only inside a fully measured recorded candidate pool. Claims about new molecules,
unperformed assay contexts, or prospective laboratory savings require new evidence.

**Retrospective Bayesian optimization and active-learning replay** in materials,
drug-discovery, and nucleic-acid settings provide precedent for evaluating a policy
against a fully labeled held-out pool. The protocol must still preserve the
behavior-policy support boundary and disclose advancement and patent-selection
bias.

**Farquhar, Gal, and Rainforth** (ICLR 2021) analyze the distribution shift caused
by active acquisition and propose PURE/LURE corrections. This is relevant to
learning-curve interpretation: an actively acquired training set need not estimate
the population distribution, and correction can help in underparameterized models
but may not help in overparameterized ones. Treat it as a sensitivity analysis,
not an automatic correction.

**Lowell, Lipton, and Wallace** (EMNLP-IJCNLP 2019) show that retrospective
active-learning gains often fail to generalize across models and tasks. This is a
core limitation for OligoAL: a gain in a historical replay does not establish a
prospective assay benefit. **Lüth et al.** (NeurIPS 2023) catalogue active-learning
evaluation pitfalls and emphasize comparisons against simple, cheap alternatives.

### Data and benchmark documentation

**Datasheets for Datasets** (Gebru et al., Communications of the ACM 2021) should
guide the derived decision-benchmark documentation. The OligoAL datasheet should
record motivation, source patent selection, assay and chemistry attrition,
duplicate/near-duplicate handling, missing context, recommended uses, prohibited
interpretations, and unknown provenance. “Unknown to the authors” is preferable to
an inferred answer.

**Pre-registration for Predictive Modeling** (Hofman et al., 2023) and
**Preregistration for Experiments with AI Agents** (Vaccaro, PMLR 306, 2026)
support freezing target roles, model/policy selection, action menus, thresholds,
budgets, primary contrasts, secondary-test families, and stopping rules before
final outcomes. The existing Huesken protocol's separation of exploratory and
fresh-seed analyses is a useful project precedent.

**Volk and Abolhasani** (Nature Communications 2024) argue that autonomous-lab
resource claims should report material or measurement use per experiment rather
than only aggregate savings. For OligoAL, report concentrations per ASO, assay
panels per campaign, QC failures, and the denominator used for every percentage.
A retrospective reduction in counted measurements is not a laboratory-cost
estimate unless the cost mapping is independently specified.

### Oligonucleotide prediction and design precedents

The ASO Atlas/OligoAI record should be represented accurately. Hill et al.'s
2026 *Molecular Therapy: Nucleic Acids* paper introduced the ASO Atlas used to
train OligoAI and reported model-guided experimental validation. ASO Atlas 2.0 is
a separate versioned release and manuscript extension. The two should not be
presented as unrelated contributions, but the Atlas 2.0 data release can be cited
separately when its versioned counts are used.

**ASOptimizer** (Hwang et al., *Molecular Therapy: Nucleic Acids*, 2024) and
**OligoWalk** are important comparison points because OligoAI reports results
against them. **PFRED** (Sciabola et al., PLOS ONE 2020) explicitly frames
siRNA/ASO design as enumerate-then-select. These references make clear that
candidate ranking and candidate-set selection predate OligoAL; the project adds a
budgeted measured-outcome acquisition formulation.

### Censored potency and dose-response methods to add before E2/E4

The potency sections need a dedicated censored-measurement review before they are
headline evidence. **COBALT** (Karlova et al., UAI 2026, PMLR 337:2713--2743)
provides a censored-normal likelihood and acquisition treatment. **C-BALD**
(Bayesian Active Learning for Censored Regression) is a related censored-regression
acquisition reference. **Turnbull's nonparametric estimator** (1976) is relevant
when IC50 values are interval-censored rather than exactly observed. For bounded
IC50 values, preserve lower/upper bounds and fit-status metadata; do not replace a
bound with its censoring threshold.

**Optimal serial dilutions designs for drug discovery experiments** (Donev and
Tobias, 2011) supplies the design-of-concentration precedent. **Inclusion of
Control Data in Fits to Concentration--Response Curves Improves Estimates of
Half-Maximal Concentrations** (La et al., 2023) supports retaining control wells
and reporting curve-fit uncertainty. The four-parameter logistic model, fit
constraints, minimum dose support, replicate handling, failed-fit rule, and
classification threshold must all be frozen before comparing stopping policies.

For E4, report measurement count and decision reliability jointly. A result such
as zero disagreements among resolved historical panels is not an independent
biological validation. Keep unresolved panels in the denominator and report QC
failures explicitly. If a future live assay can stop at arbitrary times, use
time-uniform confidence sequences (Howard et al., 2021) or an explicitly validated
group-sequential procedure instead of ordinary fixed-sample intervals checked
repeatedly.

### Revised positioning paragraph

OligoAL should state that OligoGym established standardized oligonucleotide
prediction benchmarks; Hill et al. established large-scale ASO efficacy prediction
and model-guided screening; GeneDisco established benchmarked active experimental
design for drug discovery; and LabBench established retrospective wet-lab decision
replay for AI agents. OligoAL's narrower contribution is an auditable ASO assay
decision environment with explicit measured-label access, linked assay and dose
structure, and a comparison of simple, Bayesian, and learned policies under
matched budgets. Any stronger claim requires recovered artifacts and independently
reserved target campaigns.

### Added references

```bibtex
@inproceedings{mehrjou2022genedisco,
  author = {Mehrjou, Arash and Soleymani, Mohammad and Jesson, Andrew and Notin, Pascal and Gal, Yarin and Bauer, Stefan and Schwab, Patrick},
  title = {GeneDisco: A Benchmark for Experimental Design in Drug Discovery},
  booktitle = {International Conference on Learning Representations},
  year = {2022},
  url = {https://arxiv.org/abs/2110.11875}
}

@inproceedings{jiang2017efficient,
  author = {Jiang, Shali and Malkomes, Gustavo and Converse, Geoff and Shofner, Alyssa and Moseley, Benjamin and Garnett, Roman},
  title = {Efficient Nonmyopic Active Search},
  booktitle = {Proceedings of the 34th International Conference on Machine Learning},
  series = {Proceedings of Machine Learning Research},
  volume = {70},
  pages = {1714--1723},
  year = {2017},
  url = {https://proceedings.mlr.press/v70/jiang17d.html}
}

@inproceedings{agarwal2021precipice,
  author = {Agarwal, Rishabh and Schwarzer, Max and Castro, Pablo Samuel and Courville, Aaron and Bellemare, Marc},
  title = {Deep Reinforcement Learning at the Edge of the Statistical Precipice},
  booktitle = {Advances in Neural Information Processing Systems},
  volume = {34},
  year = {2021},
  url = {https://agarwl.github.io/rliable/}
}

@inproceedings{dudik2011doubly,
  author = {Dudik, Miroslav and Langford, John and Li, Lihong},
  title = {Doubly Robust Policy Evaluation and Learning},
  booktitle = {Proceedings of the 28th International Conference on Machine Learning},
  year = {2011},
  url = {https://icml.cc/2011/papers/554_icmlpaper.pdf}
}

@article{gebru2021datasheets,
  author = {Gebru, Timnit and Morgenstern, Jamie and Vecchione, Briana and Vaughan, Jennifer Wortman and Wallach, Hanna and Daume III, Hal and Crawford, Kate},
  title = {Datasheets for Datasets},
  journal = {Communications of the ACM},
  volume = {64},
  number = {12},
  pages = {86--92},
  year = {2021},
  doi = {10.1145/3458723}
}

@article{lowell2019active,
  author = {Lowell, David and Lipton, Zachary C. and Wallace, Byron C.},
  title = {Practical Obstacles to Deploying Active Learning},
  journal = {Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing},
  year = {2019},
  url = {https://aclanthology.org/D19-1223/}
}

@article{farquhar2021active,
  author = {Farquhar, Sebastian and Gal, Yarin and Rainforth, Tom},
  title = {On Statistical Bias in Active Learning},
  journal = {International Conference on Learning Representations},
  year = {2021},
  url = {https://openreview.net/forum?id=6H2DMPW2f0}
}

@article{la2023control,
  author = {La, Van Ngoc Thuy and Nicholson, Stanley and Haneef, Amna and Kang, Lulu and Minh, David D. L.},
  title = {Inclusion of Control Data in Fits to Concentration--Response Curves Improves Estimates of Half-Maximal Concentrations},
  journal = {Journal of Medicinal Chemistry},
  volume = {66},
  pages = {12751--12761},
  year = {2023},
  doi = {10.1021/acs.jmedchem.3c00107}
}

@article{howard2021confidence,
  author = {Howard, Steven R. and Ramdas, Aaditya and McAuliffe, Jon D. and Sekhon, Jasjeet S.},
  title = {Time-Uniform, Nonparametric, Nonasymptotic Confidence Sequences},
  journal = {The Annals of Statistics},
  volume = {49},
  number = {2},
  pages = {1055--1080},
  year = {2021},
  doi = {10.1214/20-AOS1991}
}
```
