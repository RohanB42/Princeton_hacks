# Evaluation-data expansion: metadata audit

Status: completed metadata investigation; no new model evaluation, fitting,
calibration, policy reward, or final-set assignment. This answers the request for
**more evaluation data**, which has different eligibility rules from the earlier
search for unused fitting data. Generated molecules remain unvalidated hypotheses.

There are useful assessment opportunities. We already have a reserved 304-record
risk assessment, several separate efficacy transfer strata, and concrete external
experimental sources. We have not yet certified a new independent cohort matching
the full current molecular profile. Those statements are compatible: lack of new
training-eligible rows does not invalidate an existing reserved evaluation set.

## What was audited

`scripts/molecular_evaluation_data_audit.py` reads only positive-listed chemistry,
sequence, patent, target, and assay-context columns from the pinned local Atlas
release. It reads existing model provenance and role manifests, never raw outcome
columns, and never calls a predictor. The protocol seals source, model, helper,
configuration, ledger, and driver hashes before producing candidate manifests.

Each head excludes its own fitting, selection, and calibration memberships. Other
project membership is reported separately: membership in a source pool is not
proof that a label was accessed, and absence from one head's training set does
not prove project-wide freshness. Original reserved assessment roles are retained.

Independence is examined at three levels: direct source-row IDs; exact sequence
and recorded patent-ID components; and those components expanded by Hamming
distance at most two or equal-length one-base shifts. The graph includes parsed
metadata from both endpoints and all contexts, so a bridge outside the scored
context can connect apparently separate panels. This is a conservative sensitivity
definition, not a complete biological homology or patent-family resolver.
International patent aliases and unparsed chemistry still require review.

The current grammar has three mixed PS/PO MOE gapmer patterns, with 18- or
20-nucleotide sequences and methylated cytosines. A natural sequence alone does
not establish compound identity. Numerical formatting is normalized; 4,000 nM
is never silently treated as 4,500 nM, and different delivery methods, cells,
species, time points, and behavioral scales remain separate.

## Existing measured assessment coverage

The efficacy head used 2,284 fitting and 585 selection records. Its active context
is human HepG2, electroporation, 4,500 nM, 24 hours. No parsable release row
simultaneously matches that context and a current grammar pattern. This limits
direct evaluation of that specific setting; it does not prohibit declared
out-of-context evaluation.

The risk head used 873 fitting, 259 development, and 283 calibration observations.
Its original **304 final records remain sealed**. The matching metadata context
contains 1,720 records representing 1,720 distinct parsed compound identities:
these roles plus one originally allocated fitting record without a usable
observation. That extra metadata record is not new assessment evidence.

| Risk sensitivity, current chemistry/context | Remaining original final records | Interpretation |
|---|---:|---|
| Original reserved role | 304 | Preserve original assessment allocation |
| Full-release exact-sequence/patent-ID closure | 303 | One final record has an additional metadata link |
| Full-release near-sequence/patent-ID closure | 226 | Three components, targeting ATXN3, FUS, LRRK2 |

The 78-record difference between 304 and 226 is a metadata independence concern,
not an observed error rate. Do not move those records to training or silently
replace the original assessment with a favorable subset. Before unsealing, freeze
both the original-protocol analysis and the stricter independence sensitivity,
and report the discrepancy. Three surviving components give much less effective
replication than 226 independent observations.

The following complete-context strata match current grammar chemistry and survive
the efficacy head's full-release near-sequence/patent-ID exclusion:

| Target | Separate measured context | Rows | Components | Existing exposure status |
|---|---|---:|---:|---|
| KCNQ2 | Human SH-SY5Y, electroporation, 4,000 nM, 24 h | 1,008 | 1 | Target already used in historical evaluation; 468 rows have ledger memberships and 540 lack recovered membership |
| PTBP1 | Human A431, gymnosis, 3,000 nM, 48 h | 463 | 1 | Historical assessment/source memberships |
| GYS1 | Mouse B16-F10, electroporation, 7,000 nM, 24 h | 67 | 1 | Historical memberships; species transfer |
| MECP2 | Human HepG2, electroporation, 4,000 nM, 24 h | 9 | 1 | Historical memberships; different dose |
| GYS1 | Human A431, gymnosis, 4,000 nM, 48 h | 3 | 1 | Historical memberships |

These are candidate retrospective transfer diagnostics, not five newly untouched
confirmation cohorts. In particular, missing recovered membership for 540 KCNQ2
rows is not evidence of non-exposure. PTBP1 and KCNQ2 belong to the historical
seven-target reserve, whose targets were subsequently consumed by experimental
selection development/final replay. Preserve that history rather than renaming
it a fresh final test. The earlier 298-row MECP2 fitting candidate used different
eligibility criteria; it must not be substituted for these nine pattern-matching
assessment candidates.

### Subsequent handoff-reported exposure (not manifest-verified)

The user subsequently supplied a Harrison handoff describing local experimental
commit `30ac0e9` as unpushed. Its underlying manifests are not available to this
audit, so the following is source-qualified exposure evidence, not a rerun or a
change to the sealed metadata counts. It reports that original V3 final targets
MSH3, FUS, ATXN1, KCNT1, SCN2A, YAP1, IFNAR1, and SNCA were already inspected;
later conditional training used seven genes and 925 compounds, adding FUS, YAP1,
and KCNQ2. KCNQ2 therefore remains an own-current-head-independent retrospective
candidate, with additional reported training exposure elsewhere in the project.
External **KCNT2** is a different target from the reported V3 **KCNT1**.

The handoff also reports a within-target NLRP3 split of 204 training, 67
development, and 67 test compounds used for PPO and a 512-draw replication.
Without the exact split/access manifests, no record-level freshness claim follows.
Its EZH2/SPDEF source Ridge side heads and separate OligoGym GP conditional
advisories are distinct from the current molecular Ridge heads audited above.

Reported same-patent structural leads include risk panels FUS (25) and APP (71),
and hepatic panels EZH2 (41), SPDEF (19), NLRP3 (39), and IRF4 (18). These counts
are unverified source leads, not newly certified independent data or compatible
endpoint labels. Patent-family, compound, chemistry, assay, and exposure audits
would be required before assigning any evaluation role. No labels were opened
and no sealed allocation or result was changed for this addendum.

For risk, another 191 rows across three components survive the own-head exclusion
at rat Sprague-Dawley, intrathecal 3,000 micrograms, three hours, **body-parts**
scoring. Two FUS rows survive at mouse ICV 500 micrograms. Neither is the current
700-microgram mouse behavioral endpoint. Rat scores cannot be pooled into mouse
FOB calibration or treated as human clinical safety.

The parser rejected 1,211 inhibition and 45 neurotoxicity metadata rows. Counts
describe supported parsed chemistry; they are not proof that rejected rows are
scientifically unusable. Raw files were preserved. The online Atlas card currently
reports 4,896 neurotoxicity records while this pinned release has 4,900; changing
the release would require a new provenance audit, not an in-place refresh.

## Concrete external candidates

Selection used experimental design, endpoint, provenance, and metadata
availability. Public article summaries and aggregate results were visible during
literature research; this is **not** total literature outcome blinding. No external
row-level outcome columns were opened and no candidate was selected by its
observed success rate or by our predictors' performance.

**OligoAI KCNT2 validation is the strongest next transfer/potency candidate.** The
paper describes 50 new experimental ASOs: 32 sampled from the whole library and
18 sampled from a model-ranked subset. Reported validation uses MOE gapmers,
HeLa/RNAiMAX, 30 nM, 48 hours, with follow-up dose-response measurements. Keep the
random and selected strata separate; pooling them estimates neither random-library
yield nor an unbiased selection-policy comparison. Per-record chemistry and
raw validation-table availability still need verification. Its large underlying
patent compilation is substantially related to Atlas and is not automatically
new independent evidence. Article: CC BY 4.0; repository license is not a blanket
license for every source measurement. [Primary paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13427547/),
[code and released files](https://github.com/barneyhill/OligoAI),
[bulk archive](https://zenodo.org/records/20794660).

**ClinASO offers several separate target panels.** Published initial candidate
counts include PCSK9 12, IRS1 17, and ACSL4 20, with additional controls/variants
and SRPK1 sequence information. Reported 5-10-5 MOE/full-PS chemistry differs from
the active mixed-backbone grammar. Targets also differ in cells, delivery, dose,
and later conjugation. Supplementary Table S1 (`mmc2.xlsx`, 19.8 KB) contains ASO
information; Table S3 (`mmc3.xlsx`, 40.9 KB) describes low-scoring candidates.
These have not been downloaded or opened. Target panels are not yet deduplicated
independent cohorts, and candidate selection must be recorded. Article: CC BY
4.0; supplement and third-party provenance still need verification.
[Primary paper and supplement links](https://pmc.ncbi.nlm.nih.gov/articles/PMC13156736/).

**The acute-CNS study is close to the risk context but not certified new.** It
contains a 34-ASO panel at mouse ICV 700 micrograms, three hours, including
reduced-PS designs. Its supplementary sequence/chemistry tables could support
an exact compound audit. However, this paper and patent US9605263B2 already occur
in current risk qualification provenance. Overlap with Atlas may be substantial;
the panel cannot be called 34 additional independent observations. Scoring rubric,
strain, chemistry, and source rights still require record-level confirmation.
[Primary study](https://doi.org/10.1093/nar/gkaf1333).

**An eight-record external cohort was actually staged and audited.** The published
small-data study retains six DAZAP1 and two FAM69C wet-lab ASOs after QC, from a
30-candidate screen. Methods describe SH-SY5Y lipofection and five-day exposure.
Its article is CC BY; its repository is MIT, without automatically establishing
rights for literature-derived records. The metadata has 20-base sequences but no
full chemistry or usable treatment concentration. Consequently these records are
currently unqualified for exact-profile or complete-input assessment. The
QC-selected panel and two-target scope also limit inference.
[Primary paper](https://www.frontiersin.org/journals/systems-biology/articles/10.3389/fsysb.2026.1921636/full),
[pinned repository](https://github.com/rguha-cs/small-data-aso-ml-pipeline/tree/5b5f3462a0193cad93d9a898ac8fa0abcaaed250).

The two staged CSVs preserve original bytes: `Master_ASO_KD_clean.csv` (6,159
bytes) and `wetlab_KD.csv` (562 bytes). Only metadata columns were projected.
The former is a separate literature pool, not eight new laboratory measurements.
For the eight wet-lab sequences, neither head has an exact sequence match,
target overlap, or connection through the audited local exact/near/patent graph
to its own fit/selection/calibration rows. The eight sequences form five local
sequence components across **two targets in one study**. This is a useful concrete
candidate, not five independent studies. Missing external patent and chemistry
annotations prevent complete compound/provenance certification. The result also
does not turn efficacy measurements into risk labels.

## Next frozen assessment protocol

1. Pin model weights, preprocessing, inputs, thresholds, data versions, and a
   metadata-only cohort manifest before reading reserved/external labels. Audit
   fitting, hyperparameter selection, calibration, policy-development, and prior
   assessment roles separately. Retain full chemistry and publication/patent
   family provenance, not sequence alone.
2. Preserve the original 304-record risk assessment and preregister the 226-record
   component sensitivity without changing the decision threshold. Use existing
   endpoint definitions and metrics; distinguish discrimination from calibration.
   Report target/component counts, undefined metrics, and uncertainty. A bootstrap
   over individual correlated oligos would overstate precision; three surviving
   groups do not support confident broad generalization claims.
3. Evaluate efficacy transfer contexts separately, at their actual assay context,
   only after checking whether the frozen head can represent those inputs. Report
   these as retrospective diagnostics where targets/labels were already exposed.
   Do not silently change the current campaign context or add fit/calibration
   steps using assessment labels. No model fallback should invent missing dose or
   chemistry for the external eight-record panel.
4. For KCNT2/ClinASO, extract metadata under an explicit allowlist; freeze exact
   candidate strata and compound/family overlap exclusions before opening outcomes.
   Preserve raw files, source commit/hash, license evidence, controls, replicates,
   dose grids, and censoring. IC50 requires its own exact/bounded/unresolved outcome
   adjudication; single-dose inhibition is not IC50. Keep the existing Qwen pilot
   away from these prospective external panels during development.
5. Report inference at its actual unit: study, target, chemical family, compound,
   and assay replicate. More rows within one source/target increase precision
   within that setting but do not create new independent biological domains.
   A generated molecule only receives measured validation through an exact
   compound-and-assay join or a new experiment; frozen prediction is not a label.

## Reproduction and evidence

Ignored artifacts are under `artifacts/molecular-evaluation-data-expansion-v1/`:
sealed local `protocol.json` and `result.json`, outcome-free
`evaluation-candidates.json`, an external source catalog, pinned GitHub file-tree
metadata, and `external/` raw-byte manifests, sequence-only audit code, protocol,
results, and local-source hash verification. All new final assignments are null.
No datasets or generated artifacts were committed.

```sh
PYTHONPATH=src python scripts/molecular_evaluation_data_audit.py \
  --output artifacts/molecular-evaluation-data-expansion-new-run
python -m pytest tests/test_molecular_evaluation_data_audit.py -q
python -m ruff check scripts/molecular_evaluation_data_audit.py \
  tests/test_molecular_evaluation_data_audit.py
python -m ruff format --check scripts/molecular_evaluation_data_audit.py \
  tests/test_molecular_evaluation_data_audit.py
```

Actual checks: seven invariant tests passed; Ruff check and format passed. Both
metadata audits completed without opening endpoint columns, fitting, prediction,
or final-label evaluation. The external download needed network access, which
automatic review approved. This work does not certify Gate 1 reproduction,
clinical safety, a fresh joint efficacy/risk benchmark, or additional policy wins.
