"""Pytest fixtures.

Builds a tiny synthetic NSL-KDD-shaped corpus so the tests don't
need network access.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ids_pipeline import config  # noqa: E402


_RATE_COLS = {
    "serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate",
    "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate",
    "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
}


def _synth_row(rng: np.random.Generator, label: str) -> dict:
    row = {}
    for col in config.NSL_KDD_COLUMNS:
        if col == "label":
            row[col] = label
        elif col == "protocol_type":
            row[col] = rng.choice(["tcp", "udp", "icmp"])
        elif col == "service":
            row[col] = rng.choice(["http", "smtp", "ftp", "domain_u",
                                   "private", "other"])
        elif col == "flag":
            row[col] = rng.choice(["SF", "S0", "REJ", "RSTR"])
        elif col in _RATE_COLS:
            row[col] = round(float(rng.random()), 2)
        elif col == "difficulty":
            row[col] = int(rng.integers(1, 22))
        else:
            row[col] = int(rng.integers(0, 100))
    return row


@pytest.fixture(scope="session")
def synthetic_raw_dir(tmp_path_factory) -> Path:
    rng = np.random.default_rng(0)
    labels = ["normal", "neptune", "smurf", "satan", "guess_passwd",
              "buffer_overflow", "back", "ipsweep"]
    train_rows = [
        _synth_row(rng, label) for label in labels for _ in range(40)
    ]
    test_rows = [
        _synth_row(rng, label) for label in labels for _ in range(15)
    ]
    df_train = pd.DataFrame(train_rows, columns=config.NSL_KDD_COLUMNS)
    df_test = pd.DataFrame(test_rows, columns=config.NSL_KDD_COLUMNS)

    raw = tmp_path_factory.mktemp("raw")
    df_train.to_csv(raw / "KDDTrain+.txt", header=False, index=False)
    df_test.to_csv(raw / "KDDTest+.txt", header=False, index=False)
    return raw


@pytest.fixture(scope="session")
def built_db(synthetic_raw_dir, tmp_path_factory) -> tuple[Path, str]:
    from ids_pipeline.build_database import build_database

    db_path = tmp_path_factory.mktemp("db") / "ids_test.sqlite"
    db_url = f"sqlite:///{db_path}"
    build_database(raw_dir=synthetic_raw_dir, db_url=db_url, db_path=db_path)
    return db_path, db_url
