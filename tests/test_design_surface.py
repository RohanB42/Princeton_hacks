"""Design-surface invariants: chemistry fidelity, tiling, flags and the PDB schematic.

These run anywhere: nothing here needs the pinned upstream environment, a network
call or a measured label. Scoring itself is covered by the upstream-marked tests,
because it needs the fitted predictors.
"""

import pytest

from oligo_engine.design.candidates import (
    DESIGNS,
    build_helm,
    cpg_count,
    gc_fraction,
    guanine_distance_from_3prime,
    longest_g_run,
    reverse_complement,
    tile,
)
from oligo_engine.design.structure import duplex_pdb
from oligo_engine.design.transcripts import TranscriptError, from_sequence

TRANSCRIPT = "ATGGCGTCTCTACTGTTACGTCAGCTTACGGATCCGTAGCTAGCTAGCATCGATCGGGGATCCGA"


def test_reverse_complement_is_an_involution_and_rejects_junk():
    assert reverse_complement("ACGT") == "ACGT"
    assert reverse_complement("AAAC") == "GTTT"
    assert reverse_complement(reverse_complement(TRANSCRIPT)) == TRANSCRIPT
    assert reverse_complement("ACGU") == "ACGT"  # U is read as T
    with pytest.raises(ValueError):
        reverse_complement("ACGTX")


def test_candidates_hybridise_to_the_window_they_name():
    for chemistry in DESIGNS:
        for candidate in tile("G", "T1", TRANSCRIPT, chemistry=chemistry, step=3):
            window = TRANSCRIPT[candidate.start : candidate.end]
            assert candidate.target_window == window
            # The ASO must be the reverse complement of its target window, or it
            # would not hybridise to the transcript it claims to target.
            assert reverse_complement(candidate.sequence) == window
            assert len(candidate.sequence) == DESIGNS[chemistry]["length"]


def test_tiling_skips_ambiguous_windows_and_keeps_ids_unique():
    with_n = TRANSCRIPT[:20] + "N" + TRANSCRIPT[21:]
    candidates = tile("G", "T1", with_n, step=1)
    assert candidates, "expected some clean windows"
    assert all("N" not in c.target_window for c in candidates)
    assert len({c.candidate_id for c in candidates}) == len(candidates)
    assert len(candidates) < len(tile("G", "T1", TRANSCRIPT, step=1))


@pytest.mark.parametrize(
    "chemistry,wing_sugar,core_sugar",
    [("ps_moe_gapmer", "[moe]", "d"), ("ps_2ome_gapmer", "m", "d")],
)
def test_helm_matches_the_training_chemistry(chemistry, wing_sugar, core_sugar):
    design = DESIGNS[chemistry]
    sequence = "ACGT" * 6
    sequence = sequence[: design["length"]]
    helm = build_helm(sequence, chemistry)
    assert helm.startswith("RNA1{") and helm.endswith("}$$$$")
    units = helm[len("RNA1{") : -len("}$$$$")].split(".")
    assert len(units) == design["length"]
    assert all(unit.endswith("[sp]") for unit in units[:-1])  # phosphorothioate
    assert not units[-1].endswith("[sp]")  # the 3' terminus carries no linkage
    assert units[0].startswith(wing_sugar) and units[-1].startswith(wing_sugar)
    assert units[design["wing5"]].startswith(core_sugar)
    if chemistry == "ps_moe_gapmer":
        assert "[m5C]" in helm and "(C)" not in helm  # every cytosine is methylated
    else:
        assert "m(U)" in helm  # 2'OMe wings write thymine as uracil
        assert "[m5C]" not in helm


def test_helm_rejects_sequences_it_cannot_encode():
    with pytest.raises(ValueError):
        build_helm("ACGTN" * 4, "ps_moe_gapmer")
    with pytest.raises(ValueError):
        build_helm("ACGT", "ps_moe_gapmer")  # shorter than its own wings
    with pytest.raises(ValueError):
        build_helm("ACGT" * 5, "lna_gapmer")


def test_sequence_flags_follow_their_definitions():
    assert cpg_count("CGCG") == 2
    assert cpg_count("CCGG") == 1
    assert cpg_count("AAAA") == 0
    assert guanine_distance_from_3prime("AAAG") == 0
    assert guanine_distance_from_3prime("AGAA") == 2
    assert guanine_distance_from_3prime("AAAA") is None
    assert longest_g_run("AGGGTA") == 3
    assert longest_g_run("GAGAG") == 1
    assert gc_fraction("GCAT") == 0.5


def test_pdb_is_column_aligned_and_labelled_as_a_schematic():
    sequence = "CGTAACAGTAGAGACGCCA"
    pdb = duplex_pdb(sequence, "ps_moe_gapmer", 5, 4, "test")
    assert "NOT A PREDICTED STRUCTURE" in pdb
    atoms = [line for line in pdb.splitlines() if line.startswith("ATOM")]
    assert len(atoms) == len(sequence) * 3 * 2  # three pseudo-atoms, two strands
    for line in atoms:
        # Strict PDB columns: a viewer reads fixed positions, not whitespace.
        assert line[16] == " "  # altLoc empty, so the residue name starts at 18
        assert line[21] in "AB"
        int(line[6:11]), int(line[22:26])
        float(line[30:38]), float(line[38:46]), float(line[46:54])
        assert line[76:78].strip() in {"P", "C", "N"}
    assert sum(1 for line in atoms if line[21] == "A") == len(sequence) * 3
    assert {line[12:16].strip() for line in atoms} == {"P", "C1'", "N1"}


def test_pasted_sequences_are_accepted_as_fasta_or_raw():
    raw = from_sequence(TRANSCRIPT)
    assert raw.sequence == TRANSCRIPT and raw.species == "supplied"
    fasta = from_sequence(f">some header\n{TRANSCRIPT[:40]}\n{TRANSCRIPT[40:]}\n")
    assert fasta.sequence == TRANSCRIPT
    assert from_sequence(TRANSCRIPT.replace("T", "U")).sequence == TRANSCRIPT
    with pytest.raises(TranscriptError):
        from_sequence("ACGT")
    with pytest.raises(TranscriptError):
        from_sequence("ACGT!?" * 20)
