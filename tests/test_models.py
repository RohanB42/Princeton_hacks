"""Core checks for the baseline predictor boundary; run without OligoGym."""

import subprocess
import sys

from oligo_engine.models.baseline import KERNEL_GRID, LENGTH_SCALE_BOUNDS


def run_python(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )


def test_baseline_modules_import_without_loading_oligogym():
    result = run_python(
        "import sys, oligo_engine.models.baseline, oligo_engine.features.upstream;"
        "print('oligogym' in sys.modules)"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_missing_oligogym_fails_loudly_not_silently():
    result = run_python(
        "import sys; sys.modules['oligogym'] = None\n"
        "from oligo_engine.features.upstream import (\n"
        "    UpstreamEnvironmentError, verify_upstream_environment)\n"
        "try:\n"
        "    verify_upstream_environment()\n"
        "except UpstreamEnvironmentError as error:\n"
        "    print('LOUD', error)\n"
        "else:\n"
        "    print('SILENT')\n"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("LOUD"), result.stdout


def test_kernel_grid_is_the_preregistered_one():
    assert KERNEL_GRID == (
        ("rbf", 1.0),
        ("rbf", 4.0),
        ("rbf", 8.0),
        ("rbf", 16.0),
        ("matern15", 8.0),
        ("matern25", 8.0),
    )
    assert LENGTH_SCALE_BOUNDS == (1.0, 100.0)
