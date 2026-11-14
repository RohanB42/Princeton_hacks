"""Provenance guard tests independent of network or scientific dependencies."""

from unittest.mock import patch

import pytest

from oligo_engine.audit_upstream import PINNED_REVISION, audit_checkout


def test_source_audit_rejects_wrong_revision_before_reading_data(tmp_path):
    with patch("subprocess.check_output", return_value="wrong-revision\n"):
        with pytest.raises(ValueError, match=PINNED_REVISION):
            audit_checkout(tmp_path)


def test_source_audit_rejects_modified_checkout(tmp_path):
    with patch("subprocess.check_output", side_effect=[PINNED_REVISION, " M split.py"]):
        with pytest.raises(ValueError, match="must be clean"):
            audit_checkout(tmp_path)
