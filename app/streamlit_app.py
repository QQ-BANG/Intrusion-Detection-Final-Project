
# run with:  PYTHONPATH=src streamlit run app/streamlit_app.py
# (or just ./run_app.sh)
# Pages:
#   1. Overview           - counts + headline metrics from the DB
#   2. SQL playground     - run your own SQL against the schema
#   3. EDA explorer       - filter + chart the connection records
#   4. Model results      - compare the four trained classifiers
#   5. Live prediction    - enter a connection by hand, get a prediction

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text

# add src/ to path so the ids_pipeline imports work when streamlit launches
# this file directly. Hacky but simpler than installing the package.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ids_pipeline import config
from ids_pipeline.schema import get_engine


st.set_page_config(
    page_title="DARPA IDS Explorer",
    page_icon="shield",
    layout="wide",
    initial_sidebar_state="expanded",
)



@st.cache_resource
def get_db_engine():
    return get_engine(config.DB_URL)


@st.cache_data(show_spinner=False)
def load_full_view(_engine_id=0):
    eng = get_db_engine()
    with eng.connect() as conn:
        return pd.read_sql(text("SELECT * FROM v_connections_full"), conn)


@st.cache_data(show_spinner=False)
def load_metrics():
    p = config.REPORTS_DIR / "binary_results.csv"
    if not p.exists():
        return None
    return pd.read_csv(p)


@st.cache_data(show_spinner=False)
def load_multiclass_report():
    p = config.REPORTS_DIR / "multiclass_rf_report.json"
    if not p.exists():
        return None
    with open(p) as fh:
        return json.load(fh)


@st.cache_resource
def load_model(name):
    p = config.MODELS_DIR / (name + ".joblib")
    if not p.exists():
        return None
    return joblib.load(p)


def db_ready():
    return config.DB_PATH.exists()


def models_ready():
    # any joblib file in outputs/models means we've trained at least once
    return any(config.MODELS_DIR.glob("*.joblib"))


# Sidebar
with st.sidebar:
    st.title("DARPA IDS Explorer")
    st.caption("CS 210 final project")
    page = st.radio(
        "Page",
        [
            "Overview",
            "SQL playground",
            "EDA explorer",
            "Model results",
            "Live prediction",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Status")
    st.write("Database:", "ready" if db_ready() else "missing")
    st.write("Models:  ", "ready" if models_ready() else "missing")
    if not db_ready() or not models_ready():
        st.info(
            "Some pages need the pipeline to have run at least once.\n"
            "From the project root:\n\n"
            "```\nPYTHONPATH=src python3 -m ids_pipeline.run_pipeline\n```"
        )

# Page 1: Overview
if page == "Overview":
    st.header("Overview")
    st.write(
        "We loaded the NSL-KDD corpus (the cleaned version of the DARPA "
        "1998/1999 evaluation traffic) into a normalized SQLite database "
        "and trained four classifiers to detect attacks."
    )

    if not db_ready():
        st.error("`data/processed/ids.sqlite` is missing. Run the pipeline first.")
        st.stop()

    df = load_full_view()
    n_total = len(df)
    n_attack = int((df["is_attack"] == 1).sum())
    n_train = int((df["split"] == "train").sum())
    n_test = int((df["split"] == "test").sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Connections", f"{n_total:,}")
    c2.metric("Attack rate", f"{n_attack / n_total:.1%}")
    c3.metric("Train rows", f"{n_train:,}")
    c4.metric("Test rows", f"{n_test:,}")

    st.subheader("Counts per attack family")
    counts = (
        df.groupby(["split", "attack_family"]).size().reset_index(name="n")
    )
    fam_order = ["normal", "dos", "probe", "r2l", "u2r"]
    fig = px.bar(
        counts,
        x="attack_family",
        y="n",
        color="split",
        category_orders={"attack_family": fam_order},
        barmode="group",
        log_y=True,
        labels={"n": "Connections (log scale)", "attack_family": "Family"},
    )
    fig.update_layout(height=400, margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

    metrics = load_metrics()
    if metrics is not None:
        st.subheader("Headline test-set metrics")
        st.dataframe(
            metrics.style.format({
                "accuracy": "{:.4f}", "precision": "{:.4f}",
                "recall": "{:.4f}", "f1": "{:.4f}", "roc_auc": "{:.4f}",
            }).highlight_max(
                subset=["accuracy", "f1", "roc_auc"], color="#1d4d2c"
            ),
            use_container_width=True,
        )


# Page 2: SQL playground
elif page == "SQL playground":
    st.header("SQL playground")
    st.caption(
        "Run any SELECT query against the SQLite database. "
        "The schema is shown on the right."
    )

    if not db_ready():
        st.error("`data/processed/ids.sqlite` is missing. Run the pipeline first.")
        st.stop()

    presets = {
        "Pick a preset...": "",
        "Counts per family": (
            "SELECT split, attack_family, COUNT(*) AS n\n"
            "FROM v_connections_full\n"
            "GROUP BY split, attack_family\n"
            "ORDER BY split, n DESC;"
        ),
        "Top 10 attacked services": (
            "SELECT service, COUNT(*) AS n_attacks\n"
            "FROM v_connections_full\n"
            "WHERE split = 'train' AND is_attack = 1\n"
            "GROUP BY service\n"
            "ORDER BY n_attacks DESC\n"
            "LIMIT 10;"
        ),
        "Avg bytes by protocol and family": (
            "SELECT protocol_type, attack_family, COUNT(*) AS n,\n"
            "       ROUND(AVG(src_bytes), 2) AS avg_src_bytes,\n"
            "       ROUND(AVG(dst_bytes), 2) AS avg_dst_bytes\n"
            "FROM v_connections_full\n"
            "WHERE split = 'train'\n"
            "GROUP BY protocol_type, attack_family\n"
            "ORDER BY protocol_type, attack_family;"
        ),
        "Failed-login profile (R2L signal)": (
            "SELECT attack_family,\n"
            "       ROUND(AVG(num_failed_logins), 3) AS avg_failed_logins,\n"
            "       ROUND(AVG(logged_in), 3) AS pct_logged_in,\n"
            "       ROUND(AVG(is_guest_login), 3) AS pct_guest\n"
            "FROM v_connections_full\n"
            "WHERE split = 'train'\n"
            "GROUP BY attack_family;"
        ),
        "Connection-rate profile (Probe / DoS signal)": (
            "SELECT attack_family,\n"
            "       ROUND(AVG(count), 2) AS avg_count,\n"
            "       ROUND(AVG(srv_count), 2) AS avg_srv_count,\n"
            "       ROUND(AVG(serror_rate), 3) AS avg_serror_rate,\n"
            "       ROUND(AVG(rerror_rate), 3) AS avg_rerror_rate\n"
            "FROM v_connections_full\n"
            "WHERE split = 'train'\n"
            "GROUP BY attack_family;"
        ),
    }

    left, right = st.columns([3, 2])
    with left:
        preset = st.selectbox("Preset", list(presets.keys()))
        default_sql = presets[preset] if preset != "Pick a preset..." else (
            "SELECT split, attack_family, COUNT(*) AS n\n"
            "FROM v_connections_full\n"
            "GROUP BY split, attack_family\n"
            "ORDER BY split, n DESC;"
        )
        sql = st.text_area("SQL", value=default_sql, height=220)
        run = st.button("Run query", type="primary")

    with right:
        st.caption("Schema")
        st.code(
            "protocols(protocol_id, protocol_name)\n"
            "services(service_id, service_name)\n"
            "flags(flag_id, flag_name)\n"
            "attack_types(attack_id, attack_label,\n"
            "             attack_family, is_attack)\n"
            "connections(conn_id, split, duration,\n"
            "  protocol_id, service_id, flag_id,\n"
            "  src_bytes, dst_bytes, ...,\n"
            "  attack_id, difficulty)\n\n"
            "v_connections_full   <-- joined view",
            language="sql",
        )

    if run:
        stripped = sql.strip().rstrip(";").lower()
        if not stripped.startswith(("select", "with")):
            st.error("Only SELECT / WITH queries are allowed in the playground.")
        else:
            try:
                eng = get_db_engine()
                with eng.connect() as conn:
                    df = pd.read_sql(text(sql), conn)
                st.success(f"Returned {len(df)} rows.")
                st.dataframe(df, use_container_width=True)
                if len(df.columns) >= 2 and len(df) <= 50:
                    num_cols = df.select_dtypes("number").columns.tolist()
                    if num_cols:
                        x_col = df.columns[0]
                        y_col = num_cols[-1]
                        fig = px.bar(df, x=x_col, y=y_col)
                        fig.update_layout(height=350)
                        st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:
                st.error(f"Query failed: {exc}")

# Page 3: EDA explorer
elif page == "EDA explorer":
    st.header("EDA explorer")

    if not db_ready():
        st.error("`data/processed/ids.sqlite` is missing. Run the pipeline first.")
        st.stop()

    df = load_full_view()

    c1, c2, c3 = st.columns(3)
    with c1:
        split = st.multiselect(
            "Split", sorted(df["split"].unique()),
            default=["train"],
        )
    with c2:
        protos = st.multiselect(
            "Protocol", sorted(df["protocol_type"].unique()),
            default=sorted(df["protocol_type"].unique()),
        )
    with c3:
        fams = st.multiselect(
            "Attack family",
            ["normal", "dos", "probe", "r2l", "u2r"],
            default=["normal", "dos", "probe", "r2l", "u2r"],
        )

    f = df[
        df["split"].isin(split)
        & df["protocol_type"].isin(protos)
        & df["attack_family"].isin(fams)
    ]

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows after filter", f"{len(f):,}")
    if len(f):
        c2.metric("Attack rate", f"{(f['is_attack']==1).mean():.1%}")
    c3.metric("Distinct services", f"{f['service'].nunique()}")

    st.subheader("Family by protocol")
    if len(f):
        agg = f.groupby(["protocol_type", "attack_family"]).size().reset_index(name="n")
        fig = px.bar(
            agg, x="protocol_type", y="n", color="attack_family",
            category_orders={"attack_family": ["normal","dos","probe","r2l","u2r"]},
            barmode="stack",
        )
        fig.update_layout(height=380, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("log(1 + bytes) by family")
    if len(f):
        ff = f.copy()
        ff["log_src_bytes"] = np.log1p(ff["src_bytes"])
        ff["log_dst_bytes"] = np.log1p(ff["dst_bytes"])
        a, b = st.columns(2)
        with a:
            fig = px.violin(
                ff, x="attack_family", y="log_src_bytes", box=True,
                category_orders={"attack_family": ["normal","dos","probe","r2l","u2r"]},
            )
            fig.update_layout(height=380, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)
        with b:
            fig = px.violin(
                ff, x="attack_family", y="log_dst_bytes", box=True,
                category_orders={"attack_family": ["normal","dos","probe","r2l","u2r"]},
            )
            fig.update_layout(height=380, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top services in the filtered set")
    if len(f):
        topn = (
            f.groupby(["service", "attack_family"]).size()
             .reset_index(name="n")
        )
        topservices = (
            topn.groupby("service")["n"].sum()
                .sort_values(ascending=False).head(15).index.tolist()
        )
        topn = topn[topn["service"].isin(topservices)]
        fig = px.bar(
            topn, x="n", y="service", color="attack_family", orientation="h",
            category_orders={
                "service": topservices,
                "attack_family": ["normal","dos","probe","r2l","u2r"],
            },
        )
        fig.update_layout(height=520, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show raw rows"):
        st.dataframe(f.head(500), use_container_width=True)

# Page 4: Model results
elif page == "Model results":
    st.header("Model results")

    metrics = load_metrics()
    if metrics is None:
        st.error("`outputs/reports/binary_results.csv` is missing. Train the models first.")
        st.stop()

    st.subheader("Binary task: normal vs. attack (test set)")
    st.dataframe(
        metrics.style.format({
            "accuracy": "{:.4f}", "precision": "{:.4f}",
            "recall": "{:.4f}", "f1": "{:.4f}", "roc_auc": "{:.4f}",
        }),
        use_container_width=True,
    )

    metric_to_plot = st.selectbox(
        "Plot metric", ["f1", "accuracy", "precision", "recall", "roc_auc"], index=0,
    )
    fig = px.bar(
        metrics.sort_values(metric_to_plot),
        x="model", y=metric_to_plot, range_y=[0, 1],
        text=metrics.sort_values(metric_to_plot)[metric_to_plot].round(3),
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=400, margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Confusion matrices and ROC")
    cms = sorted(config.FIGURES_DIR.glob("cm_binary_*.png"))
    if cms:
        cols = st.columns(2)
        for i, p in enumerate(cms):
            cols[i % 2].image(str(p), caption=p.stem)
    roc = config.FIGURES_DIR / "roc_binary.png"
    if roc.exists():
        st.image(str(roc), caption="ROC curves on the test set")
    fi = config.FIGURES_DIR / "feature_importance_rf.png"
    if fi.exists():
        st.subheader("Random Forest feature importance")
        st.image(str(fi))

    rep = load_multiclass_report()
    if rep is not None:
        st.subheader("5-class report (Random Forest)")
        rows = []
        for k, v in rep.items():
            if isinstance(v, dict) and {"precision", "recall", "f1-score"} <= set(v):
                rows.append({"class": k, **v})
        if rows:
            mc_df = pd.DataFrame(rows)
            st.dataframe(
                mc_df.style.format({
                    "precision": "{:.3f}", "recall": "{:.3f}",
                    "f1-score": "{:.3f}", "support": "{:.0f}",
                }),
                use_container_width=True,
            )
        cm5 = config.FIGURES_DIR / "cm_multiclass_rf.png"
        if cm5.exists():
            st.image(str(cm5), caption="5-class confusion matrix")

# Page 5: Live prediction
elif page == "Live prediction":
    st.header("Live prediction")
    st.caption(
        "Enter a connection by hand and the trained model will say whether "
        "it looks like normal traffic or an attack. Less-common features are "
        "filled in with reasonable defaults."
    )

    if not db_ready():
        st.error("`data/processed/ids.sqlite` is missing. Run the pipeline first.")
        st.stop()
    if not models_ready():
        st.error("No trained models. Run the pipeline first.")
        st.stop()

    df = load_full_view()
    proto_opts = sorted(df["protocol_type"].unique())
    service_opts = sorted(df["service"].unique())
    flag_opts = sorted(df["flag"].unique())

    st.subheader("Pick a model")
    model_choice = st.selectbox(
        "Model",
        ["hist_gbdt_binary", "random_forest_binary",
         "logreg_binary", "mlp_binary"],
        index=0,
    )
    pipe = load_model(model_choice)
    if pipe is None:
        st.error(f"Model artifact `{model_choice}.joblib` not found.")
        st.stop()

    st.subheader("Quick presets")
    c1, c2, c3 = st.columns(3)
    preset = None
    if c1.button("Sample: typical normal"):
        preset = "normal"
    if c2.button("Sample: SYN flood (DoS)"):
        preset = "dos"
    if c3.button("Sample: portscan (Probe)"):
        preset = "probe"

    defaults = {
        "duration": 0, "protocol_type": "tcp", "service": "http", "flag": "SF",
        "src_bytes": 200, "dst_bytes": 5000,
        "land": 0, "wrong_fragment": 0, "urgent": 0, "hot": 0,
        "num_failed_logins": 0, "logged_in": 1, "num_compromised": 0,
        "root_shell": 0, "su_attempted": 0, "num_root": 0,
        "num_file_creations": 0, "num_shells": 0, "num_access_files": 0,
        "num_outbound_cmds": 0, "is_host_login": 0, "is_guest_login": 0,
        "count": 5, "srv_count": 5,
        "serror_rate": 0.0, "srv_serror_rate": 0.0,
        "rerror_rate": 0.0, "srv_rerror_rate": 0.0,
        "same_srv_rate": 1.0, "diff_srv_rate": 0.0,
        "srv_diff_host_rate": 0.0,
        "dst_host_count": 50, "dst_host_srv_count": 50,
        "dst_host_same_srv_rate": 1.0, "dst_host_diff_srv_rate": 0.0,
        "dst_host_same_src_port_rate": 0.1,
        "dst_host_srv_diff_host_rate": 0.0,
        "dst_host_serror_rate": 0.0, "dst_host_srv_serror_rate": 0.0,
        "dst_host_rerror_rate": 0.0, "dst_host_srv_rerror_rate": 0.0,
    }
    if preset == "dos":
        defaults.update({
            "service": "private", "flag": "S0",
            "src_bytes": 0, "dst_bytes": 0, "logged_in": 0,
            "count": 511, "srv_count": 511,
            "serror_rate": 1.0, "srv_serror_rate": 1.0,
            "same_srv_rate": 1.0, "diff_srv_rate": 0.0,
            "dst_host_count": 255, "dst_host_srv_count": 255,
            "dst_host_serror_rate": 1.0, "dst_host_srv_serror_rate": 1.0,
            "dst_host_same_src_port_rate": 1.0,
        })
    elif preset == "probe":
        defaults.update({
            "service": "private", "flag": "REJ",
            "src_bytes": 0, "dst_bytes": 0, "logged_in": 0,
            "count": 30, "srv_count": 1,
            "rerror_rate": 1.0, "srv_rerror_rate": 1.0,
            "same_srv_rate": 0.05, "diff_srv_rate": 0.95,
            "dst_host_count": 255, "dst_host_srv_count": 1,
            "dst_host_diff_srv_rate": 1.0,
            "dst_host_rerror_rate": 1.0, "dst_host_srv_rerror_rate": 1.0,
        })

    st.subheader("Connection features")
    a, b, c = st.columns(3)
    with a:
        st.markdown("**Identifiers**")
        protocol_type = st.selectbox("protocol_type", proto_opts,
            index=proto_opts.index(defaults["protocol_type"]) if defaults["protocol_type"] in proto_opts else 0)
        service = st.selectbox("service", service_opts,
            index=service_opts.index(defaults["service"]) if defaults["service"] in service_opts else 0)
        flag = st.selectbox("flag", flag_opts,
            index=flag_opts.index(defaults["flag"]) if defaults["flag"] in flag_opts else 0)
        duration = st.number_input("duration (sec)", min_value=0, value=int(defaults["duration"]))
    with b:
        st.markdown("**Bytes and counts**")
        src_bytes = st.number_input("src_bytes", min_value=0, value=int(defaults["src_bytes"]))
        dst_bytes = st.number_input("dst_bytes", min_value=0, value=int(defaults["dst_bytes"]))
        count = st.slider("count", 0, 511, int(defaults["count"]))
        srv_count = st.slider("srv_count", 0, 511, int(defaults["srv_count"]))
        dst_host_count = st.slider("dst_host_count", 0, 255, int(defaults["dst_host_count"]))
        dst_host_srv_count = st.slider("dst_host_srv_count", 0, 255, int(defaults["dst_host_srv_count"]))
    with c:
        st.markdown("**Rates**")
        serror_rate = st.slider("serror_rate", 0.0, 1.0, float(defaults["serror_rate"]))
        rerror_rate = st.slider("rerror_rate", 0.0, 1.0, float(defaults["rerror_rate"]))
        same_srv_rate = st.slider("same_srv_rate", 0.0, 1.0, float(defaults["same_srv_rate"]))
        diff_srv_rate = st.slider("diff_srv_rate", 0.0, 1.0, float(defaults["diff_srv_rate"]))
        dst_host_serror_rate = st.slider("dst_host_serror_rate", 0.0, 1.0, float(defaults["dst_host_serror_rate"]))
        dst_host_rerror_rate = st.slider("dst_host_rerror_rate", 0.0, 1.0, float(defaults["dst_host_rerror_rate"]))

    with st.expander("Advanced features (defaults usually fine)"):
        logged_in = st.checkbox("logged_in", value=bool(defaults["logged_in"]))
        is_guest_login = st.checkbox("is_guest_login", value=bool(defaults["is_guest_login"]))
        num_failed_logins = st.number_input("num_failed_logins", 0, 50, int(defaults["num_failed_logins"]))
        hot = st.number_input("hot", 0, 100, int(defaults["hot"]))
        num_compromised = st.number_input("num_compromised", 0, 100, int(defaults["num_compromised"]))
        root_shell = st.number_input("root_shell", 0, 1, int(defaults["root_shell"]))

    row = dict(defaults)
    row.update({
        "duration": duration, "protocol_type": protocol_type,
        "service": service, "flag": flag,
        "src_bytes": src_bytes, "dst_bytes": dst_bytes,
        "count": count, "srv_count": srv_count,
        "dst_host_count": dst_host_count, "dst_host_srv_count": dst_host_srv_count,
        "serror_rate": serror_rate, "rerror_rate": rerror_rate,
        "same_srv_rate": same_srv_rate, "diff_srv_rate": diff_srv_rate,
        "dst_host_serror_rate": dst_host_serror_rate,
        "dst_host_rerror_rate": dst_host_rerror_rate,
        "logged_in": int(logged_in), "is_guest_login": int(is_guest_login),
        "num_failed_logins": num_failed_logins, "hot": hot,
        "num_compromised": num_compromised, "root_shell": root_shell,
    })
    X = pd.DataFrame([row])

    st.subheader("Prediction")
    pred = int(pipe.predict(X)[0])
    proba = None
    if hasattr(pipe.named_steps["model"], "predict_proba"):
        proba = float(pipe.predict_proba(X)[0, 1])

    label = "ATTACK" if pred == 1 else "normal"
    color = "#e74c3c" if pred == 1 else "#2ecc71"
    st.markdown(
        f"<div style='padding:24px;border-radius:8px;background:{color};"
        "color:white;font-size:1.6rem;font-weight:600;text-align:center'>"
        f"Predicted: {label}</div>",
        unsafe_allow_html=True,
    )

    if proba is not None:
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=proba * 100,
            number={"suffix": "%"},
            title={"text": "Attack probability"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 50], "color": "#1a3d2a"},
                    {"range": [50, 100], "color": "#3d1f1f"},
                ],
            },
        ))
        gauge.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(gauge, use_container_width=True)

    with st.expander("Show feature row sent to the model"):
        st.dataframe(X.T.rename(columns={0: "value"}), use_container_width=True)
