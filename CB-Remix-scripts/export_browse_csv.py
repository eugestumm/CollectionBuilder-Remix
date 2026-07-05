#!/usr/bin/env python3
"""
CB-Remix-scripts/export_browse_csv.py

Turns the raw "config-browse" sheet — already read into a DataFrame — into
the CSV file the Jekyll site's browse config actually uses
(_data/config-browse.csv), applying the sheet-specific cleanup that raw
spreadsheet exports need:

  - Drops trailing "phantom" rows: rows where formulas were filled down
    past the real data, leaving a "field" of "0" or blank.
  - Blanks out literal "0" everywhere else: no column in this sheet
    legitimately contains a literal 0 — every occurrence comes from
    formulas resolving blank source cells to 0.
  - Writes RAGGED rows: trailing empty cells are dropped from the end of
    each row (matching how Google Sheets' own "publish to web as csv"
    export behaves), so e.g. "subject-en,,en,true" (4 fields) is written
    as-is even though the sheet has 6 columns, rather than padded out to
    "subject-en,,en,true,,".

Self-contained: the function below only needs `pandas` (stdlib `csv` for
writing), so this file can be copy-pasted on its own into a new
conversation/file if you just want to iterate on this piece. It does NOT
talk to the network, Google Sheets, or the ODS file directly — it only
operates on a DataFrame handed to it (already produced by read_sheet() in
the root download_csv.py).

Dependencies (install once):
    pip install pandas

Usage (as a library, not run directly):
    from export_browse_csv import export_browse_csv
"""

import pandas as pd


def export_browse_csv(browse_df, output_path):
    """Clean the raw config-browse DataFrame and write it to *output_path*
    as CSV.

    *browse_df* is the raw "config-browse" sheet, as read straight off the
    spreadsheet (no cleanup applied yet). Expected columns include:
        field, translate_id_browse, lang, btn, hidden, translate_id_sort_name
    *output_path* is a pathlib.Path (or str) for the CSV file to write,
    e.g. _data/config-browse.csv — its parent directory is created if
    needed.

    Returns the cleaned DataFrame (the same one written to disk), in case
    the caller also wants to keep it in memory.
    """
    import csv
    import pathlib

    df = browse_df

    # ── Drop phantom rows (formulas filled down past real data) ─────────
    # Scoped to this sheet specifically, since it's keyed on "field" (a
    # spreadsheet formula filled far past the real data will show up here
    # as field == "0", "", or NaN).
    if "field" in df.columns:
        before = len(df)
        stripped_field = df["field"].astype(str).str.strip()
        df = df[(stripped_field != "0") & (stripped_field != "") & (stripped_field.str.lower() != "nan")]
        after = len(df)
        print(f"[INFO] [config-browse] Dropped {before - after} empty/formula rows (kept {after})")

    # ── Blank out "0" everywhere ─────────────────────────────────────────
    # No column in this sheet legitimately contains a literal 0 — every
    # occurrence comes from formulas resolving blank source cells to 0.
    # Safe to strip globally rather than column-by-column.
    df = df.replace([0, "0", 0.0, "0.0"], "")

    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Write as RAGGED csv ──────────────────────────────────────────────
    # Trim trailing empty cells off each row before writing, instead of
    # using df.to_csv() (which would keep every row at the full column
    # count).
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(df.columns.tolist())
        for row in df.itertuples(index=False, name=None):
            row = [("" if pd.isna(v) else str(v)) for v in row]
            while row and row[-1] == "":
                row.pop()
            writer.writerow(row)

    print(f"[DONE] {output_path.name} is ready at:\n       {output_path}")

    return df
