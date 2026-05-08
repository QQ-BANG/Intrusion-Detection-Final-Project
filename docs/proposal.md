# CS 210 Project Proposal: Intrusion Detection on NSL-KDD

**Course:** CS 210, Data Management for Data Science
**Authors:** *Q'Andre Small*
**Date:** *5/7*

## 1. Problem and why it matters

Cyber attacks against enterprise networks are a constant threat, and
The IBM 2023 *Cost of a Data Breach* report estimates the average
breach now costs about $4.45M. Network intrusion detection systems
(NIDS) sit at the perimeter of these networks and try to flag
malicious activity in real time. Older signature-based NIDS like
Snort or Suricata only detects attacks that match known signatures,
which is why a lot of recent research has moved towards
machine-learning-based detectors that can, in principle, generalize to
new attacks.

The question I  want to answer is:

> Given a stream of summarized TCP/IP connection records, can we
> train a supervised classifier that distinguishes normal traffic
> from attack traffic, and can we further classify the attacks into
> the four DARPA categories (DoS, Probe, R2L, U2R)?

This problem fits the CS 210 syllabus pretty cleanly because it
forces us to use all three layers I have studied: a relational
database, the data-cleaning / EDA stack in Python, and a few
supervised machine-learning models.

## 2. Why this is worth doing

The DARPA / KDD'99 corpus is over twenty years old, but its cleaned
Version NSL-KDD is still the most-cited benchmark for IDS research
(more than a thousand peer-reviewed papers since 2009). Two recent
surveys, Ring et al. (2019) and Khraisat et al. (2019), confirm that
Most new detection algorithms get compared on it, partly because
Better datasets are mostly proprietary.

What I want to add is not a new model. It is the database step. A
lot of NSL-KDD papers just use the raw CSVs in pandas and never
build any kind of schema, even though in a real SOC, the same
Connection records would live in a SIEM with a structured schema
backing it. I designed a normalized 3NF schema, loaded NSL-KDD into it,
and run our EDA queries through SQL rather than pandas wherever
possible. That makes the project a more honest end-to-end "data
management for data science" exercise.

Prior work I'm building on:

* Tavallaee et al. (2009), introduced NSL-KDD.
* Belavagi and Muniyal (2016), Random Forest / SVM / Naive Bayes
  baselines on NSL-KDD.
* Vinayakumar et al. (2019), deep learning for NIDS.
* Pedregosa et al. (2011), scikit-learn.

Most of these focus only on the modeling step. The gap I am
filling is making the database, the cleaning, the EDA, and the
modeling reproducible from a single command, while respecting the
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
| License      | Released by the University of New Brunswick for academic use |

The 39 attack labels collapse into the four DARPA families plus
`normal`:

* DoS, denial of service (`neptune`, `smurf`, `back`, ...).
* Probe, surveillance, and scanning (`nmap`, `satan`, ...).
* R2L, remote to local (`guess_passwd`, `ftp_write`, ...).
* U2R, user to root (`buffer_overflow`, `rootkit`, ...).

## 4. Methodology

### 4.1 Database design

Normalized 3NF schema in `sql/schema.sql`:

The database is organized with several dimension tables: protocols, services, flags, and attack_types. The attack_types table is especially important because it stores the 39-to-5 attack family mapping directly in the database, so the project does not need to recompute that relationship every time the data is loaded or queried. The main fact table is connections, where each row represents one network connection. Instead of storing repeated text values directly in this table, it uses surrogate-key foreign keys that point back to the dimension tables.

To make the database easier to analyze, I also created a view called v_connections_full that performs the necessary joins between the fact and dimension tables. This lets me query the full connection records without having to manually rewrite the joins each time. I also add indexes on every foreign key and on the split column, which improves performance when filtering by train/test split or joining the connection records back to their related protocol, service, flag, and attack type information.

I picked SQLite because it is zero-config and the whole DB is one
file (about 30 MB), so a grader can open it directly with `sqlite3`.
SQLAlchemy is used in Python, so the same schema can be moved to
PostgreSQL, with one URL change if needed.

### 4.2 Cleaning and feature engineering

During preprocessing, I strip the trailing dot from KDD’99-style labels, so a label like "normal." becomes "normal". I also lowercase all categorical strings, which collapses values such as Http and http into the same category rather than treating them as separate values. After that, I coerce the numeric columns into proper numeric types and drop fully duplicated rows as a basic data-cleaning step. I keep the num_outbound_cmds column even though it is constant at 0 in NSL-KDD, because documenting and preserving it keeps the dataset schema aligned with the published specification. Finally, I one-hot encode the three categorical features and standardize the 38 numeric features so the models receive a clean, consistent feature matrix.

### 4.3 Models

Four classifiers covering the main families:

| Family         | Concrete model        | Why I picked it |
|----------------|-----------------------|------------------|
| Linear         | Logistic Regression   | Fast, easy baseline |
| Bagging trees  | Random Forest (200)   | Non-linear, gives feature importance |
| Boosting trees | HistGradientBoosting  | Usually best on tabular data |
| Neural net    | MLP (128, 64)         | Sanity check that non-tree methods don't blow them away |

### 4.4 Evaluation

The evaluation setup trains the models on KDDTrain+ and tests them on KDDTest+, with the test split only being touched once during the final evaluation. For the binary classification task, I report accuracy, precision, recall, F1-score, and ROC-AUC to evaluate the model's overall correctness and its ability to separate normal traffic from attacks. For the 5-way classification version, I include a full per-class report and a confusion matrix, making it easier to see which attack families are being detected well and which are being confused.

I also run stratified 5-fold cross-validation on the training split using --cv-folds 5 to get variance estimates without repeatedly using the test set. In addition, I include a Random Forest feature importance plot to help explain which features are contributing most to the model’s decisions. Finally, I explicitly discuss class imbalance because the r2l and u2r categories make up less than 1% of the records. This imbalance matters because a model can look strong overall while still performing poorly on the rarest and often most important attack families.

### 4.5 Tooling and reproducibility

The project is built using Python 3.12 with common data science and machine learning libraries such as pandas, scikit-learn, SQLAlchemy, and seaborn. To keep the results reproducible, I use one fixed random seed, config.RANDOM_STATE = 42, throughout the pipeline. The full workflow can be run from a single command using python -m ids_pipeline.run_pipeline, while the report is supported by three Jupyter notebooks that show the data exploration, modeling results, and final analysis more clearly. I also include pytest tests using a tiny synthetic corpus, which allows the test suite to run quickly and without needing internet access.

## 5. Risks

One major issue in this project is the shift in distribution. KDDTest+ intentionally includes attack subtypes that do not appear in KDDTrain+, and published baselines often top out around 80% accuracy because of this. I will frame that as a finding rather than a failure, because it shows a realistic problem in intrusion detection: models struggle when they face attack patterns they never saw during training.

Another challenge is class imbalance, especially for the R2L and U2R attack families. These categories make up a very small percentage of the dataset, so the model can perform well overall while still missing many rare attacks. To address this, I use class_weight="balanced" when applicable and report per-class metrics rather than relying solely on overall accuracy. Finally, I acknowledge the age of NSL-KDD as a limitation. Since it is based on older network traffic, I also point to more modern alternatives, such as CICIDS-2017 and UNSW-NB15, as future datasets for testing the same pipeline.



## 6. References

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
