# cleaning + typing for the raw NSL-KDD csv files

import logging
import numpy as np
import pandas as pd

from . import config

log = logging.getLogger(__name__)


def load_raw(path):
    # path to KDDTrain+.txt 
    if not path.exists():
        raise FileNotFoundError(
            "Raw NSL-KDD file not found at " + str(path) +
            ". Run `python -m ids_pipeline.download_data` first." )
    df = pd.read_csv(path, header=None, names=config.NSL_KDD_COLUMNS)
    log.info("Loaded raw file %s -> shape=%s", path.name, df.shape)
    return df


# columns that are actually rates, so I want to keep them as floats instead of casting to int below
RATE_COLS = {
    "serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate",
    "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate",
    "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
}


def clean_dataframe(df):
    # lowercase the categorical strings 
    # replace +/-inf with NaN, fill NaN with 0
    # drop full duplicates 
    out = df.copy()

    # strip whitespace, the dot andlowercase
    out["label"] = out["label"].astype(str).str.strip().str.rstrip(".").str.lower()

    #  lowercase and strip
    for c in config.CATEGORICAL_COLS:
        out[c] = out[c].astype(str).str.strip().str.lower()

    # numerics
    numeric_cols = [c for c in out.columns
                    if c not in config.CATEGORICAL_COLS + ["label"]]
    for c in numeric_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    out = out.replace([np.inf, -np.inf], np.nan)

    n_missing = int(out.isna().sum().sum())
    if n_missing > 0:
        log.warning("Filling %d missing numeric cells with 0", n_missing)
        out[numeric_cols] = out[numeric_cols].fillna(0)

    # drop duplicates
    n_before = len(out)
    out = out.drop_duplicates().reset_index(drop=True)
    if len(out) != n_before:
        log.info("Dropped %d duplicate rows (%d -> %d)",
                 n_before - len(out), n_before, len(out))

    if "num_outbound_cmds" in out.columns and out["num_outbound_cmds"].nunique() == 1:
        log.info("`num_outbound_cmds` is constant; keeping it anyway for schema fidelity")

    # cast back to int
    int_cols = [c for c in numeric_cols if c not in RATE_COLS]
    for c in int_cols:
        out[c] = out[c].astype(np.int64)

    return out
