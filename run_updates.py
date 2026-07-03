#!/usr/bin/env python3
"""
download_csv.py

Cross-platform script that:
  1. Downloads a .ods (OpenDocument Spreadsheet) file from a public Google
     Sheets "publish to web" URL.
  2. Extracts the sheet/tab named "DO_NOT_TOUCH(Converter_Interface)".
  3. Saves it as: _data/books-metadata.csv
  4. Launches Jekyll via: jekyll serve

Dependencies (install once):
    pip install requests pandas odfpy

Usage:
    python download_csv.py
"""

import os
import sys
import pathlib
import tempfile

# ── Third-party ──────────────────────────────────────────────────────────────
try:
    import requests
except ImportError:
    sys.exit(
        "[ERROR] 'requests' is not installed.\n"
        "Run:  pip install requests"
    )

try:
    import pandas as pd
except ImportError:
    sys.exit(
        "[ERROR] 'pandas' is not installed.\n"
        "Run:  pip install pandas odfpy"
    )

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
ODS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ4lOKlUnTG99YQ6c09QnwZ_bLxdqeIJhDRR5JQaDlgeQMFwUS2OGaWQ_3VyXIDKKPZAa3xYjTgbTLh/pub?output=ods"
SHEET_NAME = "DO_NOT_TOUCH(Converter_Interface)"
OUTPUT_DIR = "_data"                             # relative to cwd
OUTPUT_FILENAME = "books-metadata.csv"
# ─────────────────────────────────────────────────────────────────────────────


def download_ods(url: str) -> pathlib.Path:
    """Download the .ods file at *url* to a temp file and return its path."""
    print(f"[INFO] Downloading: {url}")
    try:
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        sys.exit(f"[ERROR] Download failed: {exc}")

    tmp = tempfile.NamedTemporaryFile(suffix=".ods", delete=False)
    with tmp as fh:
        for chunk in response.iter_content(chunk_size=8192):
            fh.write(chunk)

    return pathlib.Path(tmp.name)

def convert_sheet_to_csv(ods_path: pathlib.Path, sheet_name: str, output_path: pathlib.Path) -> None:
    """Read *sheet_name* from the .ods file at *ods_path* and write it as CSV."""
    print(f"[INFO] Reading sheet: {sheet_name}")
    try:
        df = pd.read_excel(ods_path, sheet_name=sheet_name, engine="odf")
    except ValueError as exc:
        all_sheets = pd.ExcelFile(ods_path, engine="odf").sheet_names
        sys.exit(
            f"[ERROR] Could not find sheet '{sheet_name}': {exc}\n"
            f"[INFO] Available sheets: {all_sheets}"
        )

    # ── Drop trailing "phantom" rows (formulas filled down past real data) ──
    before = len(df)
    df = df[df["title"].astype(str).str.strip() != "0"]
    df = df.dropna(subset=["title"])
    after = len(df)
    print(f"[INFO] Dropped {before - after} empty/formula rows (kept {after})")

    # ── Blank out "0" everywhere ─────────────────────────────────────────
    # No column in this sheet legitimately contains a literal 0 — every
    # occurrence comes from formulas resolving blank source cells to 0.
    # Safe to strip globally rather than column-by-column.
    df = df.replace([0, "0", 0.0, "0.0"], "")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"[DONE] {OUTPUT_FILENAME} is ready at:\n       {output_path}")

def main():
    output_path = pathlib.Path.cwd() / OUTPUT_DIR / OUTPUT_FILENAME

    ods_path = download_ods(ODS_URL)
    try:
        convert_sheet_to_csv(ods_path, SHEET_NAME, output_path)
    finally:
        ods_path.unlink(missing_ok=True)  # clean up temp file

    print("[INFO] Starting Jekyll server...")
    os.system("jekyll serve")


if __name__ == "__main__":
    main()