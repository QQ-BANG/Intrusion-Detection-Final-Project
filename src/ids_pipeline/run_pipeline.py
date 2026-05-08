# pipeline driver

#   python -m ids_pipeline.run_pipeline  for full pipeline     

import argparse
import logging
import sys
import time

from . import config
from .build_database import build_database
from .download_data import download_nsl_kdd
from .features import load_dataframe
from .train_models import train_all
from .visualize import (
    plot_class_balance, plot_protocol_distribution,
    plot_top_services, plot_bytes_distribution,
    plot_correlation_heatmap,)

log = logging.getLogger("ids_pipeline")


def banner(name):
    log.info("=== STEP: %s ===", name)
    return time.time()


def done(name, t0):
    log.info("--- %s done in %.2fs ---", name, time.time() - t0)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--skip-download", action="store_true")
    p.add_argument("--skip-db", action="store_true",
                   help="reuse existing data/processed/ids.sqlite")
    p.add_argument("--eda-only", action="store_true",
                   help="download + db + plots, no training")
    p.add_argument("--no-eda", action="store_true")
    p.add_argument("--cv-folds", type=int, default=0)
    p.add_argument("--quick", action="store_true",
                   help="train on 10%% of the data (smoke test)")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # download
    if not args.skip_download:
        t0 = banner("Download")
        try:
            download_nsl_kdd()
        except Exception as e:
            log.error("Download failed (%s). Place files manually in %s.",
                      e, config.RAW_DIR)
            return 2
        done("Download", t0)

    # build the db
    if not args.skip_db:
        t0 = banner("Build database")
        build_database()
        done("Build database", t0)

    # EDA plots
    if not args.no_eda:
        t0 = banner("EDA visualizations")
        df = load_dataframe()
        plot_class_balance(df)
        plot_protocol_distribution(df)
        plot_top_services(df)
        plot_bytes_distribution(df)
        plot_correlation_heatmap(df)
        done("EDA visualizations", t0)

    if args.eda_only:
        return 0

    # train models
    t0 = banner("Train models")
    train_all(
        cv_folds=args.cv_folds,
        sample_frac=0.1 if args.quick else None, )
    done("Train models", t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
