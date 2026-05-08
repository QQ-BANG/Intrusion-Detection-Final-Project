# Intrusion Detection on NSL-KDD

For the final project, the idea is to take the cybersecurity network
traffic data from the MIT Lincoln Lab DARPA 1998/1999 evaluation,
load it into a relational database, do some exploratory data analysis
in Python, and then train a few classifiers to tell normal
traffic from attack traffic.

I used NSL-KDD instead of the raw DARPA tcpdump captures because
NSL-KDD is the standard cleaned version of the same corpus that
Basically, every IDS paper since 2009 compares against (Tavallaee et
al., 2009).

## Pipeline

There are three parts:

1. Database. The cleaned connection records go into a SQLite database
   with a normalized schema (3NF). There are dimension tables for
   `protocols`, `services`, `flags`, and `attack_types`, and a fact
   table `connections` with one row per network connection. There is
   also a view `v_connections_full` that joins them all together so
   the EDA queries are short.
2. Data science. The data gets cleaned, deduplicated, profiled, and
   visualized with pandas, seaborn, and matplotlib.
3. Machine learning. We train four classifiers (Logistic Regression,
   Random Forest, Histogram Gradient Boosting, and a small MLP) and
   evaluate them on the official held-out `KDDTest+` split. The
   problem is framed both as binary (normal vs. attack) and as a
   5-way classification over the DARPA families (DoS, Probe, R2L,
   U2R, normal).

## Dataset

| Property   | Value |
|------------|-------|
| Source     | NSL-KDD (mirrored on GitHub) |
| Origin     | MIT Lincoln Lab DARPA 1998/1999 IDS Evaluation |
| Records    | 125,973 train + 22,544 test |
| Features   | 41 per connection (38 numeric + 3 categorical) |
| Targets    | `label` (39 attack types), collapsed into 5 broad families |
| License    | Public, released by University of New Brunswick |

The download script tries a couple of mirrors automatically. If your
network blocks GitHub raw, just drop `KDDTrain+.txt` and
`KDDTest+.txt` into `data/raw/` by hand and the rest of the pipeline
still runs.

## Repo layout

```
.
├── README.md                  # Project overview (this file)
├── HOWTO.md                   # Step-by-step instructions to run everything
├── requirements.txt
├── app/
│   └── streamlit_app.py       # Interactive web UI
├── run_app.sh                 # `./run_app.sh` to launch the UI
├── docs/
│   ├── proposal.md            # Project proposal (Part 1)
│   └── final_report.md        # Final report (Part 2)
├── sql/
│   ├── schema.sql             # Normalized schema for SQLite
│   └── example_queries.sql    # Analytical queries used in the report
├── src/ids_pipeline/
│   ├── config.py              # Paths, constants, attack-family map
│   ├── download_data.py       # NSL-KDD downloader
│   ├── clean_data.py          # Cleaning and typing
│   ├── schema.py              # SQLAlchemy version of schema.sql
│   ├── build_database.py      # Loads CSV into SQLite
│   ├── features.py            # Preprocessing pipeline
│   ├── visualize.py           # EDA + result plots
│   ├── evaluate.py            # Metrics helpers
│   ├── train_models.py        # Model training + evaluation
│   └── run_pipeline.py        # End-to-end CLI
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_database_queries.ipynb
│   └── 03_modeling.ipynb
├── tests/                     # pytest tests on a synthetic corpus
├── data/                      # raw + processed (gitignored)
└── outputs/                   # figures, models, reports (gitignored)
```

## Quick start

> See **[HOWTO.md](HOWTO.md)** for a step-by-step walkthrough in VS Code
> (venv setup, one-click launch configs, notebooks, web UI, troubleshooting).
> The terminal commands below are the short version.

```bash
# 1. install deps
python3 -m pip install -r requirements.txt

# 2. run the whole pipeline (download -> DB -> EDA -> train -> eval)
PYTHONPATH=src python3 -m ids_pipeline.run_pipeline

# 3. open the interactive web UI (pages: Overview, SQL playground,
#    EDA explorer, Model results, Live prediction)
./run_app.sh
# or:  PYTHONPATH=src streamlit run app/streamlit_app.py

# 4. or run individual pipeline steps
PYTHONPATH=src python3 -m ids_pipeline.download_data
PYTHONPATH=src python3 -m ids_pipeline.build_database
PYTHONPATH=src python3 -m ids_pipeline.train_models --cv-folds 5

# 5. poke at the database directly
sqlite3 data/processed/ids.sqlite < sql/example_queries.sql

# 6. unit tests (uses synthetic data, no internet needed)
PYTHONPATH=src python3 -m pytest tests/ -v
```

Useful flags on `run_pipeline`:

| Flag | What it does |
|------|--------------|
| `--skip-download` | Use whatever is already in `data/raw/`. |
| `--skip-db` | Reuse the existing `data/processed/ids.sqlite`. |
| `--eda-only` | Build the DB and figures, skip training. |
| `--quick` | Subsample to 10% for a fast smoke test. |
| `--cv-folds 5` | Also run 5-fold stratified CV on the train split. |

## Web UI (Streamlit)

`./run_app.sh` opens a local web app at `http://localhost:8501` with five pages:

1. **Overview**. Counts and headline metrics from the database, plus an
   attack-family bar chart.
2. **SQL playground**. Paste any `SELECT` against the schema and see
   the rows back. Comes with five pre-loaded example queries.
3. **EDA explorer**. Sliders / multiselects for protocol, family, and
   split, with charts that update live.
4. **Model results**. Comparison bar chart for any metric, plus the
   confusion matrices, ROC curves, and feature importance.
5. **Live prediction**. Build a connection by hand with sliders and
   dropdowns, hit one of the preset buttons (typical normal, SYN
   flood, port scan), and the trained model classifies it in real
   time with an attack-probability gauge.

You need to have run the pipeline at least once first so the database
and the saved models exist.

The app can also be hosted for free on
[Streamlit Community Cloud](https://streamlit.io/cloud): push the repo
to GitHub, point Streamlit Cloud at `app/streamlit_app.py`, and the UI
becomes a public URL you can drop into the demo video.

## Results (random seed 42)

Binary detection on the official `KDDTest+` split:

| Model                | Accuracy | Precision | Recall |    F1  | ROC-AUC |
|----------------------|---------:|----------:|-------:|-------:|--------:|
| HistGradientBoosting |   0.800  |   0.969   |  0.670 |  0.793 |  0.962  |
| MLP (128, 64)        |   0.788  |   0.937   |  0.673 |  0.783 |  0.924  |
| Random Forest (200)  |   0.770  |   0.969   |  0.616 |  0.753 |  0.961  |
| Logistic Regression  |   0.754  |   0.918   |  0.623 |  0.742 |  0.791  |

These are in the same ballpark as published NSL-KDD baselines
(F1 around 0.75 to 0.80 on `KDDTest+`). The reason nothing breaks
0.80 is well known: `KDDTest+` contains attack subtypes that are not
present in `KDDTrain+`, so even strong models hit a ceiling.

## References

* Tavallaee, M., Bagheri, E., Lu, W., & Ghorbani, A. A. (2009).
  *A detailed analysis of the KDD CUP 99 data set.* IEEE CISDA.
* Lippmann, R., Haines, J. W., Fried, D. J., Korba, J., & Das, K.
  (2000). *The 1999 DARPA off-line intrusion detection evaluation.*
  Computer Networks 34(4), 579-595.
* Pedregosa, F. et al. (2011). *Scikit-learn: Machine Learning in
  Python.* JMLR 12, 2825-2830.

