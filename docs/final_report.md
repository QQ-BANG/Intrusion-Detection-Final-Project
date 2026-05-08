# CS 210 Final Report: Intrusion Detection on NSL-KDD

**Course:** CS 210, Data Management for Data Science
**Authors:** *Q'Andre Small*
**Date:** *5/7/26*
**Repository:** *<GitHub URL>*

## Abstract

I built an end-to-end machine-learning pipeline for the network
intrusion detection that combines a normalized relational database
(SQLite, 3NF), a Python data-science layer, and four supervised
classifiers. Using NSL-KDD, the standard cleaned version of the MIT
Lincoln Lab DARPA 1998/1999 evaluation, our best model
(`HistGradientBoostingClassifier`) reaches F1 = 0.793 and
ROC-AUC = 0.962 on the official `KDDTest+` split for the binary
normal vs. attack task. A Random Forest trained to classify the
Four DARPA attack families get a macro-F1 of about 0.66, with most
of its mistakes on the rare R2L and U2R classes. The database layer
is not just decoration: it gives us a clean, queryable contract
between the messy raw text files and the modeling code, and the SQL
queries surface exactly the kind of distributional gaps that limit
IDS accuracy in practice.

## 1. Problem and background

### 1.1 Why bother

Network intrusion detection is one of the main lines of defense for
modern enterprises. The IBM 2023 *Cost of a Data Breach* report
estimates the average breach at $4.45M, and Verizon's *Data Breach
Investigations Report* shows that detection time is the single
biggest predictor of total damage. Signature-based NIDS (Snort,
Suricata only catches known attacks, which is why two decades of
research have gone into learning-based detection.

### 1.2 How this fits the course

The project hits the three layers I covered in CS 210:

* Data management. A normalized 3NF schema, dimension tables,
  surrogate keys, indexes, joins, views, and parameterized queries.
* Data science. Cleaning, profiling, visualizing, and reporting on a
  non-trivial real dataset.
* Machine learning. Supervised classification with proper
  preprocessing pipelines, train/test discipline, and decent metrics.

### 1.3 Related work

* Lippmann et al. (2000), the original DARPA evaluation.
* Tavallaee et al. (2009) introduced NSL-KDD and should that KDD'99
  was severely biased by duplicates.
* Belavagi and Muniyal (2016), RF / SVM / Naive Bayes on NSL-KDD,
  with F1 around 0.78 to 0.81.
* Vinayakumar et al. (2019), deep learning on multiple IDS datasets,
  with similar ceilings on NSL-KDD.
* Ring et al. (2019), Khraisat et al. (2019), survey papers.

The general consensus is that NSL-KDD baselines plateau near
F1 = 0.80 because `KDDTest+` deliberately contains attack subtypes
that are not in `KDDTrain+`, in order to test generalization. Our
results match this.

## 2. Data and methodology

### 2.1 Dataset

NSL-KDD has 125,973 training and 22,544 test connection records,
each with 41 features (38 numeric and 3 categorical:
`protocol_type`, `service`, `flag`) and a string label (39 specific
attack types or `normal`). I collapsed the 39 labels into the four
DARPA families plus `normal` using the mapping in
`src/ids_pipeline/config.py::ATTACK_FAMILY`.

### 2.2 Relational schema (3NF)

See `sql/schema.sql`. Dimension tables (`protocols`, `services`,
`flags`, `attack_types`) deduplicate the categorical strings, and
the fact table `connections` references them by surrogate FK. The
`attack_types` table also stores the family and `is_attack` flag, so
analytical queries do not have to re-encode the 39-to-5 mapping
every time. A view `v_connections_full` joins the fact table to its
dimensions for ad-hoc analytics.

I picked SQLite because it is zero-configuration, and the whole DB
is one file (about 30 MB), but the SQLAlchemy ORM definition in
`src/ids_pipeline/schema.py` would also work against PostgreSQL.

### 2.3 Cleaning

* Strip the trailing dot from KDD'99-style labels.
* LoIrcase the categorical strings (`Http` becomes `http`).
* Coerce numeric columns; replace +/- inf with NaN, then 0.
* Drop fully duplicated rows. NSL-KDD has very few of these by
  design, but I still do the check.
* Document `num_outbound_cmds`, which is constant 0 in the corpus.
  I keep it so the schema still matches the published spec.

### 2.4 Feature engineering

A scikit-learn `ColumnTransformer`:

* `StandardScaler` on the 38 numeric features;
* `OneHotEncoder(handle_unknown="ignore")` on the 3 categoricals.

After one-hot encoding, the feature dimensionality is around 120
(the exact number depends on which `service` values appear in
train).

### 2.5 Models

| Model                | Why included                       | Key hyperparameters |
|----------------------|------------------------------------|---------------------|
| Logistic Regression  | Linear baseline                    | `max_iter=2000` |
| Random Forest        | Non-linear plus feature importance | 200 trees, `class_Iight=balanced_subsample` |
| HistGradientBoosting | Usually best on tabular data       | 300 iters, lr=0.1 |
| MLP                  | Non-tree comparison                | (128, 64), early stopping |

All four are trained as binary classifiers. The Random Forest is
Also trained on the 5-class family target.

### 2.6 Evaluation protocol

* Train on `KDDTrain+`, test on `KDDTest+`. The test set is touched
  exactly once.
* Metrics: accuracy, precision, recall, F1, ROC-AUC for binary; full
  per-class report and confusion matrix for the multi-class version.
* Optional 5-fold stratified CV on the train split for variance
  estimates (`--cv-folds 5`).

## 3. Results

### 3.1 Class distribution

`outputs/figures/01_class_balance.png` shows the imbalance: DoS
dominates, R2L and U2R are under 1% of records. R2L is also enriched
in `KDDTest+` relative to `KDDTrain+`, which is part of why every
model struggles on it.

### 3.2 Categorical structure

`02_protocol_distribution.png` shows that `icmp` connections are
almost entirely DoS (Smurf-style flooding).
`03_top_services.png` shows `private`, `http`, and `domain_u` as
the most-targeted services, which align with the kind of flood
and scan patterns you would expect.

### 3.3 Numeric structure

`04_bytes_distribution.png` (log-scale violin plots) shows that DoS
connections have very small `src_bytes`, which is consistent with
SYN floods, while R2L connections often look superficially normal.
That is part of why R2L is so hard to detect.

`05_correlation_heatmap.png` shows that the `*_serror_rate` and
`*_srv_serror_rate` blocks are tightly correlated, as are the
`dst_host_*` views of the same statistics. That redundancy is
probably why a linear model still does okay here.

### 3.4 Binary detection on `KDDTest+`

| Model                | Acc   | Prec  | Recall |  F1   |  AUC  |
|----------------------|------:|------:|-------:|------:|------:|
| HistGradientBoosting | 0.800 | 0.969 |  0.670 | 0.793 | 0.962 |
| MLP (128, 64)        | 0.788 | 0.937 |  0.673 | 0.783 | 0.924 |
| Random Forest (200)  | 0.770 | 0.969 |  0.616 | 0.753 | 0.961 |
| Logistic Regression  | 0.754 | 0.918 |  0.623 | 0.742 | 0.791 |

(See `outputs/reports/binary_results.csv`.)

A few observations:

* All four models share the same failure mode. Precision is very
  high (around 0.97), but recall is only around 0.65. They miss
  attacks more than they fire false alarms, which is at least the
  better of the two failure modes for a SOC.
* Tree ensembles win on AUC by a wide margin over the linear
  baseline (0.96 vs 0.79), so there is a lot of non-linear structure
  in the feature space.
* The MLP edges out RF on F1 but trails on AUC. Neural nets are
  worse-calibrated probabilistic models out of the box, so this is
  not surprising.

### 3.5 Multi-class results (Random Forest, 5 classes)

See `outputs/reports/multiclass_rf_report.json` and
`outputs/figures/cm_multiclass_rf.png`.

* `normal` and `dos` are recovered almost perfectly (over 0.95 F1).
* `probe` is recovered Ill (over 0.7 F1), thanks to the `count` and
  `srv_count` features.
* `r2l` and `u2r` are heavily under-recalled. Most of the attacks in
  those families end up classified as `normal` because `KDDTest+`
  contains attack subtypes (`snmpguess`, `httptunnel`, `mscan`, ...)
  that simply do not appear in `KDDTrain+`. This is the Ill-known
  NSL-KDD ceiling.

### 3.6 Feature importance

`outputs/figures/feature_importance_rf.png` ranks the top features.
Lining up with prior work, the top discriminators are `src_bytes`,
`dst_bytes`, `service=http` / `private`, `flag=SF` / `S0`, `count`,
and `serror_rate`. So the schema's categorical dimensions are
pulling real predictive light.

## 4. Discussion and limitations

### 4.1 What I did

* The pipeline runs end-to-end from a single command and is
  deterministic (fixed seed).
* The database layer is real: 3NF, indexes, a view, and the FK
  enforcement is on. It is not just a CSV with a `.sqlite`
  extension.
* Four model families are compared on identical splits with the
  full metric suite plus confusion matrices and ROC.
* Test discipline. `KDDTest+` is touched once.
* The Streamlit UI (see `app/streamlit_app.py`) makes the project
  demoable: the same trained models run live against
  user-constructed connections, which makes the "what does an IDS
  actually do" story much more concrete than a static report.

### 4.2 What I did not do

* Dataset age. NSL-KDD was generated from 1998/1999 traffic, and
  the attack landscape has changed a lot since then (encrypted
  traffic, IoT, ransomware, and so on). Numbers do not directly
  carry over to modern networks.
* Distribution shift. `KDDTest+` contains attack subtypes that are
  absent from train, which puts a hard ceiling around 80% on
  accuracy. I frame this as a finding, but it is also a
  limitation.
* Aggregated features only. NSL-KDD gives per-connection summaries,
  not raw packets, so I cannot evaluate payload-based detection.
* Single train/test split. I add a 5-fold CV on the *train* split
  for variance estimates, but the test split is fixed.

### 4.3 Future work

* Re-run on CICIDS-2017 or UNSW-NB15 to evaluate on more modern
  traffic.
* Add a streaming evaluation that updates the model online to
  measure concept drift.
* Move the database to PostgreSQL and add row-level security for a
  multi-tenant SOC scenario.
* Try cost-sensitive learning that is explicitly tuned to a
  false-alarm budget.

## 5. Conclusion

I built a complete, reproducible cybersecurity data-science
pipeline that takes raw NSL-KDD text files all the way through a
normalized relational database, exploratory analysis, and four
supervised models. Our best model reaches F1 = 0.793 and AUC = 0.962
on the held-out `KDDTest+` set, which lines up with published
baselines. The bigger lesson is how much easier the database layer
makes everything downstream, from EDA queries to feature engineering
to per-class evaluation.

## 6. References

(See proposal.)


