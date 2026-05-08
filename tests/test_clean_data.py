import pandas as pd

from ids_pipeline import config
from ids_pipeline.clean_data import clean_dataframe


def _row(label="normal."):
    vals = {col: 0 for col in config.NSL_KDD_COLUMNS}
    vals.update({
        "protocol_type": "TCP", "service": "Http", "flag": "SF",
        "label": label, "difficulty": 21,
        "src_bytes": "100", "dst_bytes": "200",
    })
    return vals


def test_clean_strips_label_dot_and_lowercases_categoricals():
    df = pd.DataFrame([_row("Neptune.")])
    out = clean_dataframe(df)
    assert out.loc[0, "label"] == "neptune"
    assert out.loc[0, "protocol_type"] == "tcp"
    assert out.loc[0, "service"] == "http"


def test_clean_drops_duplicates():
    df = pd.DataFrame([_row(), _row(), _row("normal")])
    out = clean_dataframe(df)
    assert len(out) == 1


def test_clean_coerces_numeric_strings():
    df = pd.DataFrame([_row()])
    out = clean_dataframe(df)
    assert out.loc[0, "src_bytes"] == 100
    assert out["src_bytes"].dtype.kind in {"i", "u"}
