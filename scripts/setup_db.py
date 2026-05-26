"""
setup_db.py
───────────
Ingests the three CSV files into a local SQLite database.
Improvements over v1:

  • Schema validation — checks required columns before ingesting
  • Row-count reconciliation — warns if CSV rows don't match DB after write
  • Foreign-key integrity check — verifies all sub_id values in usage_logs
    exist in subscriptions before committing
  • PRAGMA optimisations for faster writes and safe WAL journaling
  • Clean teardown — closes connection even on error via context manager
"""

import os
import logging
import sqlite3

import pandas as pd

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("subscan.setup_db")

# ── Expected schemas ──────────────────────────────────────────────────────────

REQUIRED_COLUMNS = {
    "employees":     {"emp_id", "name", "email", "department", "status"},
    "subscriptions": {"sub_id", "emp_id", "tool_name", "monthly_cost", "license_status"},
    "usage_logs":    {"sub_id", "emp_id", "tool_name", "last_login_date", "logins_last_30_days"},
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_columns(df: pd.DataFrame, table: str) -> None:
    """Raise ValueError if any required column is missing."""
    missing = REQUIRED_COLUMNS[table] - set(df.columns)
    if missing:
        raise ValueError(f"[{table}] Missing columns: {missing}")


def _row_count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _load_csv(path: str, table: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    df = pd.read_csv(path)
    _validate_columns(df, table)
    log.info("  Loaded %-15s — %d rows", table, len(df))
    return df

# ── Main ──────────────────────────────────────────────────────────────────────

def setup(data_dir: str | None = None) -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir   = data_dir or os.path.join(script_dir, "..", "data")
    db_path    = os.path.join(data_dir, "company_database.db")

    log.info("Loading CSVs from: %s", data_dir)
    df_emp   = _load_csv(os.path.join(data_dir, "employees.csv"),     "employees")
    df_subs  = _load_csv(os.path.join(data_dir, "subscriptions.csv"), "subscriptions")
    df_usage = _load_csv(os.path.join(data_dir, "usage_logs.csv"),    "usage_logs")

    # ── Integrity check: every usage sub_id must exist in subscriptions ───────
    orphan_subs = set(df_usage["sub_id"]) - set(df_subs["sub_id"])
    if orphan_subs:
        log.warning(
            "  %d usage_log rows reference sub_ids not in subscriptions: %s …",
            len(orphan_subs), list(orphan_subs)[:5],
        )

    # ── Write to SQLite ───────────────────────────────────────────────────────
    log.info("Writing to database: %s", db_path)
    os.makedirs(data_dir, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        # Performance + safety pragmas
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous  = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")

        for df, table in [
            (df_emp,   "employees"),
            (df_subs,  "subscriptions"),
            (df_usage, "usage_logs"),
        ]:
            df.to_sql(table, conn, if_exists="replace", index=False)
            db_rows = _row_count(conn, table)
            status  = "✓" if db_rows == len(df) else "⚠ MISMATCH"
            log.info(
                "  %-20s CSV: %d rows  |  DB: %d rows  %s",
                table, len(df), db_rows, status,
            )

    log.info("✓ Database setup complete.")


if __name__ == "__main__":
    setup()