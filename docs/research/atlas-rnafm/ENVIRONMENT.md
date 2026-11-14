# Optional Atlas research environment

This study uses Python3.11.13. Actual local `.venv-atlas` imports read-only packages
from the existing pinned OligoGym/RNAFM/core environments; only PyArrow21.0.0 was
installed locally. No main lockfile or shared environment was modified.

Observed packages: NumPy1.26.4, pandas2.2.3, scikit-learn1.4.0, PyTorch2.7.0,
XGBoost2.1.4, PyArrow21.0.0. A complete actual environment receipt is saved in
`artifacts/atlas-rnafm/environment-freeze.txt`. This borrowed-path runtime is a
local execution receipt, not a clean-install reproducibility claim.

For a standalone environment, start a Python3.11 virtualenv and install the listed
versions plus pytest/Ruff and the existing verified RNAFM dependencies. Obtain the
pinned RNA-FM source at348951516e0963d22bbb33b3c9fc18c89081d38e and the verified
checkpoint recorded in `docs/rnafm-provenance.md`. Add its source directory to
PYTHONPATH or install that pinned checkout. Native Atlas anchor reproduction also
requires pinned OligoGym at97f5b9f58d9e445a8ecb0218037af7465c3708c0 and its supported
runtime. The strict Atlas parser/classical models do not require OligoGym.

Run all study commands from the research worktree with:

```sh
PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv-atlas/bin/python SCRIPT
```

Execute in dependency order in a fresh artifact directory layout (commands refuse
to overwrite completed runs):

```sh
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
.venv-atlas/bin/python scripts/prepare_atlas_study.py --output artifacts/atlas-rnafm/preparation-v1
.venv-atlas/bin/python scripts/reproduce_atlas_linear.py --upstream artifacts/atlas-rnafm/upstream --output artifacts/atlas-rnafm/native-linear-anchor
.venv-atlas/bin/python scripts/run_atlas_classical.py --output artifacts/atlas-rnafm/classical-development-v1
.venv-atlas/bin/python scripts/profile_atlas_fm.py
.venv-atlas/bin/python scripts/run_atlas_fm.py --output artifacts/atlas-rnafm/fm-development-v1
.venv-atlas/bin/python scripts/run_atlas_acquisition.py --output artifacts/atlas-rnafm/acquisition-development-v1
MPLCONFIGDIR=artifacts/atlas-rnafm/mpl .venv-atlas/bin/python scripts/report_atlas_research.py
.venv-atlas/bin/python scripts/audit_atlas_research.py
```

Before the native anchor, clone the Atlas source at
`bb90c946013f183379da04678340e193088e5f99` into the indicated ignored upstream path.
FM scripts currently use the verified local checkpoint at
`/private/tmp/oligoal-rnafm-20261114/artifacts/rnafm-checkpoint/RNA-FM_pretrained.pth`.
The library adapter accepts any checkpoint path with matching identity, but these
local research scripts need that path provided or explicitly updated on another
machine. This portability limitation is not concealed as a one-command clean install.

Checks actually completed after the study:

```sh
# Existing core environment, without optional research package requirements:
PYTHONPATH=src /Users/rohanbutani/Desktop/proj/Princeton_hacks/.venv/bin/python -m pytest -q
# 160 passed

# Optional Atlas model/oracle tests and pure parser/policy tests:
PYTHONPATH=src .venv-atlas/bin/python -m pytest -q tests/atlas tests/test_rnafm_atlas_boundaries.py tests/test_rnafm_atlas_oracle.py tests/test_rnafm_aso.py
# 21 passed (14 also included in core suite; counts are not additive)
```

Optional tests follow existing `test_rnafm*` collection rules; no core conftest or
lockfile changes were necessary. Pure parser/policy tests run in core CI. Tests of
actual model updates and cached/batched parity are additionally backed by the real
checkpoint profile and full fit receipts, not just mocked/unit execution.

All checkpoints, caches and run outputs stay ignored under `artifacts/atlas-rnafm/`.
No downloaded upstream source, source-trained weights or generated rows are committed.
