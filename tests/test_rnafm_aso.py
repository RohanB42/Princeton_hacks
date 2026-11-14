"""ASO chemistry fusion invariants in the optional RNA-FM runtime."""

import torch

from oligo_engine.models.aso_rnafm import ChemistryHead


def test_masked_pooling_and_chemistry_alignment():
    torch.manual_seed(91)
    head = ChemistryHead(context_dim=2, hidden=4).eval()
    h = torch.randn(1, 2, 4)
    mask = torch.ones(1, 2, dtype=torch.bool)
    base = torch.tensor([[0, 1]])
    sugar = torch.tensor([[0, 1]])
    link = torch.tensor([[0, 2]])
    terminal = torch.tensor([0])
    context = torch.zeros(1, 2)
    a = head(h, mask, base, sugar, link, terminal, context)
    hp = torch.cat([h, torch.randn(1, 3, 4)], dim=1)
    mp = torch.tensor([[1, 1, 0, 0, 0]], dtype=torch.bool)
    bp = torch.tensor([[0, 1, 6, 6, 6]])
    sp = torch.tensor([[0, 1, 5, 5, 5]])
    lp = torch.tensor([[0, 2, 3, 3, 3]])
    b = head(hp, mp, bp, sp, lp, terminal, context)
    torch.testing.assert_close(a, b)
    c = head(h, mask, base, torch.tensor([[1, 0]]), link, terminal, context)
    assert not torch.equal(a, c)


def test_terminal_and_modified_base_tracks_affect_representation():
    torch.manual_seed(92)
    head = ChemistryHead(1, 4).eval()
    h = torch.zeros(1, 1, 4)
    mask = torch.ones(1, 1, dtype=torch.bool)
    sugar = torch.tensor([[0]])
    link = torch.tensor([[2]])
    context = torch.zeros(1, 1)
    a = head(h, mask, torch.tensor([[1]]), sugar, link, torch.tensor([0]), context)
    b = head(h, mask, torch.tensor([[5]]), sugar, link, torch.tensor([0]), context)
    c = head(h, mask, torch.tensor([[1]]), sugar, link, torch.tensor([2]), context)
    assert not torch.equal(a, b) and not torch.equal(a, c)
