#  helpers used by train_models.py

import json
import logging
import math

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    roc_auc_score, roc_curve, confusion_matrix, classification_report,)

log = logging.getLogger(__name__)


# I started using a dataclass here, but then I needed to_csv via pandas, and a plain dict with as_dict()
class BinaryResult:
    def __init__(self, model, accuracy, precision, recall, f1, roc_auc):
        self.model = model
        self.accuracy = accuracy
        self.precision = precision
        self.recall = recall
        self.f1 = f1
        self.roc_auc = roc_auc

    def as_dict(self):
        return {
            "model": self.model,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "roc_auc": self.roc_auc,
        }


def evaluate_binary(name, y_true, y_pred, y_proba=None):
    p, r, f, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    auc = float("nan")
    if y_proba is not None:
        try:
            auc = roc_auc_score(y_true, y_proba)
        except ValueError:
            auc = float("nan")
    return BinaryResult(
        model=name,
        accuracy=accuracy_score(y_true, y_pred),
        precision=p,
        recall=r,
        f1=f,
        roc_auc=auc,)


def results_table(results):
    rows = [r.as_dict() for r in results]
    df = pd.DataFrame(rows)
    df = df.sort_values("f1", ascending=False).reset_index(drop=True)
    return df


def save_results(results, out_dir, stem="binary_results"):
    out_dir.mkdir(parents=True, exist_ok=True)
    df = results_table(results)
    csv_path = out_dir / (stem + ".csv")
    json_path = out_dir / (stem + ".json")
    df.to_csv(csv_path, index=False)
    with open(json_path, "w") as fh:
        json.dump([r.as_dict() for r in results], fh, indent=2)
    log.info("Wrote %s and %s", csv_path, json_path)
    return csv_path, json_path


def multiclass_report(y_true, y_pred, labels):
    return classification_report(
        y_true, y_pred, labels=labels, output_dict=True, zero_division=0,)


def roc_curve_data(y_true, y_proba):
    fpr, tpr, _ = roc_curve(y_true, y_proba)
    return fpr, tpr, roc_auc_score(y_true, y_proba)


def confusion(y_true, y_pred, labels=None):
    return confusion_matrix(y_true, y_pred, labels=labels)
