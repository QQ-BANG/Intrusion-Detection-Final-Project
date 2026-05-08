# EDA and result plots. Saves PNGs to outputs/figures/ by default.

import logging

import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from . import config

log = logging.getLogger(__name__)

sns.set_theme(style="whitegrid", context="notebook")
FAMILY_ORDER = ["normal", "dos", "probe", "r2l", "u2r"]


def save(fig, out_dir, name):
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved figure %s", path)
    return path


def plot_class_balance(df, out_dir=None):
    if out_dir is None:
        out_dir = config.FIGURES_DIR
    fig, ax = plt.subplots(figsize=(8, 4.5))
    counts = df.groupby(["split", "attack_family"]).size().rename("n").reset_index()
    sns.barplot(data=counts, x="attack_family", y="n", hue="split",
                order=FAMILY_ORDER, ax=ax)
    ax.set_title("Connection counts by attack family")
    ax.set_xlabel("Attack family")
    ax.set_ylabel("Number of connections")
    # log scale or else i cant see it at all
    ax.set_yscale("log")
    return save(fig, out_dir, "01_class_balance.png")


def plot_protocol_distribution(df, out_dir=None):
    if out_dir is None:
        out_dir = config.FIGURES_DIR
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sub = df[df["split"] == "train"]
    counts = sub.groupby(["protocol_type", "attack_family"]).size().rename("n").reset_index()
    sns.barplot(data=counts, x="protocol_type", y="n", hue="attack_family",
                hue_order=FAMILY_ORDER, ax=ax)
    ax.set_title("Protocol vs. attack family (train)")
    ax.set_xlabel("Protocol")
    ax.set_ylabel("Number of connections")
    return save(fig, out_dir, "02_protocol_distribution.png")


def plot_top_services(df, out_dir=None, top_n=15):
    if out_dir is None:
        out_dir = config.FIGURES_DIR
    sub = df[(df["split"] == "train") & (df["is_attack"] == 1)]
    top = sub.groupby("service").size().sort_values(ascending=False).head(top_n).reset_index(name="n")
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=top, x="n", y="service", color="steelblue", ax=ax)
    ax.set_title("Top " + str(top_n) + " services targeted by attacks (train)")
    ax.set_xlabel("Number of attack connections")
    ax.set_ylabel("Service")
    return save(fig, out_dir, "03_top_services.png")


def plot_bytes_distribution(df, out_dir=None):
    if out_dir is None:
        out_dir = config.FIGURES_DIR
    sub = df[df["split"] == "train"].copy()
    # log scale because the byte counts span like 9 orders of magnitude
    sub["log_src_bytes"] = np.log1p(sub["src_bytes"])
    sub["log_dst_bytes"] = np.log1p(sub["dst_bytes"])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    sns.violinplot(data=sub, x="attack_family", y="log_src_bytes",
                   order=FAMILY_ORDER, ax=axes[0], inner="quartile", cut=0)
    axes[0].set_title("log(1 + src_bytes) by family")
    sns.violinplot(data=sub, x="attack_family", y="log_dst_bytes",
                   order=FAMILY_ORDER, ax=axes[1], inner="quartile", cut=0)
    axes[1].set_title("log(1 + dst_bytes) by family")
    fig.tight_layout()
    return save(fig, out_dir, "04_bytes_distribution.png")


def plot_correlation_heatmap(df, out_dir=None):
    if out_dir is None:
        out_dir = config.FIGURES_DIR
    sub = df[df["split"] == "train"].copy()
    rate_cols = [c for c in sub.columns if c.endswith("_rate")]
    extra = ["count", "srv_count", "src_bytes", "dst_bytes",
             "duration", "is_attack"]
    cols = rate_cols + extra
    corr = sub[cols].corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(corr, cmap="vlag", center=0, ax=ax,
                cbar_kws={"shrink": 0.7}, square=False)
    ax.set_title("Pearson correlation of rate / count features")
    return save(fig, out_dir, "05_correlation_heatmap.png")


def plot_confusion_matrix(cm, labels, title, out_path):
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=labels, yticklabels=labels, ax=ax, cbar=False)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(title)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved figure %s", out_path)
    return out_path


def plot_roc_curves(curves, out_path):
    fig, ax = plt.subplots(figsize=(6, 5))
    for name, vals in curves.items():
        fpr, tpr, auc_score = vals
        ax.plot(fpr, tpr, label=name + " (AUC=" + f"{auc_score:.3f}" + ")")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5) 
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("Binary IDS - ROC curves (test set)")
    ax.legend(loc="lower right")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved figure %s", out_path)
    return out_path


def plot_feature_importance(names, importances, out_path, top_n=20):
    order = np.argsort(importances)[::-1][:top_n]
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.barplot(x=importances[order], y=[names[i] for i in order],
                color="steelblue", ax=ax)
    ax.set_title("Top " + str(top_n) + " feature importances (Random Forest)")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved figure %s", out_path)
    return out_path
