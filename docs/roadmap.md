# Implementation gates and future backlog

Completed first slice: contracts/specs, pinned source audit, synthetic random replay,
and a five-seed measured linear-baseline rerun. Gate 1 is still open (0.031032
reference gap versus frozen 0.03 tolerance); see upstream-verification.md. Resolve
reproducibility before adding novel models or measured acquisition policies.
Detailed dependencies and ownership: IMPLEMENTATION_TASKS.md.

November 14: all 12 released datasets and measured diagnostic replay are now
implemented under explicit user authorization. Full-row integrity validation and
sample-capped per-dataset random/uncertainty campaigns are engineering checks.
Benchmark-comparable multi-seed research conclusions, figures, app, design and RL
remain future work. The reproduction discrepancy is not marked resolved.

- [ ] H0-H4, Gate 1: pin upstream, verify mappings and split configuration, reproduce one published PCC within about 0.03. If it fails, resolve before modeling.
- [ ] H4-H12: predictor baselines; optional surface skeleton in a separately assigned task.
- [ ] H12-H20, Gate 2: measured-label curves for active versus random acquisition across at least five seeds, with defined bands. Investigate and report no separation honestly.
- [ ] H20: cut design if behind.
- [ ] H28: cut Boltz and extra datasets.
- [ ] H36: use a static result page if the interactive surface is behind.
- [ ] H44: freeze and rehearse.

Design documentation only: future PS/2'-MOE action space and frozen-predictor objectives may consider oligo hairpin, CpG motif, guanine proximity to the 3' end, and scored off-target multiplicity. Signs, scaling, weights, and endpoint compatibility need decisions. Target-RNA accessibility differs from an oligo hairpin, needs transcript retrieval, and remains stretch-only behind Gate 2. Boltz would be post-ranking rescoring, never core-loop work.
