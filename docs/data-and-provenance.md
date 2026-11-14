# Dataset registry template

Source-document values below are references, not reproduced results. Loader handles are deliberately unresolved until verified against pinned upstream code. Pearson r refers to source-document nucleobase benchmarks, not target-split scores.

| Role | Display/source name | Rows | Targets | Reference r | Loader handle |
| --- | --- | ---: | ---: | ---: | --- |
| Headline potency | Huesken / Ichihara_2007_1; `siRNA1` alias pending | 2,431 | 30 | 0.631 | unresolved |
| Auxiliary immune | TLR7 / Alharbi_2020_1; mapping pending | 192 | 4 | 0.727 | unresolved |
| Auxiliary immune | TLR8 / Alharbi_2020_2; mapping pending | 192 | 4 | 0.699 | unresolved |
| Primary toxicity | Neurotox MOE / MOE_Neurotox_1; `acute_neurotox_moe_cleaned` alias pending | 2,437 | 13 | 0.703 | unresolved |
| Stretch potency | OpenASO / McQuisten_2007_1 | 3,913 | 86 | 0.291 | unresolved |

Huesken is unmodified siRNA, while intended candidates are PS/2'-MOE ASOs: potency transfer is unresolved. Immune and MOE labels come from separate experiments with different chemistry and missing endpoints. TLR7/8 descriptions may be swapped upstream. MOE is a patent-derived rounded three-hour FOB outcome over seven ordinal categories treated as regression, with selection effects. Species, route, and dose remain unresolved because source documents disagree on rat versus mouse. Do not restore Cytotox LNA as primary or include Sherwood by default.

The upstream code license reported by the documents is Apache-2.0; dataset and weight rights require separate review. No upstream files, PDFs, datasets, or weights are copied here.
