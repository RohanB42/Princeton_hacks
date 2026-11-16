# Molecular predictor validity: executed metadata feasibility experiment

November 15, 2026. This is a completed metadata experiment and a proposed measured
follow-up. It does not qualify a predictor, promote a profile, or establish
biological efficacy. The current reward models, chemistry grammar and risk screen
are unchanged. Read with the [final specification](FINAL_MOLECULAR_DESIGN_RL_SPEC.md)
and [earlier data audit](molecular-measured-data-scaling.md).

## Answer and new evidence

**The immediate problem is a mismatch between the chosen chemistry and efficacy
assay context, not a complete absence of measurements for those chemistries.**
Thousands of exact current-pattern measurements exist at other assay contexts.
However, preserving earlier data roles and connected molecular/patent groups
prevents simply treating these measurements as unused training data. A qualified
replacement multi-pattern, multi-length profile is not established by this audit.

The executable experiment projected metadata from all **174,459 inhibition rows
and 4,900 neurotoxicity rows**, verified the pinned source hashes, and completed
in **10.57 seconds**. It read no measured outcome column, made no model predictions,
fit no model and preserved the **304 sealed risk-final rows**. Seven scientific
invariant tests passed. The immutable protocol was written before projecting the
source tables. Generated outputs remain ignored under
`artifacts/molecular-validity-experiment-v1/`.

The current efficacy tuple remains human HepG2, electroporation, 4,500 nM, 24 h:
5,870 raw rows, 23 parser rejections, **zero verified exact matches to any of the
three current patterns**. Parser failures are unknown, not evidence of absence.
The fixed risk tuple remains mouse C57BL/6, ICV, 700 micrograms, 3 h, Behavioral
tolerability. Its exact active-pattern counts reproduce the earlier protocol:
166 / 720 / 834 for `atlas-stress-18-0` / `20-0` / `20-1`.

## What changing the efficacy context would provide

All rows below exactly match the named existing pattern, including observed base
modification, sugar and linkage positions and terminal state. These are raw
metadata counts, not outcome-qualified training cohorts. Patent and target names
are source identifiers; aliases and patent families have not been resolved.

| Human efficacy context | Existing pattern | Rows | Distinct compounds | Patent IDs | Target IDs | Outside preserved patent/sequence components |
|---|---|---:|---:|---:|---:|---:|
| A431, gymnosis, 4,000 nM, 48 h | 20-0 | 8,295 | 8,090 | 6 | 5 | 1,689 |
| A431, gymnosis, 4,000 nM, 48 h | 20-1 | 1,683 | 1,681 | 2 | 2 | 0 |
| SH-SY5Y, electroporation, 4,000 nM, 24 h | 20-0 | 3,684 | 3,655 | 3 | 2 | 0 |
| SH-SY5Y, electroporation, 4,000 nM, 24 h | 20-1 | 5,960 | 5,916 | 4 | 3 | 0 |

The last column excludes every row connected to an existing selection,
development, calibration, assessment or reserved row by exact natural sequence or
patent identifier, including transitive connections through other metadata rows.
It is a conservative upper bound on possible new fitting data, **not a clean
training allocation**: near-sequence families, cross-source overlap and other
branches' exposure receipts remain unresolved. Existing fitting rows may still be
included in this count; it does not mean all remaining labels are unseen.

For example, the A431 20-1 cohort includes 1,218 historically reserved DMPK rows.
The other target is FUS, whose patent contributed to historical checkpoint
selection. Moving either role into a new fitting cohort would violate the
instruction to preserve those roles. The 8,295-row A431 20-0 cohort includes 236
active-model fitting rows, but zero active-model selection rows; other seeds'
selection memberships and transitive components still remove most of that pool.

There are 41 pattern/context combinations across the full efficacy release,
including incomplete contexts which are not eligible assay definitions. The only
complete efficacy tuple containing **all three** active patterns is human
SH-SY5Y, electroporation, 8,000 nM, 24 h: **236 / 76 / 2 rows**, respectively.
All are in preserved components. Across all contexts the 18-mer has 2,694 exact
matches, with **zero** outside those preserved components. Thus merely changing
the assay tuple does not supply a new clean cohort for the intended three-pattern,
two-length task.

## Could different chemistry solve the fixed-context mismatch?

The bounded alternative-profile search found **16 uniform-cytosine gapmer families**
shared between some inhibition context and the fixed risk context. It preserves
full ordered sugar/link tracks and terminal state and distinguishes all observed
cytosines methylated from all observed cytosines unmodified. It excludes mixed
cytosine patterns, molecules with no cytosine, uracil-containing templates and
unsupported gapmer layouts from family inference. It therefore does not claim an
exhaustive search of every chemistry present in the release.

Only one of these families overlaps the **current efficacy context**: the known
20-mer MOE 5 / DNA 10 / MOE 5, fully PS, all-C-methylated, no-terminal-phosphate
family. It has **4,758 efficacy rows / 4,368 distinct compounds**, but only **11
risk-context rows / 11 compounds across three patent IDs**. Eight risk rows remain
outside the conservative protected components. There is no observed cytosine at
one of the 20 positions in that small risk set; compatibility does not establish
position-wise or sequence-wide predictive support.

Those 11 risk rows are insufficient even for the existing requirement of at least
20 fitting observations per pattern, before independent development, calibration
and final allocations. The family's 4,758 efficacy rows are all connected to
protected metadata components. Its earlier efficacy-only model remains a useful
restricted development control, but this result cannot manufacture a qualified
multi-endpoint, multi-pattern molecular designer.

Family counts omit no-C molecules because their methylation template is
unobservable. Direct matching to an already declared pattern includes no-C
molecules when the full molecular identity matches. This explains differences
between the family table in `result.json` and active-pattern totals; it is not
inconsistent chemical canonicalization.

## Exposure and exclusions retained

The generated `exposure-ledger.json` contains source-qualified IDs rather than
invented biological labels. Memberships are overlapping provenance roles, not an
assertion that historical splits form one globally clean partition.

| Study or component | Existing exposure / restriction |
|---|---|
| Active efficacy Ridge | 2,284 fit and 585 selection IDs; selection is not spare fitting data |
| Six historical source Ridge checkpoints | All fit/selection memberships for source allocations 2,869 and 4,781, seeds 510–512; overlap remains disclosed |
| Historical broad source preparation | 95,638 source-pool IDs, 14,614 source-validation IDs; source pool is eligibility, not proof every label was read |
| Earlier supported-profile study | 2,000 fitting and 1,924 measured-assessment IDs; ATXN2/DGAT2/SERPINA1 assessment is already development evidence |
| Atlas adaptation/scaling development | F7, STAT3, NLRP3 pool and test memberships preserved; prior target adaptation used measured labels |
| Historical reserved Atlas campaigns | PTBP1, KCNQ2, DMPK, PLN, SMAD7, PSD3, DUX4; both pool and test memberships conservatively protected pending cross-study audit |
| Current risk qualification | 874 allocated fit IDs (873 observed fitting labels after prior amendment), 259 development, 283 calibration, 304 final; all roles retained |
| Current policy study | DGAT2, SOD1, B2M, HPRT1, PCSK9, VEGFA training; CFB/F7 validation; FGFR4/F9/F12/TTR development; none becomes fresh confirmation |

The union contains **30,126 protected source-row IDs**. Closing exact-sequence and
patent connections over all parsable inhibition and neurotoxicity metadata protects
**138,681 rows**. This intentionally conservative rule does not establish that
every connected outcome was read: it prevents calling related compounds or patents
independent merely because a particular row ID was unused. The cross-endpoint
exclusion is a study-design safeguard, not an assertion that risk and efficacy
measure the same biological endpoint.

Remaining exposure blockers are explicit: OligoGym–Atlas identity and near-family
overlap, unresolved patent families/gene aliases, and actual fitting/outcome-access
receipts from other research branches. Metadata for a reserved row can be audited
without revealing its outcome. No reserved label is reclassified as training in
this experiment. Historical reserved status alone is insufficient to assert that
a target was never exposed anywhere else in the project.

## The next measured experiment

Do not begin with a larger PPO run or fit all Atlas rows. The immediate experiment
should be a **separately declared retrospective transfer/development study**,
followed by a fresh supported-profile qualification if the evidence permits it.
It must preserve the current diagnostic profile for reproducibility.

1. **Complete exposure recovery before scoring.** Recover fitting, model-selection,
   calibration, stopping and actual measured-assessment IDs from the other Atlas,
   supported-ASO, robustness and OligoGym studies. Connect canonical compounds,
   natural sequences, declared Hamming-distance/one-base-shift families and verified
   patents before selecting a cohort. Quarantine unsupported parser rows and
   unresolved identifiers. Preserve the risk-final 304 and historical reserved
   campaigns. Write immutable source-qualified partitions and a conflict report;
   do not break a large connected component to obtain convenient sample counts.

2. **Declare one narrower estimand.** A431/gymnosis/4,000 nM/48 h is a candidate
   efficacy context for studying the existing 20-mer patterns, chosen using
   metadata only. However, the second pattern currently has no candidate fitting
   rows outside preserved components, and the first pattern's 1,689 rows have not
   passed the remaining audit. A one-pattern/context restriction remains a
   proposed, unapproved replacement scope; it was not implemented here. This is
   not permission to relabel the present
   HepG2 reward or to claim both lengths supported. A direct all-three-pattern
   study at the current context is blocked. If the aim remains that exact context,
   genuinely new compatible measurements are required, or an explicitly qualified
   extrapolation study must address that gap.

3. **Audit existing checkpoints before refitting.** Compare the 2,284-fit and
   3,813-fit Ridge artifacts on a common, permitted, exposure-audited development
   cohort only after export/owner parity and the complete context contract pass.
   Frozen old artifacts are historical transfer comparators, not the low/high
   points of a valid data-size learning curve: their fit and selection memberships
   changed with source size. Existing source features may be unable to identify
   the requested assay response separately from chemistry/patent effects. Assess
   the actual feature contract before assigning a context to a prediction.

4. **Freeze measured endpoints and statistics before outcome access.** For a
   recorded-compound ranking study, use campaign-macro top-20 inhibition lift over
   the exact random-pool mean as the primary endpoint, with a minimum of 30
   admissible distinct compounds per campaign. Prespecify RMSE/MAE and within-campaign
   Spearman as secondary diagnostics; constant or tiny groups yield undefined
   correlations rather than zero. Compare the same sealed panels/rows and assay
   units for every model. Use paired uncertainty across independent target/patent
   components, report small-group limitations, and require at least five final
   independent target groups for the eventual confirmatory cross-target claim.
   Development results may select models; final outcomes never select models,
   safeguards, scope, thresholds, sample sizes or stopping.

5. **If sufficient clean fitting data remain, run the classical curve first.**
   Use append-only group additions with fixed development/calibration/final sets
   and matched context-only, chemistry-aware Ridge and XGBoost controls. Start with
   sizes supported by the audited cohort; 2k/4k/8k are not valid promises here.
   Keep fitting, selection, calibration and target-adaptation labels in separate
   ledgers. A larger neural curve is contingent on this cheap comparison and a
   bounded runtime profile. Preserve negative results and all prespecified tiers.

6. **Freeze a new qualified scorer only after independent measured evidence.**
   Test whether a predictor improves recorded-compound ranking without degraded
   applicability/calibration under the frozen criteria. Then run policy/search
   comparisons under that versioned scorer and judge returned panels with a
   common independent evaluator. A higher newly rescaled surrogate return does
   not measure predictor improvement, PPO's incremental contribution, or efficacy
   of a newly generated molecule. The acute mouse-risk endpoint remains separate
   from human efficacy and cannot support a clinical safety label.

No measured development comparison ran in this task because the complete scope
and leakage gates did not pass. The blocker is demonstrated with executed metadata
counts, rather than being deferred as an unspecified data need. Alternative assay
support is promising, but it is not yet a deployable qualified profile.

## Implementation, artifacts and checks

Implementation: `scripts/molecular_validity_experiment.py`.
Tests: `tests/test_molecular_validity_experiment.py`.
The new files do not change shared contracts, dependencies, checkpoint weights,
profile configurations, raw data, model screens or the historical investigation.

```sh
PYTHONPATH=src /private/tmp/oligoal-atlas-rnafm-20261114/.venv-atlas/bin/python \
  scripts/molecular_validity_experiment.py \
  --config artifacts/molecular-policy-repair-v3/config.json \
  --historical /private/tmp/oligoal-atlas-lora-scaling-20261114/artifacts/atlas-rnafm \
  --output artifacts/molecular-validity-experiment-v1
```

Use a new output directory to reproduce: writes refuse to overwrite prior sealed
outputs. The historical directory is a required local provenance input; missing
receipts fail execution rather than reconstructing imaginary memberships.

Protocol seal: `970b5866fc453b469311933c02c7a9356ff8fa13acb11f47130794ea01998ce9`.
Result seal: `348f8c39173e3da720def96ab187ef250b9e0e89099fb3256cc7b713cf6a4273`.
Both source SHA-256 values, metadata projections, input/script hashes, Git revision
and dirty-working-tree status are recorded in the protocol. Hashing raw bytes for
integrity does not deserialize outcome columns. All Parquet reads use an explicit
positive metadata allowlist; the runner has no outcome-scoring phase.

Checks run: seven new invariant tests pass; Ruff lint and formatting pass for the
new script/tests. Tests reject outcome/unknown columns, preserve methylation,
linkage and terminal distinctions, reject unidentifiable no-C/mixed-C families,
exercise transitive protected-component exclusions independent of row ordering,
and prevent numeric context normalization from inventing biological aliases.
PyArrow emitted harmless sandbox CPU-cache introspection warnings; execution
completed successfully. No full repository test result is claimed by this task.
