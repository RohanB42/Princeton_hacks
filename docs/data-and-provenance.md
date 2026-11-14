# Dataset registry template

Source-document Pearson values below are references, not reproduced results or target-split scores. Dataset files and loader keys were checked against Roche/OligoGym revision `97f5b9f58d9e445a8ecb0218037af7465c3708c0`; this does not verify benchmark behavior.

| Role | Display/source name | Rows | Targets | Reference r | Loader handle |
| --- | --- | ---: | ---: | ---: | --- |
| Headline potency | Huesken / Ichihara_2007_1; `siRNA1` benchmark alias pending | 2,431 | 30 | 0.631 | `Huesken` |
| Auxiliary immune | TLR7 / Alharbi_2020_1; identity conflict below | 192 | 4 | 0.727 | `TLR7` |
| Auxiliary immune | TLR8 / Alharbi_2020_2; identity conflict below | 192 | 4 | 0.699 | `TLR8` |
| Primary toxicity | Neurotox MOE / MOE_Neurotox_1; `acute_neurotox_moe_cleaned` benchmark alias pending | 2,437 | 13 | 0.703 | `Neurotox MOE` |
| Stretch potency | OpenASO / McQuisten_2007_1 | 3,913 | 86 | 0.291 | `OpenASO` |

Huesken is unmodified siRNA, while intended candidates are PS/2'-MOE ASOs: potency transfer is unresolved. Immune and MOE labels come from separate experiments with different chemistry and missing endpoints. At the pinned revision, the `TLR7` registry key points to `Alharbi_2020_1`, whose JSON describes a TLR8 assay; `TLR8` points to `Alharbi_2020_2`, whose JSON describes TLR7. The underlying assay identities remain pending source-paper verification. MOE is a patent-derived rounded three-hour FOB outcome over seven ordinal categories treated as regression, with selection effects. Species, route, and dose remain unresolved because source documents disagree on rat versus mouse. Do not restore Cytotox LNA as primary or include Sherwood by default.

The upstream code license reported by the documents is Apache-2.0; dataset and weight rights require separate review. No upstream files, PDFs, datasets, or weights are copied here.
