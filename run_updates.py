#!/usr/bin/env python3
"""
download_csv.py

Cross-platform script that:
  1. Downloads a .csv file directly from a Google Sheets public export URL.
  2. Saves (or overwrites) the result as:  _data/books-metadata.csv
  3. Launches Jekyll via: jekyll serve

Dependencies (install once):
    pip install requests

Usage:
    python download_csv.py
"""

import os
import sys
import pathlib

# ── Third-party ──────────────────────────────────────────────────────────────
try:
    import requests
except ImportError:
    sys.exit(
        "[ERROR] 'requests' is not installed.\n"
        "Run:  pip install requests"
    )

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTOJ65zw28y13QZmsFBDHkS9DZo1Jw1SVOfulvrmyEzR9hMoWdnd5CYGDKpWoVWq-dhoTIOli16M_Yo/pub?gid=1031064181&single=true&output=csv"
OUTPUT_DIR = "_data"                             # relative to cwd
OUTPUT_FILENAME = "books-metadata.csv"
# ─────────────────────────────────────────────────────────────────────────────


def download_csv(url: str, output_path: pathlib.Path) -> None:
    """Download the CSV at *url* and save it to *output_path*."""
    print(f"[INFO] Downloading: {url}")
    try:
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        sys.exit(f"[ERROR] Download failed: {exc}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as fh:
        for chunk in response.iter_content(chunk_size=8192):
            fh.write(chunk)

    print(f"[DONE] {OUTPUT_FILENAME} is ready at:\n       {output_path}")


def main():
    output_path = pathlib.Path.cwd() / OUTPUT_DIR / OUTPUT_FILENAME
    download_csv(CSV_URL, output_path)

    print("[INFO] Starting Jekyll server...")
    os.system("jekyll serve")


if __name__ == "__main__":
    main()