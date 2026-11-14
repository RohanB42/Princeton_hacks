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

Optional checks:

```sh
PYTHONPATH=src .venv-atlas/bin/python -m pytest tests/atlas tests/test_rnafm_aso.py
```

`tests/atlas/test_boundaries.py` needs the optional pandas/XGBoost research runtime;
its placement/collection must be coordinated with the integrator before merging
into core CI. Pure chemistry parser tests need no FM or dataset downloads.

All checkpoints, caches and run outputs stay ignored under `artifacts/atlas-rnafm/`.
No downloaded upstream source, source-trained weights or generated rows are committed.
