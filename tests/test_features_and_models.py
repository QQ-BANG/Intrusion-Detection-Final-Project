import numpy as np
from sklearn.linear_model import LogisticRegression

from ids_pipeline.features import (
    build_preprocessor, get_feature_matrix, FEATURE_COLUMNS,
)
from ids_pipeline.evaluate import evaluate_binary
from ids_pipeline.train_models import _make_pipeline


def test_feature_matrix_loads(built_db):
    _, url = built_db
    Xtr, ybtr, yftr, Xte, ybte, yfte = get_feature_matrix(db_url=url)
    assert Xtr.shape[1] == len(FEATURE_COLUMNS)
    assert len(Xtr) == len(ybtr) == len(yftr)
    assert len(Xte) == len(ybte) == len(yfte)
    assert set(ybtr.unique()).issubset({0, 1})


def test_preprocessor_one_hot_and_scales(built_db):
    _, url = built_db
    Xtr, _, _, _, _, _ = get_feature_matrix(db_url=url)
    pre = build_preprocessor()
    Z = pre.fit_transform(Xtr)
    assert Z.shape[0] == len(Xtr)
    assert Z.shape[1] >= 37


def test_logreg_pipeline_trains_and_predicts(built_db):
    _, url = built_db
    Xtr, ybtr, _, Xte, ybte, _ = get_feature_matrix(db_url=url)
    pipe = _make_pipeline(LogisticRegression(max_iter=500))
    pipe.fit(Xtr, ybtr)
    y_pred = pipe.predict(Xte)
    y_proba = pipe.predict_proba(Xte)[:, 1]
    res = evaluate_binary("logreg", ybte, y_pred, y_proba)
    assert 0.0 <= res.accuracy <= 1.0
    assert 0.0 <= res.f1 <= 1.0
    assert np.isfinite(res.roc_auc)
