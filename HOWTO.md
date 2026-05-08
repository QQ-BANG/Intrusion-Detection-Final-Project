# How to run this project (in VS Code)

Step by step. Assumes you're using VS Code, which is the easiest way to
do everything: Python, notebooks, the SQLite database, and the
Streamlit web app all work inside the editor.

If you'd rather use the terminal directly, see the brief note at the
bottom.

---

## 0. What you need

* [VS Code](https://code.visualstudio.com/).
* **Python 3.10 or newer**. If you don't have it, install from
  [python.org](https://www.python.org/downloads/) (on Windows make
  sure to tick "Add Python to PATH" during install).
* About **300 MB of free disk space**.
* **Internet access** the first time you run the pipeline (it pulls
  about 3 MB of dataset files from GitHub). After that, offline is
  fine.

---

## 1. Get the code

You have two options.

### Option A: clone it with VS Code's Git integration

1. Open VS Code.
2. Hit `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac) to open the command
   palette.
3. Type `Git: Clone` and pick that command.
4. Paste the repo URL: `https://github.com/QQ-BANG/Intrusion-Detection-Final-Project.git`
5. Pick a folder on your computer to put it in.
6. When it asks "Open the cloned repository?", click **Open**.

### Option B: download a ZIP

1. On the GitHub page, click the green **Code** button → **Download
   ZIP**.
2. Unzip it somewhere.
3. In VS Code: `File > Open Folder...` and pick the unzipped folder.

Either way, you should now see the project files in the Explorer
sidebar on the left (`README.md`, `HOWTO.md`, `src/`, `app/`, etc.).

---

## 2. Install the recommended extensions

The first time you open the project, VS Code will pop up a notification
in the bottom-right that says:

> **This workspace has extension recommendations.**

Click **Install** and it'll add three extensions:

* **Python** (Microsoft) — runs Python files, manages venvs, runs tests.
* **Jupyter** (Microsoft) — opens `.ipynb` notebooks inline.
* **SQLite Viewer** (qwtel) — lets you browse the database visually.

If you missed the popup, open the Extensions sidebar (`Ctrl+Shift+X`),
search for `@recommended`, and click Install on each.

---

## 3. Create a Python virtual environment

A venv keeps this project's dependencies separate from anything else
on your machine.

1. Hit `` Ctrl+` `` to open VS Code's integrated terminal at the bottom.
2. Run:
   ```bash
   python -m venv venv
   ```
3. VS Code will pop up a notification: **"We noticed a new environment
   has been created. Do you want to select it for the workspace folder?"**
   Click **Yes**.

If it doesn't pop up, do it manually: hit `Ctrl+Shift+P`, type
`Python: Select Interpreter`, and pick the one that says
`./venv/bin/python` (or `.\venv\Scripts\python.exe` on Windows).

From now on, every new terminal you open in VS Code will have the
venv activated automatically — you don't have to do anything else.

---

## 4. Install the dependencies

Open a fresh terminal (`` Ctrl+` ``) — you should see `(venv)` at the
start of the prompt — and run:

```bash
pip install -r requirements.txt
```

This pulls down pandas, scikit-learn, SQLAlchemy, matplotlib, seaborn,
streamlit, plotly, and a few smaller things. First time it takes 1-3
minutes.

When it's done, verify everything imports cleanly:

```bash
python -c "import pandas, sklearn, streamlit; print('ok')"
```

You should see `ok`.

---

## 5. Run the full pipeline

This is where the project actually does its thing: download the
dataset, build the database, generate the EDA charts, train all four
classifiers, and write the metric reports.

There are three ways to run it. **The first is easiest.**

### Easiest: one click

1. Click the **Run and Debug** icon in the left sidebar (it's the
   triangle with a bug, or hit `Ctrl+Shift+D`).
2. At the top there's a green play button with a dropdown next to it.
   Open the dropdown and pick **"Run full pipeline"**.
3. Click the green play button (or hit `F5`).

The pipeline runs in the integrated terminal at the bottom and takes
about **45-60 seconds** on a normal laptop.

### Other ways

* **From the terminal:**
  ```bash
  python -m ids_pipeline.run_pipeline
  ```
  (`PYTHONPATH=src` is already set for you by `.vscode/settings.json`,
  so you don't have to type it.)

* **As a debug-able run** (with breakpoints): set a breakpoint by
  clicking in the gutter of any `.py` file under `src/ids_pipeline/`,
  then hit F5 with the same launch config selected.

### What success looks like

You should see logs like:

```
INFO ids_pipeline: === STEP: Download ===
INFO ids_pipeline: === STEP: Build database ===
INFO ids_pipeline: === STEP: EDA visualizations ===
INFO ids_pipeline: === STEP: Train models ===
...

=== Binary results (test set) ===
        model  accuracy  precision  recall     f1  roc_auc
    hist_gbdt    0.8002     0.9692  0.6702 0.7925   0.9618
          mlp    0.7879     0.9371  0.6726 0.7831   0.9239
random_forest    0.7697     0.9685  0.6155 0.7527   0.9614
       logreg    0.7537     0.9175  0.6234 0.7424   0.7914
```

That last table is the headline result.

### What it produced

In the Explorer sidebar you'll now see new files:

* `data/raw/` — `KDDTrain+.txt`, `KDDTest+.txt`
* `data/processed/ids.sqlite` — the database (~30 MB)
* `outputs/figures/` — 12 PNG charts (you can click any of them to
  preview inline in VS Code)
* `outputs/models/` — 5 trained sklearn pipelines (`.joblib`)
* `outputs/reports/` — `binary_results.csv` and the multi-class report

---

## 6. Launch the interactive web UI

After the pipeline has run at least once, you can launch the
Streamlit web app.

1. **Run and Debug** sidebar (`Ctrl+Shift+D`).
2. Pick **"Streamlit web UI"** from the dropdown.
3. Hit F5.
4. (Alternative, if the extensions don't work, just run this command in the terminal)
 streamlit run app/streamlit_app.py)

The app has 5 pages in its sidebar:

1. **Overview** — counts, attack rate, headline metrics.
2. **SQL playground** — type any `SELECT` against the database.
3. **EDA explorer** — filter and chart the connection records live.
4. **Model results** — compare classifiers, browse confusion matrices
   and ROC curves.
5. **Live prediction** — build a fake connection with sliders, hit
   one of the preset buttons (typical normal / SYN flood / port scan),
   and watch the model classify it in real time.

To stop the server, click in the integrated terminal where it's
running and hit `Ctrl+C`, or click the red square in the debug
toolbar at the top.

---

## 7. Open the notebooks

In the Explorer sidebar, click any of:

* `notebooks/01_eda.ipynb`
* `notebooks/02_database_queries.ipynb`
* `notebooks/03_modeling.ipynb`

VS Code opens them as interactive notebooks. The first time, it'll
ask which kernel to use — pick the venv interpreter you set up in
step 3.

To run the cells:

* `Shift+Enter` runs the current cell and moves to the next.
* `Ctrl+Enter` runs the current cell and stays put.
* The "Run All" button at the top runs the whole notebook.

The **Variables** panel (top-right of the notebook view) lets you
inspect any DataFrame in a spreadsheet-style viewer, which is way
nicer than just printing it. Right-click any DataFrame and pick "View
Value in Data Viewer" for sortable, filterable inspection.

When you're happy with a notebook, save it with `Ctrl+S` — the
rendered outputs get baked in, and they'll show up automatically when
anyone views the file on GitHub.

---

## 8. Browse the SQLite database

After the pipeline has run, double-click `data/processed/ids.sqlite`
in the Explorer sidebar. The SQLite Viewer extension opens a tab
where you can:

* Browse the rows of `protocols`, `services`, `flags`,
  `attack_types`, and `connections`.
* Run ad-hoc SQL queries (there's a query box at the top).
* Look at the joined `v_connections_full` view — that's the one most
  of the analysis uses.

For more involved queries, open `sql/example_queries.sql` — it has
five preloaded analytical queries you can copy into the viewer.

---

## 9. Run the unit tests

1. Click the **Testing** icon in the left sidebar (it looks like a
   beaker / flask).
2. The first time, VS Code asks you to configure tests. Pick:
   * **pytest**
   * directory: **`tests`**
3. You'll see a tree of all 9 tests. Click any test and hit the green
   play button to run just that one, or click the play button at the
   top of the panel to run them all.

Right-click any test and pick **Debug Test** to step through it with
breakpoints. The tests use a tiny synthetic dataset so they don't
need internet or even the real NSL-KDD files.

---

## 10. Other launch configs

Open the **Run and Debug** dropdown again — there are six configs
total, all in `.vscode/launch.json`:

| Config | What it does |
|---|---|
| Run full pipeline | Download + DB + EDA + training. The default. |
| Quick smoke test (10% of train) | Same flow but on 10% of the data. ~10 seconds. |
| EDA only (no training) | Build DB and figures, skip the slow training step. |
| Train models only | Re-train without redownloading or rebuilding the DB. |
| Streamlit web UI | Launches the web app. |
| Run unit tests | Runs `pytest tests/ -v`. |

---
