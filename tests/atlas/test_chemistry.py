import pytest

from oligo_engine.atlas.chemistry import parse_helm


def test_chemistry_alignment_and_projection():
    x = parse_helm("RNA1{{[moe]([5meC])[sp].d(T).[cet](G)}}$$$$")
    assert x.natural_rna == "CUG"
    assert x.bases == ("5meC", "T", "G")
    assert x.sugars == ("MOE", "DNA", "cEt")
    assert x.links == ("PS", "PO", "END")
    assert x.terminal == "none"
    y = parse_helm("RNA1{[moe](C)[sp].d(T).[cet](G)}$$$$")
    assert x.natural_rna == y.natural_rna and x.identity != y.identity


@pytest.mark.parametrize(
    "bad",
    [
        "RNA1{{d(A).bad.d(T)}}$$$$",
        "RNA1{{d([unknown])}}$$$$",
        "RNA1{{[unknown](A)}}$$$$",
        "RNA1{{d(A)}}|RNA2{{d(T)}}$$$$",
        "RNA1{{d(A)..d(T)}}$$$$",
        "RNA1{{d(A)[sp]junk}}$$$$",
    ],
)
def test_no_silent_token_loss(bad):
    with pytest.raises(ValueError):
        parse_helm(bad)


def test_terminal_linkage_is_separate():
    a = parse_helm("RNA1{{d(A)[sp]}}$$$$")
    assert a.links == ("END",) and a.terminal == "PS"
    assert a.identity != parse_helm("RNA1{{d(A)}}$$$$").identity
