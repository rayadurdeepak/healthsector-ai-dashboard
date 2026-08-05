"""
SQLite storage layer -- single source of truth for everything the
pipeline produces (predictions, news, paper trades, accuracy checks,
market indexes).

Why SQLite instead of the plain CSV-append logic used before: SQLite
enforces one real table per data type instead of us hand-rolling
column-overlap checks before every append (that's what caused the
contaminated-history-file incident earlier). It's a single file
(healthcare_pipeline/output/healthcare.db) -- no server to install, no
separate service to run, just a file like a CSV. Every table is also
auto-exported back to the same CSV filenames you already had, so Excel
and Power BI keep working exactly like before with zero extra setup.

Basic usage:
    import db
    db.save_dataframe("predictions", today_df)
    df = db.load_table("predictions")
    db.export_all_to_csv()
"""

import os
import sqlite3

import pandas as pd

import config

DB_PATH = os.path.join(config.OUTPUT_DIR, "healthcare.db")

# table_name -> csv filename exported after every write, so anything
# already pointed at the old CSVs (Power BI, Excel, your own scripts)
# keeps working unchanged.
CSV_EXPORT_MAP = {
    "predictions": "prediction_models.csv",
    "predictions_latest": "healthcare_full_data.csv",
    "news_archive": "news_archive.csv",
    "paper_trades": "paper_trade_ledger.csv",
    "accuracy_detail": "accuracy_tracking_detail.csv",
    "accuracy_summary": "accuracy_scorecard.csv",
    "market_indexes": "market_indexes.csv",
    "predictions_timeline": "predictions_timeline.csv",
}


def get_connection():
    return sqlite3.connect(DB_PATH)


def _align_columns(conn, table_name: str, df: pd.DataFrame):
    """If the table already exists but is missing columns that `df` has
    (e.g. a new field got added to the pipeline), add them via ALTER
    TABLE instead of letting the insert fail. This is what makes schema
    evolution safe -- new columns show up as NULL for old rows instead of
    breaking the whole save."""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if cur.fetchone() is None:
        return  # table doesn't exist yet -- to_sql will create it fresh, nothing to align
    existing_cols = {row[1] for row in cur.execute(f'PRAGMA table_info("{table_name}")')}
    for col in df.columns:
        if col not in existing_cols:
            safe_col = col.replace('"', '""')
            try:
                cur.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{safe_col}" TEXT')
            except sqlite3.OperationalError:
                pass  # column race/already added -- non-fatal
    conn.commit()


def save_dataframe(table_name: str, df: pd.DataFrame, mode: str = "append",
                    dedupe_subset: list = None, dedupe_keep: str = "last",
                    sort_before_dedupe: str = None):
    """
    Writes df into `table_name`. mode="append" adds rows (the normal
    case for daily logs); mode="replace" overwrites the whole table (used
    for the "latest snapshot" tables like today's full prediction sheet).

    dedupe_subset: if given, drops duplicate rows on those columns AFTER
    the append -- e.g. so re-running main.py twice on the same day
    doesn't double-log everything.
    dedupe_keep: "last" (default -- e.g. predictions: a same-day re-run
    should overwrite the earlier one) or "first" (e.g. news archive: keep
    the date a headline was FIRST seen, not the latest date it reappeared
    in the RSS feed).
    sort_before_dedupe: optional column to sort by before deduping, so
    "first"/"last" refers to that column's order rather than row order.
    """
    if df is None or df.empty:
        return

    df = df.copy()
    df.columns = [str(c) for c in df.columns]

    conn = get_connection()
    try:
        if mode == "append":
            _align_columns(conn, table_name, df)
        df.to_sql(table_name, conn, if_exists=("replace" if mode == "replace" else "append"), index=False)

        if dedupe_subset:
            full = pd.read_sql(f'SELECT * FROM "{table_name}"', conn)
            before = len(full)
            if sort_before_dedupe and sort_before_dedupe in full.columns:
                full = full.sort_values(sort_before_dedupe)
            full = full.drop_duplicates(subset=dedupe_subset, keep=dedupe_keep)
            if len(full) != before:
                full.to_sql(table_name, conn, if_exists="replace", index=False)
    finally:
        conn.close()

    _export_table_to_csv(table_name)


def load_table(table_name: str) -> pd.DataFrame:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if cur.fetchone() is None:
            return pd.DataFrame()
        return pd.read_sql(f'SELECT * FROM "{table_name}"', conn)
    finally:
        conn.close()


def _export_table_to_csv(table_name: str):
    csv_name = CSV_EXPORT_MAP.get(table_name)
    if not csv_name:
        return
    df = load_table(table_name)
    if df.empty:
        return
    path = os.path.join(config.OUTPUT_DIR, csv_name)
    try:
        df.to_csv(path, index=False)
    except Exception as e:  # noqa: BLE001
        print(f"[db] WARNING: couldn't export {table_name} to {path}: {e}")


def export_all_to_csv():
    for table_name in CSV_EXPORT_MAP:
        _export_table_to_csv(table_name)
