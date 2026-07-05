#!/usr/bin/env python3
"""
CB-Remix-scripts/export_metadata_csv.py

Turns the raw "DO_NOT_TOUCH(Converter_Interface)" (books/collection
metadata) sheet — already read into a DataFrame — into the CSV file
CollectionBuilder actually uses (_data/books-metadata.csv), applying the
sheet-specific cleanup that raw spreadsheet exports need:

  - Drops trailing "phantom" rows: rows where formulas were filled down
    past the real data, leaving a "title" of "0" or blank.
  - Blanks out literal "0" everywhere else: no column in this sheet
    legitimately contains a literal 0 — every occurrence comes from
    formulas resolving blank source cells to 0.

Self-contained: the function below only needs `pandas`, so this file can
be copy-pasted on its own into a new conversation/file if you just want to
iterate on this piece. It does NOT talk to the network, Google Sheets, or
the ODS file directly — it only operates on a DataFrame handed to it
(already produced by read_sheet() in the root download_csv.py).

Dependencies (install once):
    pip install pandas

Usage (as a library, not run directly):
    from export_metadata_csv import export_metadata_csv
"""


def export_metadata_csv(metadata_df, output_path):
    """Clean the raw metadata DataFrame and write it to *output_path* as CSV.

    *metadata_df* is the raw "DO_NOT_TOUCH(Converter_Interface)" sheet, as
    read straight off the spreadsheet (no cleanup applied yet).
    *output_path* is a pathlib.Path (or str) for the CSV file to write,
    e.g. _data/books-metadata.csv — its parent directory is created if
    needed.

    Returns the cleaned DataFrame (the same one written to disk), in case
    the caller also wants to keep it in memory.
    """
    import pathlib
    import pandas as pd

    df = metadata_df

    # ── Drop trailing "phantom" rows (formulas filled down past real data) ──
    # Scoped to this sheet specifically, since it's the one keyed on a
    # "title" column (a spreadsheet formula filled far past the real data
    # will show up here as title == "0", "", or NaN).
    if "title" in df.columns:
        before = len(df)
        stripped_title = df["title"].astype(str).str.strip()
        df = df[(stripped_title != "0") & (stripped_title != "") & (stripped_title.str.lower() != "nan")]
        after = len(df)
        print(f"[INFO] [metadata] Dropped {before - after} empty/formula rows (kept {after})")

    # ── Blank out "0" everywhere ─────────────────────────────────────────
    # No column in this sheet legitimately contains a literal 0 — every
    # occurrence comes from formulas resolving blank source cells to 0.
    # Safe to strip globally rather than column-by-column.
    df = df.replace([0, "0", 0.0, "0.0"], "")

    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[DONE] {output_path.name} is ready at:\n       {output_path}")

    return df
