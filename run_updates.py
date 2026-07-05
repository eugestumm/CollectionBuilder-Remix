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


def _get_ods_cell_text(cell) -> str:
    """Extract a cell's text, preserving paragraph breaks as "\\n".

    ODS stores each line of a multi-line cell as a separate <text:p>
    element. odfpy's teletype.extractText(), when called on the *cell*
    directly, concatenates every descendant paragraph's text with NO
    separator at all — so a cell like:
        "First paragraph."
        ""
        "Second paragraph."
    comes back as "First paragraph.Second paragraph." (newlines silently
    dropped). Extracting each <text:p> individually and joining with "\\n"
    keeps the original line breaks intact.
    """
    from odf.text import P
    from odf import teletype

    paragraphs = cell.getElementsByType(P)
    if not paragraphs:
        return ""
    return "\n".join(teletype.extractText(p) for p in paragraphs)


def read_sheet(ods_path: pathlib.Path, sheet_name: str) -> pd.DataFrame:
    """Read a single named sheet from the .ods file into a DataFrame.

    Uses odfpy directly (not pandas.read_excel(engine="odf")) specifically
    to preserve line breaks inside multi-paragraph cells — see
    _get_ods_cell_text() for why that matters.
    """
    from odf.opendocument import load
    from odf.table import Table, TableRow, TableCell

    print(f"[INFO] Reading sheet: {sheet_name}")
    doc = load(str(ods_path))
    tables = doc.spreadsheet.getElementsByType(Table)
    table = next((t for t in tables if t.getAttribute("name") == sheet_name), None)

    if table is None:
        available = [t.getAttribute("name") for t in tables]
        sys.exit(
            f"[ERROR] Could not find sheet '{sheet_name}'\n"
            f"[INFO] Available sheets: {available}"
        )

    rows_data = []
    for row in table.getElementsByType(TableRow):
        row_repeat = int(row.getAttribute("numberrowsrepeated") or 1)
        row_values = []
        for cell in row.getElementsByType(TableCell):
            col_repeat = int(cell.getAttribute("numbercolumnsrepeated") or 1)
            text = _get_ods_cell_text(cell)
            row_values.extend([text] * col_repeat)

        if all(v == "" for v in row_values):
            # Don't materialize huge runs of blank filler rows (common at
            # the tail of a Google Sheets ODS export).
            continue
        for _ in range(row_repeat):
            rows_data.append(list(row_values))

    while rows_data and all(v == "" for v in rows_data[-1]):
        rows_data.pop()  # defensive: trim any trailing blank row that slipped through

    if not rows_data:
        return pd.DataFrame()

    max_len = max(len(r) for r in rows_data)
    rows_data = [r + [""] * (max_len - len(r)) for r in rows_data]

    header, *data = rows_data
    return pd.DataFrame(data, columns=header)


def clean_dataframe(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    """Apply shared cleanup rules to a sheet's DataFrame."""
    # ── Drop trailing "phantom" rows (formulas filled down past real data) ──
    # Only applies to the books sheet, which is keyed on a "title" column.
    if sheet_name == DROP_PHANTOM_ROWS_ON and "title" in df.columns:
        before = len(df)
        stripped_title = df["title"].astype(str).str.strip()
        df = df[(stripped_title != "0") & (stripped_title != "") & (stripped_title.str.lower() != "nan")]
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


def build_pages_from_sheet(pages_df, config_df=None, base_dir: str = ".") -> None:
    """Generate Jekyll markdown pages from the "pages" spreadsheet tab.

    Self-contained: everything needed (column names, folder-name lookup,
    the front-matter builder, the imports it uses) lives inside this
    function, so it can be copy-pasted on its own into a new
    conversation/file. Only needs `pandas` and `ruamel.yaml` installed.

    Expected columns in *pages_df*:
        filename, title-lang1, content-lang1, title-lang2, content-lang2,
        permalink, layout, extra-metadata

    *config_df* is the "config" tab (columns: category, content). It's used
    only to look up the "lang2-id" category (e.g. "pt", "es") so the
    foreign-language folder is named after whatever language code is
    actually configured, instead of being hardcoded to "pt". If *config_df*
    is omitted, or "lang2-id" isn't found/blank there, it falls back to "pt".

    For each row, up to two markdown files are written:
        <base_dir>/pages/<filename>.md        (lang1 / English)
        <base_dir>/<lang2 folder>/<filename>.md   (lang2, e.g. pt/)

    Front matter is built as an actual dict and dumped with ruamel.yaml, so
    values with colons, quotes, or accented characters are escaped
    correctly — never hand-built as raw text.

    Field placement, matching the two example files:
        - lang1 (pages/):  title, layout, permalink, then any extra-metadata
          keys. permalink IS included, since only the lang2 folder gets an
          automatic permalink prefix from _config.yml's `defaults:` block.
        - lang2 folder:    title, layout, then any extra-metadata keys.
          permalink is deliberately OMITTED here — Jekyll's `defaults:`
          scope for that path already assigns a permalink automatically.

    "extra-metadata" is parsed as one "key: value" pair per line (a cell can
    have multiple lines if the sheet author used Alt+Enter for more than
    one extra field) and merged into both language versions' front matter.

    A markdown file is only written if there's actually something to put in
    it: for lang1 that means title/content/permalink/layout/extra-metadata
    aren't ALL blank; for lang2, same but without permalink in that check
    (since lang2 never uses it). This is why, for example, a row with only
    a permalink and no lang2 title/content produces just the lang1 page.

    Special case: the "index" filename is never written to the lang1
    (pages/) folder — Jekyll doesn't want a pages/index.md alongside the
    site's own root index. Instead, it's written directly at the project
    root as <base_dir>/index.md, with a different field set matching
    Jekyll/CollectionBuilder's homepage convention:
        layout: <layout column, cleaned>
        title:  <title-lang1>
        lang:   <config's "lang1-id", e.g. "en">
    (no permalink — the root index doesn't need one).
    The lang2 (foreign-language) version of "index" is unaffected by this
    and still goes through the normal lang2 handling below, e.g. producing
    <lang2 folder>/index.md as the site's foreign-language homepage.
    """
    import io
    import pathlib
    import pandas as pd
    from ruamel.yaml import YAML

    COL_FILENAME = "filename"
    COL_TITLE_LANG1 = "title-lang1"
    COL_CONTENT_LANG1 = "content-lang1"
    COL_TITLE_LANG2 = "title-lang2"
    COL_CONTENT_LANG2 = "content-lang2"
    COL_PERMALINK = "permalink"
    COL_LAYOUT = "layout"
    COL_EXTRA_METADATA = "extra-metadata"

    LANG1_FOLDER = "pages"
    DEFAULT_LANG1_ID = "en"
    DEFAULT_LANG2_FOLDER = "pt"
    LANG1_ID_CATEGORY = "lang1-id"
    LANG2_ID_CATEGORY = "lang2-id"
    CONFIG_CATEGORY_COL = "category"
    CONFIG_CONTENT_COL = "content"
    ROOT_INDEX_FILENAME = "index"

    required_cols = [
        COL_FILENAME, COL_TITLE_LANG1, COL_CONTENT_LANG1,
        COL_TITLE_LANG2, COL_CONTENT_LANG2, COL_PERMALINK,
        COL_LAYOUT, COL_EXTRA_METADATA,
    ]
    missing_cols = [c for c in required_cols if c not in pages_df.columns]
    if missing_cols:
        print(f"[WARN] pages sheet is missing column(s) {missing_cols} — skipping page generation")
        return

    def clean(value) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip()

    def clean_layout(value) -> str:
        """Like clean(), but also strips a redundant "layout:" prefix, in
        case the "layout" cell was typed as "layout: home-infographic"
        instead of just "home-infographic" — otherwise that literal prefix
        would end up nested inside the front matter's own `layout:` key.
        """
        text = clean(value)
        if text.lower().startswith("layout:"):
            text = text.split(":", 1)[1].strip()
        return text

    def get_config_category_value(category: str, default: str) -> str:
        """Look up a single category's value in config_df (columns:
        category, content), falling back to *default* if config_df is
        missing, malformed, or the category isn't there / is blank.
        """
        if config_df is None:
            return default
        if CONFIG_CATEGORY_COL not in config_df.columns or CONFIG_CONTENT_COL not in config_df.columns:
            return default

        match = config_df[config_df[CONFIG_CATEGORY_COL].astype(str).str.strip() == category]
        if match.empty:
            return default

        value = clean(match.iloc[0][CONFIG_CONTENT_COL])
        return value or default

    def get_lang1_id() -> str:
        return get_config_category_value(LANG1_ID_CATEGORY, DEFAULT_LANG1_ID)

    def get_lang2_folder_name() -> str:
        return get_config_category_value(LANG2_ID_CATEGORY, DEFAULT_LANG2_FOLDER)

    def parse_extra_metadata(raw: str) -> dict:
        """Turn "key: value" lines (one or more, newline-separated) into a dict."""
        pairs = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, _, val = line.partition(":")
            pairs[key.strip()] = val.strip()
        return pairs

    def write_markdown(folder: pathlib.Path, filename: str, front_matter: dict, body: str) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        file_path = folder / f"{filename}.md"

        yaml = YAML()
        yaml.default_flow_style = False
        yaml.allow_unicode = True

        buf = io.StringIO()
        yaml.dump(front_matter, buf)

        file_path.write_text(
            "---\n" + buf.getvalue() + "---\n\n" + body.strip() + "\n",
            encoding="utf-8",
        )
        print(f"[DONE] Wrote {file_path}")

    base = pathlib.Path(base_dir)
    lang1_dir = base / LANG1_FOLDER
    lang2_folder_name = get_lang2_folder_name()
    lang2_dir = base / lang2_folder_name
    lang1_id = get_lang1_id()
    print(f"[INFO] lang2 folder resolved to: {lang2_folder_name}")

    for _, row in pages_df.iterrows():
        filename = clean(row[COL_FILENAME])
        if not filename:
            continue  # can't create a file without a name

        permalink = clean(row[COL_PERMALINK])
        layout = clean_layout(row[COL_LAYOUT])
        extra_meta = parse_extra_metadata(clean(row[COL_EXTRA_METADATA]))

        title1 = clean(row[COL_TITLE_LANG1])
        content1 = clean(row[COL_CONTENT_LANG1])

        if filename == ROOT_INDEX_FILENAME:
            # Special case: site homepage. Written directly at the project
            # root (base_dir/index.md), NOT inside pages/ — Jekyll doesn't
            # want a pages/index.md alongside the site's own root index.
            # Field order matches Jekyll/CollectionBuilder's expectation:
            # layout, title, lang (lang comes from config's "lang1-id",
            # not from a spreadsheet column on this row).
            front_matter_root = {}
            if layout:
                front_matter_root["layout"] = layout
            if title1:
                front_matter_root["title"] = title1
            front_matter_root["lang"] = lang1_id
            front_matter_root.update(extra_meta)
            write_markdown(base, filename, front_matter_root, content1)
        elif title1 or content1 or permalink or layout or extra_meta:
            # ── lang1 (English) -> pages/<filename>.md ─────────────────
            front_matter1 = {}
            if title1:
                front_matter1["title"] = title1
            if layout:
                front_matter1["layout"] = layout
            if permalink:
                front_matter1["permalink"] = permalink
            front_matter1.update(extra_meta)
            write_markdown(lang1_dir, filename, front_matter1, content1)

        # ── lang2 -> <lang2 folder>/<filename>.md ───────────────────────
        title2 = clean(row[COL_TITLE_LANG2])
        content2 = clean(row[COL_CONTENT_LANG2])
        if title2 or content2 or layout or extra_meta:
            front_matter2 = {}
            if title2:
                front_matter2["title"] = title2
            if layout:
                front_matter2["layout"] = layout
            front_matter2.update(extra_meta)
            write_markdown(lang2_dir, filename, front_matter2, content2)


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

    update_config_yml(pathlib.Path.cwd() / CONFIG_YML_PATH, dataframes[CONFIG_SHEET_NAME])
    build_pages_from_sheet(dataframes["pages"], dataframes[CONFIG_SHEET_NAME], base_dir=pathlib.Path.cwd())

    print("[INFO] Starting Jekyll server...")
    os.system("jekyll serve")


if __name__ == "__main__":
    main()