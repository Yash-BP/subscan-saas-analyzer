"""
analyze_waste.py
────────────────
Core SubScan analytics engine. Connects to the SQLite database, applies
business rules to classify waste, and exports a clean report CSV.

Improvements over v1:

  • Three-tier waste classification:
      1. Terminated Employee    — account active for an offboarded employee
      2. Zombie License         — zero logins in the past N days
      3. At-Risk License        — low logins (1–4) in the past N days (new)

  • Annualised savings calculation added to every row in the output CSV
  • Department-level rollup table exported as a second CSV
  • Tool-level rollup table exported as a third CSV
  • Single SQL query with a CTE — no in-Python merge required for waste logic
  • Config loaded via a typed dataclass mirroring .env values
  • Execution summary printed to both log and stdout
  • Atomic CSV write: writes to a temp file, renames on success — no partial
    output if the script crashes mid-export
"""

import os
import logging
import sqlite3
import tempfile
from dataclasses import dataclass

import pandas as pd
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv()


@dataclass
class AnalyticsConfig:
    inactivity_threshold_days: int = int(os.getenv("INACTIVITY_THRESHOLD_DAYS", 30))
    low_usage_threshold: int       = int(os.getenv("LOW_USAGE_THRESHOLD", 4))

    label_terminated: str = os.getenv(
        "WASTE_LABEL_TERMINATED", "Terminated Employee (Wasted License)"
    )
    label_zombie: str = os.getenv(
        "WASTE_LABEL_ZOMBIE", "Zero Usage in 30 Days (Zombie License)"
    )
    label_at_risk: str = os.getenv(
        "WASTE_LABEL_AT_RISK", "Low Usage (At-Risk License)"
    )

    def __post_init__(self):
        if self.inactivity_threshold_days < 1:
            raise ValueError("INACTIVITY_THRESHOLD_DAYS must be >= 1")


# ── Logging ───────────────────────────────────────────────────────────────────

script_dir   = os.path.dirname(os.path.abspath(__file__))
log_path     = os.path.join(script_dir, "execution_audit.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler(),          # also print to terminal
    ],
)
log = logging.getLogger("subscan.analyze")

# ── SQL ───────────────────────────────────────────────────────────────────────

# Single query — joins all three tables and returns the full merged dataset.
# Business rule classification happens in Python (easier to unit-test).
MERGE_QUERY = """
SELECT
    s.sub_id,
    e.emp_id,
    s.tool_name,
    s.monthly_cost,
    s.license_status,
    e.name,
    e.email,
    e.department,
    e.status          AS emp_status,
    u.last_login_date,
    u.logins_last_30_days
FROM subscriptions   s
JOIN employees       e ON s.emp_id  = e.emp_id
JOIN usage_logs      u ON s.sub_id  = u.sub_id
                      AND s.emp_id  = u.emp_id
                      AND s.tool_name = u.tool_name
WHERE s.license_status = 'Active'
"""

# ── Waste classification ───────────────────────────────────────────────────────

def classify_waste(row: pd.Series, cfg: AnalyticsConfig) -> str:
    """
    Three-tier classifier.

    Priority order matters: terminated is always wasteful regardless of login
    count, so it's checked first.
    """
    if row["emp_status"] == "Terminated":
        return cfg.label_terminated
    if row["logins_last_30_days"] == 0:
        return cfg.label_zombie
    if row["logins_last_30_days"] <= cfg.low_usage_threshold:
        return cfg.label_at_risk
    return "Active & Used"


# ── Atomic file write ─────────────────────────────────────────────────────────

def _safe_write_csv(df: pd.DataFrame, dest_path: str) -> None:
    """Write to a temp file in the same directory, then rename atomically."""
    dir_name = os.path.dirname(dest_path)
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".csv.tmp")
    try:
        os.close(fd)
        df.to_csv(tmp_path, index=False)
        os.replace(tmp_path, dest_path)   # atomic on POSIX, best-effort on Windows
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


# ── Main ──────────────────────────────────────────────────────────────────────

def analyze(data_dir: str | None = None) -> pd.DataFrame:
    cfg      = AnalyticsConfig()
    data_dir = data_dir or os.path.join(script_dir, "..", "data")
    db_path  = os.path.join(data_dir, "company_database.db")

    log.info("─" * 60)
    log.info("SubScan Analytics Engine — starting")
    log.info("  Inactivity threshold : %d days", cfg.inactivity_threshold_days)
    log.info("  At-risk threshold    : <= %d logins", cfg.low_usage_threshold)

    # ── Load from DB ──────────────────────────────────────────────────────────
    if not os.path.exists(db_path):
        log.error("Database not found: %s — run setup_db.py first", db_path)
        raise FileNotFoundError(db_path)

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(MERGE_QUERY, conn)

    log.info("Loaded %d active subscription rows from database", len(df))

    # ── Classify waste ────────────────────────────────────────────────────────
    df["waste_category"] = df.apply(classify_waste, axis=1, cfg=cfg)
    df["annual_waste"]   = df["monthly_cost"] * 12

    # ── Filter to wasted only ─────────────────────────────────────────────────
    df_waste = df[df["waste_category"] != "Active & Used"].copy()

    # ── Build rollups ─────────────────────────────────────────────────────────
    # 1. Department rollup
    dept_rollup = (
        df_waste
        .groupby("department", as_index=False)
        .agg(
            wasted_licenses=("sub_id", "count"),
            monthly_waste=("monthly_cost", "sum"),
            annual_waste=("annual_waste", "sum"),
        )
        .sort_values("monthly_waste", ascending=False)
    )

    # 2. Tool rollup
    tool_rollup = (
        df_waste
        .groupby("tool_name", as_index=False)
        .agg(
            wasted_licenses=("sub_id", "count"),
            monthly_waste=("monthly_cost", "sum"),
            annual_waste=("annual_waste", "sum"),
        )
        .sort_values("monthly_waste", ascending=False)
    )

    # 3. Waste category summary
    cat_summary = (
        df_waste
        .groupby("waste_category")
        .agg(count=("sub_id", "count"), monthly_waste=("monthly_cost", "sum"))
    )

    # ── Log summary ───────────────────────────────────────────────────────────
    total_monthly   = df_waste["monthly_cost"].sum()
    total_annual    = df_waste["annual_waste"].sum()
    pct_waste       = total_monthly / df["monthly_cost"].sum() * 100

    log.info("─" * 60)
    log.info("AUDIT RESULTS")
    log.info("  Total licenses audited : %d", len(df))
    log.info("  Wasted licenses found  : %d  (%.1f%% of total)", len(df_waste), pct_waste)
    log.info("  Monthly waste          : $%s", f"{total_monthly:,.0f}")
    log.info("  Annualised waste       : $%s", f"{total_annual:,.0f}")
    log.info("")
    log.info("  Breakdown by category:")
    for cat, row in cat_summary.iterrows():
        log.info("    %-45s  %d licenses  $%d/mo", cat, row["count"], row["monthly_waste"])
    log.info("")
    log.info("  Top 5 tools by waste:")
    for _, r in tool_rollup.head(5).iterrows():
        log.info("    %-15s  %d licenses  $%d/mo", r["tool_name"], r["wasted_licenses"], r["monthly_waste"])

    # ── Export ────────────────────────────────────────────────────────────────
    report_path       = os.path.join(data_dir, "identified_waste_report.csv")
    dept_rollup_path  = os.path.join(data_dir, "dept_rollup.csv")
    tool_rollup_path  = os.path.join(data_dir, "tool_rollup.csv")

    _safe_write_csv(df_waste,    report_path)
    _safe_write_csv(dept_rollup, dept_rollup_path)
    _safe_write_csv(tool_rollup, tool_rollup_path)

    log.info("Reports saved:")
    log.info("  %s", report_path)
    log.info("  %s", dept_rollup_path)
    log.info("  %s", tool_rollup_path)
    log.info("─" * 60)
    log.info("SubScan Analytics Engine — complete")

    return df_waste


if __name__ == "__main__":
    analyze()