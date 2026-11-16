# OLIGARCH anonymous workshop manuscript

The completed draft is **`OLIGARCH-anonymous-review.pdf`**. It has **8 pages of main text; 9 pages total including references**, in the supplied AAAI-27 anonymous submission format. A concise Related Work section is included. This is a manuscript draft for review, not a claim that all scientific submission issues have been resolved.

## Files

- `AAAI_AI2ASE_Short/oligarch.tex`: manuscript entry point; all requested sections.
- `AAAI_AI2ASE_Short/references.bib`: twenty verified citations covering biology, prediction, molecular search, acquisition, planning, and potency measurement.
- `AAAI_AI2ASE_Short/figures/{prediction,measurement_planning,molecular}.pdf`: three manuscript vector figures; PNG previews are alongside them.
- `OLIGARCH-latex-source.zip`: portable anonymous source package with the required style, bibliography style, figures and build instructions.
- `EVIDENCE_AUDIT.md`: author-only claims-to-source map, citation verification and unresolved scientific issues. **Do not submit this internal file unredacted.**
- `evidence/`: two recovered original reports, figure-source hashes and manuscript-source hashes.
- `verification.json`: page, font, anonymity-string, cross-reference, overflow and numerical checks.
- `rendered/`: page images and extracted text for visual inspection; not submission material.
- `generate_figures.py`: regenerate figures from existing repo reports/aggregates; performs no fitting or new experiments.
- `build.py`: compile with pdfLaTeX, BibTeX, then two pdfLaTeX passes; copies the final review PDF to this directory.
- `package_sources.py`: refresh the standalone anonymous source ZIP.
- `verify_manuscript.py`: verify the built PDF and selected derived results against saved aggregates.

The existing `AnonymousSubmission2027.tex/.pdf` and other author-kit examples were preserved. **Those are template instructions, not the OLIGARCH manuscript.** The style and bibliography-style files were not edited. All new work is contained under `paper/`. The earlier OligoAL-named draft is preserved under `revisions/before-oligarch-rename/`; the current manuscript and outputs use OLIGARCH.

## Build

With a standard TeX Live installation, run from the repository root:

```sh
python paper/build.py
python paper/verify_manuscript.py
```

`build.py` also detects the portable pdfLaTeX installation created in `.tex-runtime/` for this session. The supplied AAAI-27 style requires pdfLaTeX; XeLaTeX/Tectonic is not a compatible substitute. `verify_manuscript.py` needs PyMuPDF (or the session's `.render-deps/`). Figure regeneration needs NumPy and Matplotlib:

```sh
python paper/generate_figures.py
python paper/build.py
python paper/verify_manuscript.py
```

A standalone source package can be compiled without the repository's datasets or artifacts, using its included figure PDFs. Regeneration of the scientific figures requires the original report/aggregate files named in the source manifest. No raw outcomes, checkpoints or hidden assay records are included in the source package.

## Verification completed

- Nine total US Letter pages, main text and conclusion within the workshop's eight-page allowance; references begin on a separate page 9.
- Three vector figures, three compact tables, five labeled equations, numbered conventional sections and resolved cross-references.
- Anonymous author configuration, empty PDF author metadata, no identifying project-owner names or local paths in extracted PDF text.
- Sixteen embedded fonts, no Type 3 fonts, no overflowing boxes or undefined citations/references in the final build. Some ordinary underfull-box warnings remain; rendered pages were inspected for readability.
- All nine pages rendered and visually inspected. Figure label crowding and two long equations were corrected without changing the template, margins, fonts or spacing.
- Planning optimality counts and mean yields, the 63.8% readout reduction, and the six-of-eight molecular comparison checked against original saved aggregates.
- The portable source ZIP was extracted into a separate directory and successfully compiled without repository data or report dependencies.
- No new experiment, model training, raw-data edit, Git commit, push or workshop submission was performed.

## Main unresolved items

Recover original later linked-assay records before adding their numerical comparisons; resolve independent molecular evaluation and assay applicability; retain the failed stopping-QC criterion; and confirm the venue's supplementary-material requirements. See `EVIDENCE_AUDIT.md` for the concise full list and source map. Historical linked-assay numerical summaries are now excluded because their original records remain unavailable.

## Current editorial revision

Applied the exact requested OLIGARCH title and underlining, renamed the framework throughout the manuscript, replaced implementation version labels with descriptive task names, redesigned the architecture figure using sentence-case serif typography, and added a cited biological introduction plus reinforcement-learning and planning citations. Repetitive disclaimers were removed or replaced by direct statements of contribution; reported assessment failures and evidence-access limitations remain accurate. This earlier revision left Related Work as a placeholder; it is now complete.

The readability revision introduces specialist terms and abbreviations on first use, explains equation symbols and decision rules, and simplifies dense passages without changing numerical results. References now start on their own page in the anonymous review draft. Remove the explicit bibliography page break for camera-ready formatting. Related Work has since been completed.

The latest revision removes the architecture figure and its manuscript references, adds a compact four-paragraph Related Work section based on `literature-review-shortlist.md`, and restores the requested standard AAAI 2027 copyright text through the supported manuscript command. The abstract omits the unresolved-panel qualification; Results and Limitations retain the failed criterion. A repeated introduction preview and the conclusion were shortened to retain eight main-text pages. References begin on page nine. The style files are unchanged.

The narrative revision opens with “We introduce OLIGARCH,” connects each results subsection to a common resource-allocation question, and expands practical implications in Discussion. Redundant prose and unverified historical numerical summaries were removed to preserve the eight-page limit. Scientific qualifications remain in Results and Limitations; no unsupported priority claim was added.
