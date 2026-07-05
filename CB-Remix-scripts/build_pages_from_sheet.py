#!/usr/bin/env python3
"""
CB-Remix-scripts/build_pages_from_sheet.py

Generates Jekyll markdown pages (English + foreign language, plus the
special-cased site homepage index.md) from the "pages" spreadsheet tab.

Self-contained: the function below imports everything it needs internally,
so this whole file can be copy-pasted on its own into a new
conversation/file if you just want to iterate on this piece.

Does NOT talk to the network or Google Sheets — it only operates on
DataFrames handed to it (pages_df, config_df) plus a base directory to
write files into.

Dependencies (install once):
    pip install pandas ruamel.yaml

Usage (as a library, not run directly):
    from build_pages_from_sheet import build_pages_from_sheet
"""


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
    to look up:
        - "lang2-id" (e.g. "pt", "es") so the foreign-language folder is
          named after whatever language code is actually configured,
          instead of being hardcoded to "pt". Falls back to "pt" if
          *config_df* is omitted or "lang2-id" isn't found/blank.
        - "lang1-id" (e.g. "en") used only for the special root index.md
          case below. Falls back to "en".

    For each row, up to two markdown files are written:
        <base_dir>/pages/<filename>.md        (lang1 / English)
        <base_dir>/<lang2 folder>/<filename>.md   (lang2, e.g. pt/)

    Front matter is built as an actual dict and dumped with ruamel.yaml, so
    values with colons, quotes, or accented characters are escaped
    correctly — never hand-built as raw text.

    Field placement, matching the example files:
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
