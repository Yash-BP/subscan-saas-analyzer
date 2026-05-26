"""
run_pipeline.py
───────────────
Single entry point for the full SubScan pipeline.

Usage:
    python scripts/run_pipeline.py              # full run
    python scripts/run_pipeline.py --skip-gen   # skip data generation (use existing CSVs)
    python scripts/run_pipeline.py --only-analyze  # only run analytics (DB already built)

Why this file exists:
    The original project required running three scripts manually in the right order.
    This orchestrator runs them in sequence, handles errors gracefully, and prints
    a final audit summary — making the project one-command reproducible.
"""

import argparse
import logging
import os
import sys
import time

# Add scripts dir to path so sibling imports work whether called from root or scripts/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_billing_data import generate, DataConfig
from setup_db import setup
from analyze_waste import analyze

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("subscan.pipeline")

# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SubScan — SaaS Subscription Waste Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_pipeline.py                 # full run from scratch
  python scripts/run_pipeline.py --skip-gen      # re-run DB + analytics on existing CSVs
  python scripts/run_pipeline.py --only-analyze  # re-run analytics only
        """,
    )
    parser.add_argument(
        "--skip-gen", action="store_true",
        help="Skip data generation (use existing CSVs in data/)",
    )
    parser.add_argument(
        "--only-analyze", action="store_true",
        help="Only run the analytics engine (database must already exist)",
    )
    return parser.parse_args()


# ── Step runner ───────────────────────────────────────────────────────────────

def _run_step(name: str, fn, *args, **kwargs):
    log.info("")
    log.info("═" * 55)
    log.info("  STEP: %s", name)
    log.info("═" * 55)
    start = time.perf_counter()
    try:
        result = fn(*args, **kwargs)
        elapsed = time.perf_counter() - start
        log.info("  ✓ %s completed in %.2fs", name, elapsed)
        return result
    except Exception as exc:
        log.error("  ✗ %s FAILED: %s", name, exc)
        raise


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    log.info("")
    log.info("╔══════════════════════════════════════════════╗")
    log.info("║         SubScan Pipeline  v2.0               ║")
    log.info("╚══════════════════════════════════════════════╝")

    pipeline_start = time.perf_counter()

    if not args.skip_gen and not args.only_analyze:
        _run_step("Generate billing data", generate, DataConfig())

    if not args.only_analyze:
        _run_step("Build SQLite database", setup)

    df_waste = _run_step("Run analytics engine", analyze)

    total_elapsed = time.perf_counter() - pipeline_start
    log.info("")
    log.info("╔══════════════════════════════════════════════╗")
    log.info("║         Pipeline complete  (%.2fs)          ║", total_elapsed)
    log.info("║                                              ║")
    log.info("║  Wasted licenses : %-4d                      ║", len(df_waste))
    log.info("║  Monthly waste   : $%-8s                 ║", f"{int(df_waste['monthly_cost'].sum()):,}")
    log.info("║  Annual waste    : $%-8s                 ║", f"{int(df_waste['annual_waste'].sum()):,}")
    log.info("╚══════════════════════════════════════════════╝")
    log.info("")


if __name__ == "__main__":
    main()