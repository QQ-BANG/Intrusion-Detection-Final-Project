# CS 210 Final Report: Intrusion Detection on NSL-KDD

**Course:** CS 210, Data Management for Data Science
**Authors:** *Q'Andre Small*
**Date:** *5/7/26*

## Abstract

I built a machine-learning pipeline for the network
intrusion detection that combines a normalized relational database
(SQLite, 3NF), a Python data-science layer, and four supervised
classifiers. Using NSL-KDD, the standard cleaned version of the MIT
Lincoln Lab DARPA 1998/1999 evaluation, the best model
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
biggest predictor of total damage. Signature based NIDS Snort,
Suricata only catches known attacks, which is why two decades of
research have gone into learning-based detection.  With more and more people 
becoming a part of the digital space, it seems that the number of accounts
and information a database can hold is endless, which is why now more than ever
it is important to protect this data

### 1.2 How this fits the course

The project hits the three layers shown to me in our CS 210 class:

Data management, which in this case looks like a normalized 3NF schema, dimension tables, surrogate keys, indexes, joins, views, and parameterized queries. Data science, which encapsulates Cleaning, profiling, visualizing, and reporting on a non-trivial real dataset. Machine learning in the form of Supervised classification with proper preprocessing pipelines, train/test discipline, and decent metrics.

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

I picked SQLite because it is zero-configuration, and the whole Database
is one file, but the SQLAlchemy ORM definition in
`src/ids_pipeline/schema.py` would also work against PostgreSQL.

### 2.3 Cleaning

For preprocessing, I first strip the trailing dot from the KDD'99 style labels so that the attack names are clean and consistent.
I also converted all the categorical strings to lowercase, so values such as `Http` become `http`.  After that, I coerce the numeric columns into proper numeric types, replace positive and negative infinity values with NaN, and then fill those missing values with 0.  I would also drop any duplicate rows and then document the `num_outbound_cmd` feature, which is constantly 0 throughout the corpus, and I would keep it in the dataset so that the schema continues to match the NSL-KDD Specifications
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


The model is trained on KDDTrain+ and evaluated on KDDTest+, with the test set used only once at the final evaluation stage. For the binary classification version, I report accuracy, precision, recall, F1-score, and ROC-AUC to measure overall performance and the model's ability to separate normal and attack traffic. For the multi-class version, I included a full per-class classification report and a confusion matrix so that performance can be compared across each attack category. I also include an optional 5-fold stratified cross-validation step on the training split using --cv-folds 5, which helps estimate how much the model’s performance varies across different training folds.

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


Here are some of my observations. All four models show the same general failure pattern. Their precision is very high, around 0.97, but their recall is only around 0.65. This means the models are more likely to miss attacks than to create false alarms, which is still the better failure mode for a SOC because it avoids overwhelming analysts with too many incorrect alerts. The tree-based ensemble models perform much better than the linear baseline in terms of AUC, with scores around 0.96 compared to 0.79. This suggests that the dataset contains many nonlinear patterns that linear models cannot capture well. The MLP slightly outperforms the Random Forest in F1-score, but it falls behind on AUC. This is not too surprising because neural networks are often not as well-calibrated as probabilistic models by default, even when their classification performance is strong.

### 3.5 Multi-class results (Random Forest, 5 classes)

See `outputs/reports/multiclass_rf_report.json` and
`outputs/figures/cm_multiclass_rf.png`.

The multi-class results show that normal and dos traffic are recovered almost perfectly, with F1-scores above 0.95. The probe class is also recovered fairly well, with an F1-score above 0.70, likely because features such as `count` and `srv_count` help capture scanning-style behavior. However, the R2L and U2R classes are heavily under-recalled. Many attacks from these families are incorrectly classified as normal because KDDTest+ contains attack subtypes such as `snmpguess,` `httptunnel` , and `mscan` that do not appear in KDDTrain+. This creates a known performance ceiling in NSL-KDD, where models struggle to recognize attack types they were never exposed to during training.

### 3.6 Feature importance

`outputs/figures/feature_importance_rf.png` ranks the top features.
Lining up with prior work, the top discriminators are `src_bytes`,
`dst_bytes`, `service=http` / `private`, `flag=SF` / `S0`, `count`,
and `serror_rate`. So the schema's categorical dimensions are
pulling real predictive light.

## 4. Discussion and limitations

### 4.1 What I did

The pipeline runs end-to-end from a single command and stays deterministic because it uses a fixed random seed. The database layer is also fully implemented rather than being treated like a CSV file with a .sqlite extension. It follows 3NF design, includes indexes, uses a view, and has foreign key enforcement turned on. For modeling, four different model families are compared using the same train/test splits, along with the full metric suite, confusion matrices, and ROC analysis. The project also follows proper test discipline because KDDTest+ is only touched once during the final evaluation. Finally, the Streamlit UI in `app/streamlit_app.py` makes the project much easier to demo because the trained models can run live against user-constructed network connections. This helps make the purpose of an IDS feel much more concrete than it would in a static report.


### 4.2 What I did not do

One limitation of this project is the age of the dataset. NSL-KDD was generated from 1998 to 1999 network traffic, and the attack landscape has changed significantly since then with the rise of encrypted traffic, IoT devices, ransomware, and other modern threats. Because of this, the performance numbers from this project should not be assumed to directly transfer to modern networks. Another limitation is distribution shift: KDDTest+ contains attack subtypes that are not present in the training set, which creates a hard ceiling on model accuracy around 80%. I treat this as an important finding, but it is also a limitation of the dataset itself. The dataset also only provides aggregated per-connection features rather than raw packets, so this project cannot evaluate payload-based detection methods. Finally, the evaluation uses a single fixed train/test split. I include optional 5-fold cross-validation on the training split to estimate variance, but the final test set remains fixed.

### 4.3 Future work

For future work, I would first re-run the pipeline on a more modern intrusion detection dataset such as CICIDS-2017 or UNSW-NB15. This would make the results more realistic because those datasets include newer traffic patterns and attack behaviors than NSL-KDD. I would also add a streaming evaluation setup in which new network connections arrive over time, and the model is continuously updated or re-evaluated. This would help measure concept drift, which is important because real network behavior changes as users, devices, and attackers change.

Another improvement would be moving the database layer from SQLite to PostgreSQL. PostgreSQL would make the project more realistic for a production style SOC environment because it supports stronger concurrency, better access control, and features like row-level security. That would allow different analysts or tenants to access only the records they are allowed to see. Finally, I suggest using cost-sensitive learning tuned around a specific false-alarm budget. Instead of only maximizing general metrics like accuracy or F1-score, the model could be trained to balance missed attacks against alert volume in a way that better matches how a real SOC operates.

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


