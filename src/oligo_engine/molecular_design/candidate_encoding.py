"""Label-free, position-independent sequence/chemistry features for proposals."""

import numpy as np

from .contracts import Design, Pattern


def encode_candidate(design: Design, pattern: Pattern, max_length: int) -> np.ndarray:
    """Encode the actual antisense strand, chemistry and terminal; pad with zeros."""
    value = np.zeros((max_length, 16), np.float32)
    for i, base in enumerate(design.sequence):
        value[i, "ACGT".index(base)] = 1
        value[i, 4 + ("DNA", "MOE", "OMe", "cEt").index(pattern.sugars[i])] = 1
        value[i, 8] = pattern.methyl_c[i]
        value[i, 9] = i < pattern.length - 1 and pattern.links[i] == "PS"
        value[i, 10] = i < pattern.length - 1 and pattern.links[i] == "PO"
        value[i, 11] = 1
        value[i, 12] = pattern.wing5 <= i < pattern.length - pattern.wing3
        value[i, 13 + ("none", "PO", "PS").index(design.terminal)] = 1
    return value
