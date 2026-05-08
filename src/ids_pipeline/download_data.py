# downloads the NSL-KDD txt files from github mirrors if fails ill just do it by hand

import logging
import sys

import requests
from tqdm import tqdm

from . import config

log = logging.getLogger(__name__)


def try_download(url, dest, timeout=30):
    # returns True on success, False on any error, so we move to the next mirror
    try:
        r = requests.get(url, stream=True, timeout=timeout)
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        # write to a .part file first, then rename. This is to try and prevent corruption of file
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as fh:
            bar = tqdm(total=total, unit="B", unit_scale=True,
                       desc=dest.name, leave=False)
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    fh.write(chunk)
                    bar.update(len(chunk))
            bar.close()
        tmp.replace(dest)
        return True
    except Exception as e:
        log.warning("Failed to download %s (%s)", url, e)
        return False


def fetch_file(name, urls, raw_dir):
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / name
    if dest.exists() and dest.stat().st_size > 0:
        log.info("Already present: %s (%d bytes)", dest, dest.stat().st_size)
        return dest

    for url in urls:
        log.info("Trying mirror: %s", url)
        ok = try_download(url, dest)
        if ok:
            log.info("Saved %s", dest)
            return dest

    raise RuntimeError(
        "Could not download " + name + " from any mirror. "
        "Please place the file manually in " + str(raw_dir)
    )


def download_nsl_kdd(raw_dir=None):
    if raw_dir is None:
        raw_dir = config.RAW_DIR
    paths = {}
    for name, urls in config.NSL_KDD_URLS.items():
        paths[name] = fetch_file(name, urls, raw_dir)
    return paths


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        paths = download_nsl_kdd()
    except Exception as e:
        log.error("Download failed: %s", e)
        return 1
    for name, p in paths.items():
        print(name, "->", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
