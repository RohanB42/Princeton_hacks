import numpy as np
import pandas as pd
import pytest

from oligo_engine.atlas.baselines import Classical, Features
from oligo_engine.atlas.splits import sequence_groups


def fixture():
    return pd.DataFrame(
        [
            {
                "source_row_id": str(i),
                "HELM Annotation": f"RNA1{{{{d({'ACGT'[i % 4]})[sp].d(T)}}}}$$$$",
                "USPTO ID": f"p{i % 3}",
                "natural_rna": str(i),
                "cell_line": "A",
                "cell_line_species": "human",
                "transfection_method": "Gymnosis",
                "dosage_nm": 100.0,
                "treatment_period_hrs": 24.0,
            }
            for i in range(12)
        ]
    )


def test_label_column_rejected_and_hidden_labels_cannot_fit():
    x = fixture()
    y = np.arange(12, dtype=float)
    with pytest.raises(ValueError):
        Classical("ridge").fit(x.assign(Inhibition_pct=y), y)
    a = Classical("ridge").fit(x, y)
    b = Classical("ridge").fit(x.copy(), y.copy())
    np.testing.assert_allclose(a.predict(x), b.predict(x))
    assert a.fit_ids == x.source_row_id.tolist()


def test_context_fit_excludes_unseen_category():
    x = fixture()
    f = Features().fit(x)
    assert "UNSEEN" not in f.context.named_transformers_["cat"].categories_[0]
    assert np.isfinite(f.transform(x.assign(cell_line="UNSEEN")).data).all()


def test_near_sequence_components():
    s = ["AAAAAA", "AAAAAC", "AAAACC", "CCCCCC", "GAAAAA"]
    g = sequence_groups(s)
    assert g[0] == g[1] == g[2] == g[4]
    assert g[3] != g[0]
