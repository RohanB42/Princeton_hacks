# Decisions and status

- Existing `main` repository and GitHub remote are preserved. Working project and import names are `oligo-design-engine` and `oligo_engine`.
- Python 3.11 and Poetry 2.1.4 are selected to match source-document environment claims. A real `poetry.lock` was resolved with Poetry 2.1.4; local installation and checks passed on Python 3.13.9, Ruff 0.12.12, and pytest 8.4.2. CI targets Python 3.11 but has not run yet. The scaffold needs only Ruff and pytest; no scientific dependency is installed.
- Source PDFs are context, not files to publish. Older v2 target-split headline text is superseded by v5 nucleobase headline protocol.
- No license or author attribution is chosen. Project code license and rights to upstream datasets/weights need owner review.
- Upstream integration, package revision, dataset handles, and experimental results have not been verified or implemented.
