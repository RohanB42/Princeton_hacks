"""Stable content identities shared by prediction and evaluation artifacts."""

import hashlib
import json


def identity(value: object) -> str:
    """Hash JSON-compatible content without depending on Python hash seeds."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
