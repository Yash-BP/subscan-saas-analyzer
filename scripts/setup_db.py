"""
setup_db.py  (Phase 1 Upgrade)
──────────────────────────────
Same as before, with one addition:
  • Loads the new historical_usage_logs CSV into SQLite
  • Applies vw_cohort_retention.sql to create the Power BI cohort view

Everything else (schema validation, row-count reconciliation,
foreign-key check, WAL pragmas) is untouched.
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
    # New table added in Phase 1
    "historical_usage_logs": {"sub_id", "emp_id", "tool_name", "billing_month", "login_count"},
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_columns(df: pd.DataFrame, table: str) -> None:
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
    log.info("  Loaded %-25s — %d rows", table, len(df))
    return df


def _apply_sql_file(conn: sqlite3.Connection, sql_path: str) -> None:
    """Read a .sql file and execute every statement inside it."""
    if not os.path.exists(sql_path):
        log.warning("SQL file not found, skipping: %s", sql_path)
        return
    with open(sql_path, "r") as f:
        sql = f.read()
    # SQLite executescript handles multiple statements separated by semicolons
    conn.executescript(sql)
    log.info("  Applied SQL file: %s", os.path.basename(sql_path))


# ── Main ──────────────────────────────────────────────────────────────────────

def setup(data_dir: str | None = None) -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir   = data_dir or os.path.join(script_dir, "..", "data")
    db_path    = os.path.join(data_dir, "company_database.db")

    log.info("Loading CSVs from: %s", data_dir)

    # Original three tables
    df_emp   = _load_csv(os.path.join(data_dir, "employees.csv"),              "employees")
    df_subs  = _load_csv(os.path.join(data_dir, "subscriptions.csv"),          "subscriptions")
    df_usage = _load_csv(os.path.join(data_dir, "usage_logs.csv"),             "usage_logs")

    # New Phase 1 table
    df_hist  = _load_csv(os.path.join(data_dir, "historical_usage_logs.csv"),  "historical_usage_logs")

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
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous  = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")

        all_tables = [
            (df_emp,   "employees"),
            (df_subs,  "subscriptions"),
            (df_usage, "usage_logs"),
            (df_hist,  "historical_usage_logs"),   # ← new
        ]

        for df, table in all_tables:
            df.to_sql(table, conn, if_exists="replace", index=False)
            db_rows = _row_count(conn, table)
            status  = "✓" if db_rows == len(df) else "⚠ MISMATCH"
            log.info(
                "  %-28s CSV: %d rows  |  DB: %d rows  %s",
                table, len(df), db_rows, status,
            )

        # ── Apply both SQL view files ─────────────────────────────────────────
        _apply_sql_file(conn, os.path.join(script_dir, "setup_powerbi_views.sql"))
        _apply_sql_file(conn, os.path.join(script_dir, "vw_cohort_retention.sql"))

    log.info("✓ Database setup complete — all tables and views loaded.")


if __name__ == "__main__":
    setup()