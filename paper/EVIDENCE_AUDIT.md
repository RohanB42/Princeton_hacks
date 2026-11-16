# Manuscript evidence and unresolved issues

Internal author working document — **not part of the anonymous submission**.
Prepared November 16, 2026. No new scientific experiment or model fitting was run for this manuscript.

## Issues that remain

1. **Original V3 recovery.** The eight-cohort 3.125 / 3.000 / 2.500 / 2.234375 means, later PPO ablations, original Qwen option-order diagnostics, and MSH3 rescoring are recorded only in the preserved handoff in this checkout. The original later V3 commits, fits, eligible pools and purchase ledgers are unavailable. The current manuscript excludes these historical numerical summaries and retains only the linked-assay task description and evidence limitation. Recover and audit the originals before promoting them to a submission-grade empirical claim. This is separate from V1/V2, whose original report was recovered from the remote-tracking branch.
2. **Molecular biological evaluation.** No independent final groups are certified for the active joint chemistry/assay profile. The eight targets mix training, checkpoint selection and development, with predictor exposure varying. Surrogate improvement does not demonstrate measured efficacy or safety. A fully matched pretraining attribution and total-cost comparison remain open.
3. **Dose-response qualification failed.** All three early methods asserted a class for the one unresolved assessment reference. The 63.8% readout saving is descriptive, not a passed qualified-efficiency result or laboratory cost saving. Preserve the 240-ASO assessment; any repaired rule needs new assessment data.
4. **Reproduction and inference limits.** Three of seven efficacy reproductions remain outside the tolerance. Huesken split seeds share observations; target/patent independence is incomplete; the 600-candidate replay has only two previously exposed targets. No significant label-saving or broad learned-policy superiority is established.
5. **Model assumptions.** Planning results are exact only for the stated finite synthetic model. Its prior, noise, perfect confirmation and direct-confirmation availability differ from V3. Bayesian dose-response confidence is not empirically calibrated. Atlas source-size comparisons change composition and internal validation groups.
6. **Submission completion.** Related Work is complete. The CFP does not specify a separate supplementary-file policy; confirm allowed anonymized supporting files in CMT. The existing AAAI-27 kit is preserved unchanged. The official AAAI author-kit link returns HTTP 403 in this environment, so independent byte-for-byte verification against a fresh download was not possible.

## Claims-to-evidence map

Paths below are repository-relative unless prefixed `paper/`. Committed reports are authoritative for their stated studies; later status summaries are used only where explicitly identified.

| Paper claim / display | Original evidence | Status / scope |
|---|---|---|
| Atlas 295,007 readouts, 430 targets, 606 patents | `data/aso_atlas_2/release/upstream_manifest.json` | Pinned release inventory; not independent experiments |
| Huesken 2,431 / 30 targets; seven-dataset reproduction 4/7 | `docs/updates/2026-11-14-1150-est.md`; `docs/gate1-efficacy-reproduction.md` | Endpoint-specific reproduction, expanded gate incomplete |
| Acquisition +0.0095, CI, p; hybrid +0.0112; label savings 72.5 | `docs/acquisition-comparison.md`, confirmatory seeds 110–149 | Frozen protocol; paired within one dataset; no significant threshold savings |
| Figure 1a | Same confirmatory report | Effect and reported bootstrap interval, not invented raw learning curves |
| Huesken 200-label Ridge .4910, FM-Ridge .3374, frozen head .2801, LoRA .4196; Figure 1b | `docs/updates/2026-11-14-1150-est.md`; protocol `docs/rnafm-lora-comparison.md` | Completed five-seed comparison; descriptive means |
| Atlas 3%/5% Ridge 19.883/19.656, LoRA 22.391/22.340 | `codex/atlas-lora-scaling:docs/research/atlas-rnafm/SCALING-RESULTS.md`, copied verbatim to `paper/evidence/atlas-scaling-original.md` | Validation-selected source, **fixed three target epochs**, all 200 target labels; not the selected target-duration arm |
| V1/V2 sentinel 29.42→25.80; GP 25.76; greedy/PPO/random 9.20/8.36/3.76 | `origin/codex/experimental-selection-rl:docs/research/experimental-selection/RESULTS.md`, copied verbatim to `paper/evidence/experimental-selection-v1-v2-original.md` | Original report recovered; source fit 12,000 and calibration 2,500; five target campaigns |
| 600-candidate Table 1; counts, roles, behavior | `docs/experimental-selection-600-results.md`; `docs/experimental-selection-600-protocol.md`; `configs/experimental_rl/atlas_600_3layer.toml` | Report and frozen protocol; prior-exposed two-target diagnostic |
| Historical V3 means and MSH3 rescoring | `docs/experimental-selection-handoff-assessment.md` | **Handoff only; excluded from the current manuscript** |
| F7 exact/bound pilot 1.667→2.000 for random/greedy/Qwen | `docs/ic50-qwen-from-scratch.md`; `artifacts/ic50-qwen-from-scratch-v1/{protocol,results,summary,completion-audit}.json` | New frozen 100 nM pilot, not original V3/Qwen3-4B replay |
| Dose study 93 development, 240 assessment, errors, means, QC | `docs/adaptive-dose-response-experiment.md`; `artifacts/adaptive-dose-response-v1/report.json` | Table 2 and Figure 2a read saved assessment aggregates; failures retained |
| DP 162 settings, optimality counts, mean yields, max gap .4 | `docs/value-of-planning-experiment.md`; `artifacts/value-of-planning-v1/{grid.csv,ppo.json,protocol.json}` | Synthetic model expectations; no biological inference |
| Figure 2b headroom slice | `artifacts/value-of-planning-v1/grid.csv` | B=6, prevalence=.5, dependence-mixture=.75; columns cost 2/3/4, rows u=.1/.5/1 |
| Eight-target molecular Table 3 | `docs/molecular-scientific-experiments.md`; `artifacts/molecular-eight-target-extension-v1/eight-target-summary.json` | Retains target roles; means across seeds 800–804 |
| Molecular Figure 3 query trajectories | `artifacts/molecular-ppo-attribution-v1/analysis.json`, `summaries` | Actual mean archive trajectories for eight-request condition, four original development targets |
| PPO minus pretraining at 8/32 requests; 27,028 vs 2,880 offline queries | `docs/molecular-ppo-attribution-experiment.md`; `docs/molecular-policy-repair.md`; attribution artifact | Training costs aggregate five seeds; deployment separate; two head calls/request |
| F12 all 89 designs fail computational screen | `docs/molecular-policy-repair.md` and saved coverage audit | No measured biological-risk claim |
| No certified molecular final groups / domain gap | `docs/molecular-validity-experiment.md`; `docs/molecular-generalization-experiment.md`; `docs/molecular-compatible-data-experiment.md` | Compatibility and exposure audits; no outcome-based scope relaxation |

`evidence/figure-sources.json` records SHA-256 identities for all files read or transcribed into manuscript figures. The plotting script does not load raw assay outcome tables or retrain models. Original template examples `figure1.pdf` / `figure2.pdf`, if present, are not used by `oligarch.tex`.

## Bibliographic verification

All eleven cited entries were checked against primary proceedings, the original preprint, or the dataset's own release metadata. Related Work remains undrafted; extra outline anchors were not inserted merely to pad the bibliography.

| BibTeX key | Verification source |
|---|---|
| `oligogym` | https://proceedings.neurips.cc/paper_files/paper/2025/hash/4927dd556ff6e49671e3a77ac1f12487-Abstract-Datasets_and_Benchmarks_Track.html |
| `atlas` | https://huggingface.co/datasets/barneyhill/aso-atlas-2/blob/main/croissant.json ; dataset DOI 10.57967/hf/8687 |
| `rnafm` | https://arxiv.org/abs/2204.00300 (the RNA-FM preprint, not a misattributed RhoFold journal paper) |
| `lora` | https://arxiv.org/abs/2106.09685 (2021 preprint explicitly cited as such) |
| `ppo` | https://arxiv.org/abs/1707.06347 |
| `masking` | https://arxiv.org/abs/2006.14171 ; FLAIRS 35 (2022), DOI 10.32473/flairs.v35i.130584 |
| `jiang` | https://proceedings.mlr.press/v70/jiang17d.html |
| `nguyen` | https://proceedings.mlr.press/v139/nguyen21f.html ; proceedings index misspells “Active” as “Acitve”; bibliography uses corrected spelling |

Venue: https://ai-2-ase.github.io/cop/ explicitly states eight pages for long papers, references excluded, AAAI formatting and double-blind anonymization. The main-conference seven-page limit does not supersede this workshop limit. Official author-kit link: https://aaai.org/authorkit27/ .

## OLIGARCH editorial revision

The manuscript now uses OLIGARCH throughout and replaces internal version labels with descriptive single-dose, online Bayesian and linked-assay task names. Original report titles, paths and study IDs above are retained for provenance. Repetitive non-claim statements were removed from the abstract, introduction and captions while retaining the failed stopping criterion, surrogate/measured distinction and unresolved source evidence.

Added primary-source and textbook citations:

| Key | Verified source | Use |
|---|---|---|
| `zamecnik` | https://pubmed.ncbi.nlm.nih.gov/75545/ ; DOI 10.1073/pnas.75.1.280 | Sequence-specific antisense inhibition as a scientific intervention |
| `finkel` | https://www.nejm.org/doi/abstract/10.1056/NEJMoa1702752 ; https://pubmed.ncbi.nlm.nih.gov/29091570/ | Nusinersen, RNA splicing and therapeutic relevance |
| `sutton` | https://mitpress.mit.edu/9780262039246/reinforcement-learning/ | RL formulation and finite-horizon Bellman recursion |

Existing PPO and action-masking citations now also accompany the assay policy description; Jiang et al. and Nguyen et al. accompany the exact-planning motivation as well as the assay-lookahead description. The user-requested title is preserved literally, including capitalization and underlining.

## Readability revision

Added first-use definitions and plain-language explanations of models, policies, uncertainty, potency, metrics, and mathematical symbols. Numerical results, citations, evaluation failures, and evidence qualifications are unchanged. The anonymous review bibliography now begins on a separate page, with a source comment to remove the explicit break for camera-ready. The supplied style files remain unchanged.

## Completed Related Work and layout revision

The manuscript adds nine verified references from `literature-review-shortlist.md`. The brief section distinguishes prediction, constrained molecular search, acquisition/planning, and potency evidence without importing prior papers' performance numbers into our results.

| New key | Primary verification source |
|---|---|
| `oligoai` | https://pmc.ncbi.nlm.nih.gov/articles/PMC13427547/ ; https://www.broadinstitute.org/publications/broad1380766 |
| `asoptimizer` | https://github.com/Spidercores/ASOptimizer/blob/main/README.md ; DOI 10.1016/j.omtn.2024.102186 |
| `oligoformer` | Publisher PDF, DOI 10.1093/bioinformatics/btae577 |
| `oligorl` | https://pmc.ncbi.nlm.nih.gov/articles/PMC9004649/ |
| `pmo` | https://papers.neurips.cc/paper_files/paper/2022/file/8644353f7d307baaf29bc1e56fe8e0ec-Paper-Datasets_and_Benchmarks.pdf |
| `genedisco` | https://arxiv.org/abs/2110.11875 ; official ICLR 2022 OpenReview paper |
| `sebaugh` | https://onlinelibrary.wiley.com/doi/10.1002/pst.426 |
| `donev` | https://www.tandfonline.com/doi/full/10.1080/10543406.2010.481801 |
| `cobalt` | https://proceedings.mlr.press/v337/karlova26a.html |

The architecture figure is excluded from the manuscript and source ZIP. The user-requested copyright text is set using `\copyrighttext` in the manuscript, without modifying the supplied style. The style's default submission notice differs; this is an explicit user-requested override, with anonymous authors retained. The abstract qualification was removed, while the failed unresolved-reference criterion remains explicit in Results, the table/figure caption, and Limitations. All numerical results are unchanged.

## Narrative and scientific-validity pass

Reframed the abstract around introducing OLIGARCH and the introduction around its paired decision environments, comparative controls, and evidence-sufficiency studies. Result transitions now state each study's role. Discussion links learning, proposals, purchases, potency evidence, and planning to practical resource allocation. Retrospective readout savings remain distinct from passing the failed qualification criterion. Removed unverified eight-cohort historical means and MSH3 rescoring from the manuscript; originals remain in prior revisions and this audit. Corrected correlation wording to linear association and avoided causal isolation claims for pretraining.

No priority/“first” claim was added. OligoRL already supplies constrained oligonucleotide RL; the ASO Atlas 2.0 upstream repository explicitly describes a pipeline cost model and strategy comparisons (https://github.com/barneyhill/aso-atlas-2, checked November 16, 2026). Related Work now acknowledges that overlap. The contribution is the specific combination of chemistry-constrained construction, purchased-outcome access, query accounting, and controlled decision studies. This pass does not constitute a new independent replication or recover missing records.
