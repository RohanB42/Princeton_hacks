"""Adapter integrity checks using tiny architecture-compatible synthetic backbones."""

from dataclasses import replace

import pytest

torch = pytest.importorskip("torch")
from torch import nn  # noqa: E402
from torch.nn import functional as F  # noqa: E402

from oligo_engine.contracts import Observation  # noqa: E402
from oligo_engine.models.rnafm_lora import (  # noqa: E402
    RNAFMLoRAPredictor,
    inject_qv_adapters,
)


class Alphabet:
    def get_batch_converter(self):
        def convert(rows):
            tokens = torch.zeros(
                len(rows), max(len(seq) for _, seq in rows) + 2, dtype=torch.long
            )
            for i, (_, seq) in enumerate(rows):
                tokens[i, 0] = 1
                tokens[i, 1 : len(seq) + 1] = torch.tensor(
                    ["ACGU".index(c) + 2 for c in seq]
                )
                tokens[i, len(seq) + 1] = 6
            return None, None, tokens

        return convert


class Tiny(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed = nn.Embedding(7, 8)
        layer = nn.Module()
        layer.self_attn = nn.Module()
        layer.self_attn.q_proj = nn.Linear(8, 8)
        layer.self_attn.v_proj = nn.Linear(8, 8)
        self.layers = nn.ModuleList([layer])

    def forward(self, tokens, repr_layers):
        x = self.embed(tokens)
        attention = self.layers[0].self_attn
        # Like upstream fused attention, directly access weights rather than forward.
        x = torch.tanh(F.linear(x, attention.q_proj.weight, attention.q_proj.bias))
        x = F.linear(x, attention.v_proj.weight, attention.v_proj.bias)
        return {"representations": {repr_layers[0]: x}}


def factory():
    with torch.random.fork_rng():
        torch.manual_seed(123)
        return Tiny(), Alphabet()


def rows():
    return tuple(
        Observation(str(i), seq, "target", "siRNA", "", "")
        for i, seq in enumerate(("AAAA", "CCCC", "GGGG", "UUUU", "ACGU", "UGCA"))
    )


def predictor(**kwargs):
    return RNAFMLoRAPredictor(
        factory,
        lambda records: [(r.sequence, r.sequence[::-1]) for r in records],
        {"checkpoint_sha256": "synthetic-fixture-only"},
        rank=2,
        hidden_size=8,
        layer=1,
        epochs=3,
        batch_size=2,
        **kwargs,
    )


def test_weight_parametrization_zero_start_and_real_updates():
    model, _ = factory()
    x = torch.ones(2, 3, dtype=torch.long)
    before = model(x, repr_layers=[1])["representations"][1].detach().clone()
    targets = inject_qv_adapters(model, 2, 4)
    assert len(targets) == 2
    after = model(x, repr_layers=[1])["representations"][1]
    torch.testing.assert_close(before, after, rtol=0, atol=0)
    after.sum().backward()
    trainable = [(name, p) for name, p in model.named_parameters() if p.requires_grad]
    assert all("parametrizations.weight.0." in name for name, _ in trainable)
    assert any(p.grad is not None and p.grad.abs().sum() > 0 for _, p in trainable)
    with pytest.raises(ValueError, match="fresh base"):
        inject_qv_adapters(model, 2, 4)


def test_fit_freezes_base_resets_each_budget_and_roundtrips(tmp_path):
    model = predictor()
    data = rows()
    labels = (0.0, 20.0, 40.0, 60.0, 80.0, 100.0)
    model.fit(data, labels)
    first = model.predict(data)
    assert model.fit_audit["base_unchanged"]
    assert model.fit_audit["adapter_changed"]
    assert model.fit_audit["labels_used"] == 6
    model.fit(data[:4], labels[:4])
    smaller = model.predict(data)
    fresh = predictor()
    fresh.fit(data[:4], labels[:4])
    assert smaller == fresh.predict(data)
    model.fit(tuple(reversed(data)), tuple(reversed(labels)))
    assert model.predict(data) == first
    path = tmp_path / "adapter.pt"
    checksum = model.save_adapter(path)
    restored = predictor()
    restored.load_adapter(path, checksum)
    assert restored.predict(data) == first
    with pytest.raises(ValueError, match="checksum"):
        restored.load_adapter(path, "bad")
    changed = predictor(seed=1)
    with pytest.raises(ValueError, match="identity"):
        changed.load_adapter(path, checksum)
    payload = torch.load(path, weights_only=True)
    assert all(
        key.startswith("head.") or "parametrizations.weight.0." in key
        for key in payload["state"]
    )


def test_invalid_labels_and_unfitted_prediction():
    model = predictor()
    with pytest.raises(RuntimeError):
        model.predict(rows())
    with pytest.raises(ValueError, match="finite"):
        model.fit(rows(), (0.0, 1.0, 2.0, 3.0, 4.0, float("nan")))
    with pytest.raises(ValueError, match="unique"):
        model.fit((rows()[0], replace(rows()[1], sample_id="0")), (1.0, 2.0))


def test_frozen_control_uses_same_initial_head_and_has_no_adapter_updates():
    adapted, frozen = predictor(), predictor(adapt_backbone=False)
    adapted._reset()
    frozen._reset()
    for left, right in zip(
        adapted.head.parameters(), frozen.head.parameters(), strict=True
    ):
        torch.testing.assert_close(left, right, rtol=0, atol=0)
    frozen.fit(rows(), (0.0, 20.0, 40.0, 60.0, 80.0, 100.0))
    assert frozen.fit_audit["base_unchanged"]
    assert not frozen.fit_audit["adapter_changed"]
    assert frozen.fit_audit["adapted_modules"] == []
