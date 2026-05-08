# Reads KDDTrain+ / KDDTest+ csvs and loads them into a SQLite database with a normalized schema
# Run:  python -m ids_pipeline.build_database
# Steps inside build_database():
#   1) Read CSV files and clean them
#   3) make tables (protocols/services/flags/attack_types)
#   4) replace the categorical strings on the connection rows with FK ids
#   5) insert into the connections fact table

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from . import config
from .clean_data import clean_dataframe, load_raw
from .schema import Base, get_engine

log = logging.getLogger(__name__)


def load_split(raw_dir, name, split):
    df = load_raw(raw_dir / name)
    df = clean_dataframe(df)
    df["split"] = split
    df["attack_family"] = df["label"].map(config.ATTACK_FAMILY).fillna("unknown")
    df["is_attack"] = (df["attack_family"] != "normal").astype(int)
    return df


def build_dim(df, col):
    # small dim table
    values = sorted(df[col].dropna().unique().tolist())
    return pd.DataFrame({col + "_id": range(1, len(values) + 1), col: values})


def build_database(raw_dir=None, db_url=None, db_path=None):
    if raw_dir is None:
        raw_dir = config.RAW_DIR
    if db_path is None:
        db_path = config.DB_PATH
    if db_url is None:
        db_url = "sqlite:///" + str(db_path)

    if db_path.exists():
        log.info("Removing existing database at %s", db_path)
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    train = load_split(raw_dir, "KDDTrain+.txt", "train")
    test = load_split(raw_dir, "KDDTest+.txt", "test")
    full = pd.concat([train, test], ignore_index=True)
    log.info("Loaded %d train + %d test rows", len(train), len(test))

    engine = get_engine(db_url)
    Base.metadata.create_all(engine)

    # build dim tables
    # schema (protocol_name, etc.), the df columns are the original ones
    protocols = build_dim(full, "protocol_type").rename(
        columns={"protocol_type_id": "protocol_id",
                 "protocol_type": "protocol_name"})
    
    services = build_dim(full, "service").rename(
        columns={"service": "service_name"})
    
    flags = build_dim(full, "flag").rename(
        columns={"flag": "flag_name"})

    attack_labels = sorted(full["label"].unique().tolist())
    attack_types = pd.DataFrame({
        "attack_id": range(1, len(attack_labels) + 1),
        "attack_label": attack_labels,
        "attack_family": [config.ATTACK_FAMILY.get(lbl, "unknown")
                          for lbl in attack_labels],
        "is_attack": [0 if lbl == "normal" else 1 for lbl in attack_labels],
    })

    # write the dim tables first so the FKs from connections will resolve
    with engine.begin() as conn:
        protocols.to_sql("protocols", conn, if_exists="append", index=False)
        services.to_sql("services", conn, if_exists="append", index=False)
        flags.to_sql("flags", conn, if_exists="append", index=False)
        attack_types.to_sql("attack_types", conn, if_exists="append", index=False)

    # build lookup dicts to swap strings -> FK ids
    proto_map = dict(zip(protocols["protocol_name"], protocols["protocol_id"]))
    svc_map = dict(zip(services["service_name"], services["service_id"]))
    flag_map = dict(zip(flags["flag_name"], flags["flag_id"]))
    attack_map = dict(zip(attack_types["attack_label"], attack_types["attack_id"]))

    fact = full.copy()
    fact["protocol_id"] = fact["protocol_type"].map(proto_map)
    fact["service_id"] = fact["service"].map(svc_map)
    fact["flag_id"] = fact["flag"].map(flag_map)
    fact["attack_id"] = fact["label"].map(attack_map)

    # now drop the raw string columns since we replaced them with FK ids
    fact = fact.drop(columns=["protocol_type", "service", "flag", "label",
                              "attack_family", "is_attack"])

    # column order has to match the connections table schema
    column_order = [
        "split", "duration", "protocol_id", "service_id", "flag_id",
        "src_bytes", "dst_bytes", "land", "wrong_fragment", "urgent",
        "hot", "num_failed_logins", "logged_in", "num_compromised",
        "root_shell", "su_attempted", "num_root", "num_file_creations",
        "num_shells", "num_access_files", "num_outbound_cmds",
        "is_host_login", "is_guest_login", "count", "srv_count",
        "serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate",
        "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate",
        "dst_host_count", "dst_host_srv_count", "dst_host_same_srv_rate",
        "dst_host_diff_srv_rate", "dst_host_same_src_port_rate",
        "dst_host_srv_diff_host_rate", "dst_host_serror_rate",
        "dst_host_srv_serror_rate", "dst_host_rerror_rate",
        "dst_host_srv_rerror_rate", "attack_id", "difficulty",]
    
    fact = fact[column_order]


    with engine.begin() as conn:
        fact.to_sql("connections", conn, if_exists="append",
                    index=False, chunksize=10000)

    # also create the convenience view from schema.sql. This is annoying to
    # do in the ORM so we just grab the CREATE VIEW from the .sql file and
    # execute it directly.
    schema_file = config.SQL_DIR / "schema.sql"
    if schema_file.exists():
        ddl = schema_file.read_text()
        marker = "CREATE VIEW IF NOT EXISTS v_connections_full"
        view_stmt = ddl.split(marker)[1]
        view_stmt = marker + view_stmt
        view_stmt = view_stmt.split(";")[0] + ";"
        with engine.begin() as conn:
            conn.execute(text(view_stmt))

    with engine.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM connections")).scalar_one()
    log.info("Database built at %s with %d connection rows", db_path, n)
    return db_path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw-dir", type=Path, default=config.RAW_DIR)
    p.add_argument("--db-path", type=Path, default=config.DB_PATH)
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level,
                        format="%(levelname)s %(name)s: %(message)s")
    build_database(raw_dir=args.raw_dir, db_path=args.db_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
