# CS 210 Project Proposal: Intrusion Detection on NSL-KDD

**Course:** CS 210, Data Management for Data Science
**Authors:** *<your name(s) here>*
**Date:** *<submission date>*

## 1. Problem and why it matters

Cyber attacks against enterprise networks are a constant threat, and
the IBM 2023 *Cost of a Data Breach* report estimates the average
breach now costs about $4.45M. Network intrusion detection systems
(NIDS) sit at the perimeter of these networks and try to flag
malicious activity in real time. Older signature-based NIDS like
Snort or Suricata only detect attacks that match known signatures,
which is why a lot of recent research has moved towards
machine-learning based detectors that can in principle generalize to
new attacks.

The question we want to answer is:

> Given a stream of summarized TCP/IP connection records, can we
> train a supervised classifier that distinguishes normal traffic
> from attack traffic, and can we further classify the attacks into
> the four DARPA categories (DoS, Probe, R2L, U2R)?

This problem fits the CS 210 syllabus pretty cleanly because it
forces us to use all three layers we have studied: a relational
database, the data-cleaning / EDA stack in Python, and a few
supervised machine-learning models.

## 2. Why this is worth doing

The DARPA / KDD'99 corpus is over twenty years old, but its cleaned
version NSL-KDD is still the most-cited benchmark for IDS research
(more than a thousand peer-reviewed papers since 2009). Two recent
surveys, Ring et al. (2019) and Khraisat et al. (2019), confirm that
most new detection algorithms get compared on it, partly because
better datasets are mostly proprietary.

What we want to add is not a new model. It is the database step. A
lot of NSL-KDD papers just use the raw CSVs in pandas and never
build any kind of schema, even though in a real SOC the same
connection records would live in a SIEM with a structured schema
backing it. We design a normalized 3NF schema, load NSL-KDD into it,
and run our EDA queries through SQL rather than pandas wherever
possible. That makes the project a more honest end-to-end "data
management for data science" exercise.

Prior work we are building on:

* Tavallaee et al. (2009), introduced NSL-KDD.
* Belavagi and Muniyal (2016), Random Forest / SVM / Naive Bayes
  baselines on NSL-KDD.
* Vinayakumar et al. (2019), deep learning for NIDS.
* Pedregosa et al. (2011), scikit-learn.

Most of these focus only on the modelling step. The gap we are
filling is making the database, the cleaning, the EDA, and the
modelling reproducible from a single command, while respecting the
official train/test split (which is not i.i.d., and that is what
makes NSL-KDD genuinely hard to do well on).

## 3. Data

| Property     | Value |
|--------------|-------|
| Source       | NSL-KDD, public mirror on GitHub |
| Origin       | MIT Lincoln Lab DARPA 1998/1999 IDS Evaluation |
| Format       | Plain-text CSV, 43 columns |
| Records      | 125,973 train (`KDDTrain+.txt`) + 22,544 test (`KDDTest+.txt`) |
| Features     | 38 numeric + 3 categorical (`protocol_type`, `service`, `flag`) |
| Targets      | `label` (39 specific attack types), collapsed to 5 broad families |
| Accessibility | Confirmed: download script in `src/ids_pipeline/download_data.py` pulls both files in seconds; multiple mirrors |
| License      | Released by University of New Brunswick for academic use |

The 39 attack labels collapse into the four DARPA families plus
`normal`:

* DoS, denial of service (`neptune`, `smurf`, `back`, ...).
* Probe, surveillance and scanning (`nmap`, `satan`, ...).
* R2L, remote to local (`guess_passwd`, `ftp_write`, ...).
* U2R, user to root (`buffer_overflow`, `rootkit`, ...).

## 4. Methodology

### 4.1 Database design

Normalized 3NF schema in `sql/schema.sql`:

* dimension tables: `protocols`, `services`, `flags`,
  `attack_types` (the last one stores the 39-to-5 family mapping at
  the database level so we never have to recompute it later).
* fact table: `connections`, one row per network connection, with
  surrogate-key foreign keys into the dimensions.
* a view `v_connections_full` that does the joins for us.
* indexes on every FK and on `split` so the analytical queries are
  not painful.

We picked SQLite because it is zero-config and the whole DB is one
file (about 30 MB), so a grader can open it directly with `sqlite3`.
SQLAlchemy is used in Python so the same schema can move to
PostgreSQL with one URL change if we need to.

### 4.2 Cleaning and feature engineering

* strip the trailing dot from KDD'99-style labels (`"normal."`
  becomes `"normal"`);
* lowercase the categorical strings so `Http` and `http` collapse;
* coerce numeric columns and drop full duplicates;
* keep `num_outbound_cmds` (it is constant 0 in NSL-KDD, but we
  document it so the schema matches the spec);
* one-hot encode the three categoricals, standardize the 38
  numerics.

### 4.3 Models

Four classifiers covering the main families we studied:

| Family         | Concrete model        | Why we picked it |
|----------------|-----------------------|------------------|
| Linear         | Logistic Regression   | Fast, easy baseline |
| Bagging trees  | Random Forest (200)   | Non-linear, gives feature importance |
| Boosting trees | HistGradientBoosting  | Usually best on tabular data |
| Neural net    | MLP (128, 64)         | Sanity check that non-tree methods don't blow them away |

### 4.4 Evaluation

* Train on `KDDTrain+`, test on `KDDTest+`. The test split is
  touched once.
* Metrics: accuracy, precision, recall, F1, ROC-AUC for binary;
  full per-class report and confusion matrix for the 5-way version.
* Stratified 5-fold CV on the train split for variance estimates
  (`--cv-folds 5`).
* Feature importance plot from the Random Forest.
* Explicit discussion of class imbalance, since R2L and U2R are
  under 1% of the records.

### 4.5 Tooling and reproducibility

* Python 3.12, pandas, scikit-learn, SQLAlchemy, seaborn.
* One fixed random seed (`config.RANDOM_STATE = 42`).
* End-to-end CLI (`python -m ids_pipeline.run_pipeline`) plus three
  Jupyter notebooks for the report.
* `pytest` tests on a tiny synthetic corpus so the test suite runs
  without internet.

## 5. Risks

* Distribution shift. `KDDTest+` deliberately contains attack
  subtypes that are not in `KDDTrain+`, and published baselines top
  out around 80% accuracy because of it. We will frame this as a
  finding, not a failure.
* Class imbalance for R2L and U2R. We will use
  `class_weight=balanced` and report per-class metrics.
* Dataset age. We acknowledge this in the limitations section and
  cite more modern alternatives (CICIDS-2017, UNSW-NB15) for future
  work.

## 6. Deliverables

* the `src/ids_pipeline/` Python package and CLI;
* `sql/schema.sql` and `sql/example_queries.sql`;
* three notebooks (`01_eda.ipynb`, `02_database_queries.ipynb`,
  `03_modeling.ipynb`);
* this proposal and the final report under `docs/`;
* `tests/` unit tests, `requirements.txt`, and a README that
  explains how to run everything.

## 7. References

1. Lippmann, R., et al. *The 1999 DARPA off-line intrusion detection
   evaluation.* Computer Networks 34(4), 2000.
2. Tavallaee, M., et al. *A detailed analysis of the KDD CUP 99 data
   set.* IEEE CISDA, 2009.
3. Ring, M., et al. *A survey of network-based intrusion detection
   datasets.* Computers & Security 86, 2019.
4. Khraisat, A., et al. *Survey of intrusion detection systems:
   techniques, datasets and challenges.* Cybersecurity 2(1), 2019.
5. Pedregosa, F., et al. *Scikit-learn: Machine Learning in Python.*
   JMLR 12, 2011.
