#!/usr/bin/env python3
"""
download_csv.py

Cross-platform script that:
  1. Downloads a .ods (OpenDocument Spreadsheet) file from a public Google
     Sheets "publish to web" URL.
  2. Extracts three sheets/tabs:
       - "DO_NOT_TOUCH(Converter_Interface)"  -> exported to _data/books-metadata.csv
       - "pages"                              -> kept in memory only
       - "config"                             -> kept in memory only
  3. Uses the "config" tab (columns: category, content) to patch matching
     top-level fields in _config.yml, leaving comments/formatting intact.
  4. Launches Jekyll via: jekyll serve

Dependencies (install once):
    pip install requests pandas odfpy ruamel.yaml

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

try:
    from ruamel.yaml import YAML
except ImportError:
    sys.exit(
        "[ERROR] 'ruamel.yaml' is not installed.\n"
        "Run:  pip install ruamel.yaml"
    )

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
ODS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ4lOKlUnTG99YQ6c09QnwZ_bLxdqeIJhDRR5JQaDlgeQMFwUS2OGaWQ_3VyXIDKKPZAa3xYjTgbTLh/pub?output=ods"
OUTPUT_DIR = "_data"  # relative to cwd

# Sheets that get written to disk as CSV: {sheet name in workbook -> output filename}
EXPORT_SHEETS = {
    "DO_NOT_TOUCH(Converter_Interface)": "books-metadata.csv",
}

# Sheets that are only kept in memory (as DataFrames) for later use — not
# written to disk.
MEMORY_ONLY_SHEETS = ["pages", "config"]

# Only the books sheet has a "title" column with formula-filled phantom rows
# past the real data, so this row-drop is scoped to that sheet only.
DROP_PHANTOM_ROWS_ON = "DO_NOT_TOUCH(Converter_Interface)"

# _config.yml gets its fields patched from the "config" sheet, whose columns
# are named as below (case-insensitive match against these).
CONFIG_YML_PATH = "_config.yml"
CONFIG_SHEET_NAME = "config"
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


def read_sheet(ods_path: pathlib.Path, sheet_name: str) -> pd.DataFrame:
    """Read a single named sheet from the .ods file into a DataFrame."""
    print(f"[INFO] Reading sheet: {sheet_name}")
    try:
        df = pd.read_excel(ods_path, sheet_name=sheet_name, engine="odf")
    except ValueError as exc:
        all_sheets = pd.ExcelFile(ods_path, engine="odf").sheet_names
        sys.exit(
            f"[ERROR] Could not find sheet '{sheet_name}': {exc}\n"
            f"[INFO] Available sheets: {all_sheets}"
        )
    return df


def clean_dataframe(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    """Apply shared cleanup rules to a sheet's DataFrame."""
    # ── Drop trailing "phantom" rows (formulas filled down past real data) ──
    # Only applies to the books sheet, which is keyed on a "title" column.
    if sheet_name == DROP_PHANTOM_ROWS_ON and "title" in df.columns:
        before = len(df)
        df = df[df["title"].astype(str).str.strip() != "0"]
        df = df.dropna(subset=["title"])
        after = len(df)
        print(f"[INFO] [{sheet_name}] Dropped {before - after} empty/formula rows (kept {after})")

    # ── Blank out "0" everywhere ─────────────────────────────────────────
    # No column in these sheets legitimately contains a literal 0 — every
    # occurrence comes from formulas resolving blank source cells to 0.
    # Safe to strip globally rather than column-by-column.
    df = df.replace([0, "0", 0.0, "0.0"], "")

    return df


def update_config_yml(
    yaml_path: pathlib.Path,
    config_df,
    category_col: str = "category",
    content_col: str = "content",
) -> None:
    """Patch fields in a Jekyll _config.yml from the "config" spreadsheet tab.

    Self-contained: everything needed (the field map, the path-setter, the
    imports it uses) lives inside this function, so it can be copy-pasted
    on its own into a new conversation/file. Only needs `pandas` (as `pd`
    somewhere importable) and `ruamel.yaml` installed in the environment.

    Driven entirely by FIELD_MAP below: for each (yaml_path, category) pair,
    look up *category* in the spreadsheet and, if a non-blank value is
    found, write it to *yaml_path* in the yaml file.

    - Paths under "site_languages" are created if missing (that block is
      meant to be generated by this script).
    - All other paths must already exist in _config.yml, or the write is
      skipped and reported — this avoids silently inventing new top-level
      keys with no surrounding comment/context.
    - A blank cell in the spreadsheet is skipped rather than clearing an
      existing value.

    Uses ruamel.yaml (round-trip mode) instead of PyYAML specifically
    because it preserves comments and key ordering, which a plain
    yaml.safe_load/yaml.dump cycle would otherwise strip out.
    """
    import re
    import pandas as pd
    from ruamel.yaml import YAML

    # ── yaml_path -> spreadsheet category ───────────────────────────────
    # One line per field. Left side is where it lives in _config.yml (dot
    # path, with [N] for a position inside a list). Right side is the
    # "category" value to look for in the spreadsheet's "config" tab.
    # To wire up a new field, just add a line here.
    FIELD_MAP = {
        "url":                                      "url",
        "baseurl":                                  "baseurl",
        "source-code":                              "source-code",

        # lang1 (English) is the site's default language, so it uses the
        # plain top-level fields directly.
        "title":                                    "title-lang1",
        "tagline":                                  "tagline-lang1",
        "description":                              "description-lang1",

        # site_languages[0] = lang1 (English), site_languages[1] = lang2 (Portuguese)
        "site_languages[0].lang_id":                "lang1-id",
        "site_languages[0].lang_display":           "lang1",
        "site_languages[1].lang_id":                "lang2-id",
        "site_languages[1].lang_display":           "lang2",
        "site_languages[1].lang_site_title":        "title-lang2",
        "site_languages[1].lang_site_tagline":      "tagline-lang2",
        "site_languages[1].lang_site_description":  "description-lang2",
    }

    path_segment_re = re.compile(r"^([\w-]+)(?:\[(\d+)\])?$")

    def set_yaml_path(config_data, path: str, value, create_missing: bool = False) -> bool:
        """Set a value at a dot/bracket path like "site_languages[1].lang_display".

        If *create_missing* is False, the path must already exist (aside
        from the final key) or nothing is changed and False is returned.
        If True, missing dicts/list slots are created along the way.
        """
        segments = path.split(".")
        node = config_data

        for i, segment in enumerate(segments):
            match = path_segment_re.match(segment)
            key, index = match.group(1), match.group(2)
            is_last = i == len(segments) - 1

            if index is None:
                if is_last:
                    if key not in node and not create_missing:
                        return False
                    node[key] = value
                    return True
                if key not in node or node[key] is None:
                    if not create_missing:
                        return False
                    node[key] = {}
                node = node[key]
            else:
                index = int(index)
                if key not in node or node[key] is None:
                    if not create_missing:
                        return False
                    node[key] = []
                item_list = node[key]
                while len(item_list) <= index:
                    if not create_missing:
                        return False
                    item_list.append({})
                if is_last:
                    item_list[index] = value
                    return True
                node = item_list[index]

        return False

    if not yaml_path.exists():
        print(f"[WARN] {yaml_path} does not exist — skipping config update")
        return

    if category_col not in config_df.columns or content_col not in config_df.columns:
        print(
            f"[WARN] config sheet is missing '{category_col}' or '{content_col}' "
            f"column(s) — skipping config update. Found columns: {list(config_df.columns)}"
        )
        return

    # category -> cleaned value, straight from the spreadsheet
    values_by_category = {
        str(row[category_col]).strip(): (
            "" if pd.isna(row[content_col]) else str(row[content_col]).strip()
        )
        for _, row in config_df.iterrows()
    }

    yaml = YAML()
    yaml.preserve_quotes = True

    with open(yaml_path, "r", encoding="utf-8") as fh:
        config_data = yaml.load(fh)

    updated, skipped_missing, skipped_blank = [], [], []

    for yaml_field_path, category in FIELD_MAP.items():
        if category not in values_by_category:
            continue  # this category isn't in the spreadsheet at all

        value = values_by_category[category]
        if value == "":
            skipped_blank.append(yaml_field_path)
            continue

        create_missing = yaml_field_path.startswith("site_languages")
        if set_yaml_path(config_data, yaml_field_path, value, create_missing=create_missing):
            updated.append(yaml_field_path)
        else:
            skipped_missing.append(yaml_field_path)

    with open(yaml_path, "w", encoding="utf-8") as fh:
        yaml.dump(config_data, fh)

    print(f"[DONE] {yaml_path} updated. Fields set: {updated}")
    if skipped_missing:
        print(
            f"[WARN] These yaml paths don't exist in {yaml_path} (and aren't "
            f"auto-created), so they were skipped: {skipped_missing}"
        )
    if skipped_blank:
        print(f"[INFO] These fields were blank in the spreadsheet, so left untouched: {skipped_blank}")


def load_all_sheets(ods_path: pathlib.Path, output_dir: pathlib.Path) -> dict:
    """Read every configured sheet into a DataFrame.

    - Sheets in EXPORT_SHEETS are cleaned and written to CSV in *output_dir*.
    - Sheets in MEMORY_ONLY_SHEETS are cleaned but NOT written to disk —
      they're only returned, for use later in the same process.

    Returns a dict of {sheet_name: DataFrame} covering all loaded sheets.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    dataframes = {}

    for sheet_name, csv_filename in EXPORT_SHEETS.items():
        df = read_sheet(ods_path, sheet_name)
        df = clean_dataframe(df, sheet_name)
        dataframes[sheet_name] = df

        output_path = output_dir / csv_filename
        df.to_csv(output_path, index=False)
        print(f"[DONE] {csv_filename} is ready at:\n       {output_path}")

    for sheet_name in MEMORY_ONLY_SHEETS:
        df = read_sheet(ods_path, sheet_name)
        df = clean_dataframe(df, sheet_name)
        dataframes[sheet_name] = df
        print(f"[INFO] [{sheet_name}] Loaded into memory only ({len(df)} rows) — not exported to CSV")

    return dataframes


def main():
    output_dir = pathlib.Path.cwd() / OUTPUT_DIR

    ods_path = download_ods(ODS_URL)
    try:
        dataframes = load_all_sheets(ods_path, output_dir)
    finally:
        ods_path.unlink(missing_ok=True)  # clean up temp file

    # `dataframes["pages"]` is available here for whatever comes next.
    update_config_yml(pathlib.Path.cwd() / CONFIG_YML_PATH, dataframes[CONFIG_SHEET_NAME])

    print("[INFO] Starting Jekyll server...")
    os.system("jekyll serve")


if __name__ == "__main__":
    main()