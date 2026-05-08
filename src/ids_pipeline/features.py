# feature loading and sklearn preprocessing pipeline

import logging

import pandas as pd
from sqlalchemy import text
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from . import config
from .schema import get_engine

log = logging.getLogger(__name__)


# all numeric features used for the models
NUMERIC_FEATURES = [
    "duration", "src_bytes", "dst_bytes", "land", "wrong_fragment", "urgent",
    "hot", "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root", "num_file_creations",
    "num_shells", "num_access_files", "num_outbound_cmds",
    "is_host_login", "is_guest_login", "count", "srv_count",
    "serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate",
    "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate",
    "dst_host_count", "dst_host_srv_count", "dst_host_same_srv_rate",
    "dst_host_diff_srv_rate", "dst_host_same_src_port_rate",
    "dst_host_srv_diff_host_rate", "dst_host_serror_rate",
    "dst_host_srv_serror_rate", "dst_host_rerror_rate",
    "dst_host_srv_rerror_rate",
]

CATEGORICAL_FEATURES = ["protocol_type", "service", "flag"]

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def load_dataframe(db_url=None, split=None):
    # pulls connection rows joined with their dim tables.
    # split=None -> all rows. split='train' or 'test' filters.
    if db_url is None:
        db_url = config.DB_URL
    engine = get_engine(db_url)

    if split is None:
        sql = "SELECT * FROM v_connections_full"
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn)
    else:
        sql = "SELECT * FROM v_connections_full WHERE split = :split"
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params={"split": split})


def split_features_targets(df):
    X = df[FEATURE_COLUMNS].copy()
    y_binary = df["is_attack"].astype(int)
    y_family = df["attack_family"].astype(str)
    return X, y_binary, y_family


def build_preprocessor():
    # standardize the 38 numerics
    #had to use ohe for older version of sklearns
    try:
        ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        ohe = OneHotEncoder(handle_unknown="ignore", sparse=False)

    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", ohe, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False, )


def get_feature_matrix(db_url=None):
    # returns (Xtrain, ybin_train, yfam_train, Xtest, ybin_test, yfam_test)
    train = load_dataframe(db_url=db_url, split="train")
    test = load_dataframe(db_url=db_url, split="test")
    Xtr, ybtr, yftr = split_features_targets(train)
    Xte, ybte, yfte = split_features_targets(test)
    log.info("Train X=%s, Test X=%s", Xtr.shape, Xte.shape)
    return Xtr, ybtr, yftr, Xte, ybte, yfte


# backward compatability aliases 
_NUMERIC_FEATURES = NUMERIC_FEATURES
_CATEGORICAL_FEATURES = CATEGORICAL_FEATURES
