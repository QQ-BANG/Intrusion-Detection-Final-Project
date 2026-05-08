# Train and evaluate the IDS classifiers.
# Two framings:
#   1) Binary  - normal vs. attack
#   2) 5-class - normal / dos / probe / r2l / u2r
# Models:
#   Logistic Regression, Random Forest, HistGradientBoosting, MLP, this is cool because I actually did something similar in my data inference class as far as training goes
#  Saves stuff to outputs/models, outputs/reports, outputs/figures.
as 
import argparse
import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_score

from . import config
from .evaluate import (
    evaluate_binary, results_table, save_results,
    multiclass_report, roc_curve_data, confusion,)
from .features import build_preprocessor, get_feature_matrix
from .visualize import (
    plot_confusion_matrix, plot_roc_curves, plot_feature_importance,)

log = logging.getLogger(__name__)


def build_models(random_state=config.RANDOM_STATE):
    # dict of name -> untrained sklearn estimator
    models = {}
    models["logreg"] = LogisticRegression(
        max_iter=2000, n_jobs=-1, random_state=random_state,
    )
    models["random_forest"] = RandomForestClassifier(
        n_estimators=200, max_depth=None, n_jobs=-1,
        random_state=random_state, class_weight="balanced_subsample",
    )
    models["hist_gbdt"] = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.1, max_depth=None,
        random_state=random_state,
    )

    models["mlp"] = MLPClassifier(
        hidden_layer_sizes=(128, 64), max_iter=60,
        early_stopping=True, random_state=random_state,
    )
    return models


def make_pipeline(estimator):
    return Pipeline([
        ("preprocess", build_preprocessor()),
        ("model", estimator),
    ])


# old name, keeping as an alias because some notebooks/tests import it
_make_pipeline = make_pipeline


def get_attack_proba(pipe, X):
    # try predict_proba, fall back to decision_function rescaled, otherwise nothing
    model = pipe.named_steps["model"]
    if hasattr(model, "predict_proba"):
        return pipe.predict_proba(X)[:, 1]
    if hasattr(model, "decision_function"):
        scores = pipe.decision_function(X)
        # rescale to [0,1] just so it plays nice with roc_auc_score
        lo, hi = scores.min(), scores.max()
        return (scores - lo) / (hi - lo + 1e-12)
    return None


def train_all(db_url=None, models_dir=None, figures_dir=None,
              reports_dir=None, cv_folds=0, sample_frac=None):
    # cv_folds > 1 ; also report stratified k-fold CV F1 on train
    # sample_frac in (0,1) -> subsample train for smoke tests
    if models_dir is None:
        models_dir = config.MODELS_DIR
    if figures_dir is None:
        figures_dir = config.FIGURES_DIR
    if reports_dir is None:
        reports_dir = config.REPORTS_DIR

    for d in (models_dir, figures_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)

    Xtr, ybtr, yftr, Xte, ybte, yfte = get_feature_matrix(db_url=db_url)

    if sample_frac is not None and 0 < sample_frac < 1.0:
        # use a deterministic sample, so reruns give the same numbers
        idx = (
            pd.Series(range(len(Xtr)))
              .sample(frac=sample_frac, random_state=config.RANDOM_STATE)
              .values
        )
        Xtr = Xtr.iloc[idx]
        ybtr = ybtr.iloc[idx]
        yftr = yftr.iloc[idx]
        log.info("Subsampled training set to %d rows", len(Xtr))

    #binary
    binary_results = []
    roc_data = {}
    cv_scores = {}

    for name, est in build_models().items():
        log.info("=== Binary: training %s ===", name)
        pipe = make_pipeline(est)
        pipe.fit(Xtr, ybtr)

        y_pred = pipe.predict(Xte)
        y_proba = get_attack_proba(pipe, Xte)
        res = evaluate_binary(name, ybte, y_pred, y_proba)
        binary_results.append(res)
        log.info("  %s -> acc=%.4f f1=%.4f auc=%.4f",
                 name, res.accuracy, res.f1, res.roc_auc)

        if y_proba is not None and not np.isnan(res.roc_auc):
            roc_data[name] = roc_curve_data(ybte, y_proba)

        cm = confusion(ybte, y_pred, labels=[0, 1])
        plot_confusion_matrix(
            cm, labels=["normal", "attack"],
            title="Binary confusion matrix - " + name,
            out_path=figures_dir / ("cm_binary_" + name + ".png"),
        )

        joblib.dump(pipe, models_dir / (name + "_binary.joblib"))

        if cv_folds and cv_folds > 1:
            try:
                skf = StratifiedKFold(n_splits=cv_folds, shuffle=True,
                                      random_state=config.RANDOM_STATE)
                cv = cross_val_score(pipe, Xtr, ybtr, cv=skf,
                                     scoring="f1", n_jobs=-1)
                cv_scores[name] = float(cv.mean())
                log.info("  %s -> %d-fold CV F1 = %.4f +/- %.4f",
                         name, cv_folds, cv.mean(), cv.std())
            except Exception as e:
                log.warning("CV failed for %s: %s", name, e)

    save_results(binary_results, reports_dir, stem="binary_results")
    if cv_scores:
        pd.Series(cv_scores).to_csv(
            reports_dir / "binary_cv_f1.csv", header=["cv_f1"],)

    if roc_data:
        plot_roc_curves(roc_data, figures_dir / "roc_binary.png")

    # feature importance from the random forest
    rf_pipe = joblib.load(models_dir / "random_forest_binary.joblib")
    rf_model = rf_pipe.named_steps["model"]
    pre = rf_pipe.named_steps["preprocess"]
    try:
        feat_names = pre.get_feature_names_out().tolist()
    except Exception:
        feat_names = ["f" + str(i) for i in range(rf_model.n_features_in_)]
    plot_feature_importance(
        feat_names, rf_model.feature_importances_,
        out_path=figures_dir / "feature_importance_rf.png",
    )

    # multiclass
    log.info("=== Multi-class: training Random Forest on attack family ===")
    rf_multi = make_pipeline(RandomForestClassifier(
        n_estimators=200, n_jobs=-1, random_state=config.RANDOM_STATE,
        class_weight="balanced_subsample",))
    rf_multi.fit(Xtr, yftr)
    y_pred_fam = rf_multi.predict(Xte)

    fam_labels = ["normal", "dos", "probe", "r2l", "u2r"]
    cm_fam = confusion(yfte, y_pred_fam, labels=fam_labels)
    plot_confusion_matrix(
        cm_fam, labels=fam_labels,
        title="Multi-class confusion matrix - Random Forest",
        out_path=figures_dir / "cm_multiclass_rf.png",)
    rep = multiclass_report(yfte, y_pred_fam, labels=fam_labels)
    with open(reports_dir / "multiclass_rf_report.json", "w") as fh:
        json.dump(rep, fh, indent=2)
    joblib.dump(rf_multi, models_dir / "random_forest_multiclass.joblib")

    # print a summary table to stdout
    df = results_table(binary_results)
    print()
    print("=== Binary results (test set) ===")
    print(df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    if cv_scores:
        print()
        print("=== Stratified CV F1 on train ===")
        for k, v in cv_scores.items():
            print("  " + k.ljust(14) + f"{v:.4f}")

    return df


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cv-folds", type=int, default=0,
                   help="if >1 also run stratified k-fold CV")
    p.add_argument("--sample-frac", type=float, default=None,
                   help="subsample the training set (smoke test)")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level,
                        format="%(levelname)s %(name)s: %(message)s")
    train_all(cv_folds=args.cv_folds, sample_frac=args.sample_frac)
    return 0


if __name__ == "__main__":
    sys.exit(main())
