"""Strict parsing, masking, checkpoint and cache invariants without real weights."""

from dataclasses import replace

import numpy as np
import pytest
import torch

from oligo_engine.contracts import Observation
from oligo_engine.representations.rnafm import FrozenRNAFM, duplex_sequences


def observation(a="ACGT", b="UG"):
    def polymer(name, sequence):
        return name + "{" + ".".join(f"R({base})P" for base in sequence) + "}"

    return Observation(
        "id",
        polymer("RNA1", a) + "|" + polymer("RNA2", b) + "$$$$V2.0",
        "target",
        "siRNA",
        "",
        "",
    )


def fake_encoder(tmp_path):
    from fm import Alphabet

    alphabet = Alphabet.from_architecture("roberta_large", "rna")

    class FakeModel(torch.nn.Module):
        def forward(self, tokens, repr_layers):
            assert not self.training
            assert not torch.is_grad_enabled()
            values = tokens.float().unsqueeze(-1).expand(-1, -1, 640)
            return {"representations": {12: values}}

    encoder = FrozenRNAFM.__new__(FrozenRNAFM)
    encoder.model = FakeModel().eval()
    encoder.alphabet = alphabet
    encoder.batch_converter = alphabet.get_batch_converter()
    encoder.device = "cpu"
    encoder.cache_dir = tmp_path
    encoder._identity = "test-only-not-pretrained"
    encoder._config = {"name": "fixture"}
    return encoder


def test_projection_preserves_strands_and_rejects_unknown_bases():
    row = observation()
    assert duplex_sequences((row,)) == (("ACGU", "UG"),)
    with pytest.raises(ValueError, match="unsupported"):
        duplex_sequences((observation("ACGN"),))
    with pytest.raises(ValueError):
        duplex_sequences((replace(row, sequence="not HELM"),))
    with pytest.raises(ValueError, match="exactly"):
        duplex_sequences((replace(row, sequence="RNA1{R(A)P}$$$$V2.0"),))


def test_padding_special_tokens_and_strand_order_are_excluded(tmp_path):
    encoder = fake_encoder(tmp_path)
    vector = encoder.encode((observation(),))[0]
    first = np.mean([encoder.alphabet.get_idx(base) for base in "ACGU"])
    second = np.mean([encoder.alphabet.get_idx(base) for base in "UG"])
    np.testing.assert_array_equal(vector[:640], first)
    np.testing.assert_array_equal(vector[640:], second)
    assert vector.dtype == np.float32
    assert encoder.encode(())[0:0].shape == (0, 1280)


def test_cache_exact_hit_order_and_tampering(tmp_path):
    encoder = fake_encoder(tmp_path)
    a, b = observation(), observation("UU", "A")
    values = encoder.encode((a, b))
    np.testing.assert_array_equal(encoder.encode((b, a)), values[::-1])
    path = encoder._cache_path(a.sequence)
    with np.load(path, allow_pickle=False) as archive:
        content = dict(archive)
    content["vector"] = content["vector"] + 1
    np.savez_compressed(path, **content)
    with pytest.raises(ValueError, match="hash mismatch"):
        encoder.encode((a,))


def test_cache_identity_separates_representation_versions(tmp_path):
    encoder = fake_encoder(tmp_path)
    row = observation()
    encoder.encode((row,))
    old = encoder._cache_path(row.sequence)
    encoder._identity = "another-weight-or-pooling-identity"
    assert encoder._cache_path(row.sequence) != old
    assert encoder._load_cache(row.sequence) is None


def test_checkpoint_load_never_falls_back(tmp_path):
    with pytest.raises(FileNotFoundError):
        FrozenRNAFM(tmp_path / "missing.pth")
    bad = tmp_path / "bad.pth"
    bad.write_bytes(b"not pretrained weights")
    with pytest.raises(ValueError, match="SHA-256"):
        FrozenRNAFM(bad)
