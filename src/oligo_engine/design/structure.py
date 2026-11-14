"""An idealized ASO:RNA duplex, written as PDB for a viewer.

**This is a schematic, not a predicted structure.** No structure prediction is run
anywhere in this project. Coordinates come from textbook A-form helical parameters
applied to the designed sequence, so the picture shows length, register, gapmer
architecture and where flagged bases sit - and nothing about the real conformation
of any particular molecule. The PDB carries that warning in its REMARK records so
it travels with the file into PyMOL or anywhere else.

Per residue three pseudo-atoms are written: the backbone phosphate ``P``, the sugar
``C1'`` and a base centroid ``N1``. That is enough for a viewer to draw a recognisable
double helix and to colour by chemistry, and too little to be mistaken for an
all-atom model.
"""

from math import cos, pi, radians, sin

# Idealized A-form parameters (Arnott): the hybrid duplex an RNase H gapmer forms is
# intermediate between A and B, so these are indicative only.
RISE = 2.81
TWIST = radians(32.7)
PHOSPHATE_RADIUS = 8.8
SUGAR_RADIUS = 6.4
BASE_RADIUS = 3.2
# Angular offset of the complementary strand about the helix axis.
STRAND_OFFSET = radians(154.0)
PAIR = {"A": "U", "T": "A", "G": "C", "C": "G", "U": "A"}


def _atom(serial, name, residue, chain, index, x, y, z, element):
    return (
        # PDB column layout: 13-16 atom, 17 altLoc, 18-20 residue, 22 chain,
        # 23-26 sequence, 27 iCode, 31-38/39-46/47-54 coordinates, 77-78 element.
        f"ATOM  {serial:>5d} {name:<4s} {residue:>3s} {chain}{index:>4d}    "
        f"{x:>8.3f}{y:>8.3f}{z:>8.3f}  1.00  0.00          {element:>2s}"
    )


def _residue_name(base: str, strand: str, in_wing: bool, chemistry: str) -> str:
    if strand == "B":
        return {"A": "  A", "C": "  C", "G": "  G", "U": "  U"}.get(base, "  N")
    if in_wing:
        return "MOE" if chemistry == "ps_moe_gapmer" else "OMe"
    return {"A": " DA", "C": " DC", "G": " DG", "T": " DT"}.get(base, " DN")


def duplex_pdb(
    sequence: str,
    chemistry: str,
    wing5: int,
    wing3: int,
    title: str = "designed ASO",
) -> str:
    """Return PDB text for the ASO (chain A) paired with its target RNA (chain B)."""
    if not sequence:
        raise ValueError("A sequence is required")
    length = len(sequence)
    lines = [
        f"TITLE     IDEALIZED SCHEMATIC OF {title.upper()[:50]}",
        "REMARK   1 NOT A PREDICTED STRUCTURE. Coordinates are textbook A-form",
        "REMARK   1 helical parameters applied to the designed sequence. No",
        "REMARK   1 structure prediction, docking or energy minimisation was run.",
        "REMARK   1 Three pseudo-atoms per residue: P, C1', base centroid as N1.",
        f"REMARK   2 CHEMISTRY {chemistry}; wings {wing5} (5') and {wing3} (3');",
        f"REMARK   2 DNA core {length - wing5 - wing3} monomers; chain A is the ASO,",
        "REMARK   2 chain B the complementary target RNA, antiparallel.",
    ]
    serial = 1
    for index, base in enumerate(sequence):
        angle = index * TWIST
        height = index * RISE
        in_wing = index < wing5 or index > length - 1 - wing3
        residue = _residue_name(base, "A", in_wing, chemistry)
        for name, radius, element in (
            ("P", PHOSPHATE_RADIUS, "P"),
            ("C1'", SUGAR_RADIUS, "C"),
            ("N1", BASE_RADIUS, "N"),
        ):
            lines.append(
                _atom(
                    serial,
                    name,
                    residue,
                    "A",
                    index + 1,
                    radius * cos(angle),
                    radius * sin(angle),
                    height,
                    element,
                )
            )
            serial += 1
    # Chain B runs antiparallel: residue i of B pairs with residue (length-1-i) of A.
    for index in range(length):
        partner = length - 1 - index
        base = PAIR.get(sequence[partner], "N")
        angle = partner * TWIST + STRAND_OFFSET
        height = partner * RISE
        residue = _residue_name(base, "B", False, chemistry)
        for name, radius, element in (
            ("P", PHOSPHATE_RADIUS, "P"),
            ("C1'", SUGAR_RADIUS, "C"),
            ("N1", BASE_RADIUS, "N"),
        ):
            lines.append(
                _atom(
                    serial,
                    name,
                    residue,
                    "B",
                    index + 1,
                    radius * cos(angle),
                    radius * sin(angle),
                    height,
                    element,
                )
            )
            serial += 1
    lines.append("END")
    return "\n".join(lines) + "\n"


def helix_turns(length: int) -> float:
    return length * TWIST / (2 * pi)
