-- ============================================================
-- vw_cohort_retention.sql
-- SubScan — Cohort Retention Analysis
-- Target DB: company_database.db (SQLite)
-- ============================================================
--
-- WHAT THIS FILE DOES (plain English):
--   It reads historical_usage_logs (12 months of data per employee)
--   and answers the question:
--   "Of all employees who started using a tool in a given month,
--    how many are STILL using it 1 month later? 2 months later? etc."
--
-- The result is a table that Power BI turns into a retention heatmap.
--
-- WHY CTEs?
--   Instead of writing one giant messy query, CTEs let us break the
--   problem into small, named steps that are easy to read and debug.
-- ============================================================

DROP VIEW IF EXISTS vw_cohort_retention;

CREATE VIEW vw_cohort_retention AS

-- ── Step 1: Cohort Setup ──────────────────────────────────────────────────
-- Find the FIRST month each employee used each tool.
-- That first month is their "cohort month" — the month they were born into.
WITH Cohort_Setup AS (
    SELECT
        emp_id,
        tool_name,
        MIN(billing_month) AS cohort_month   -- earliest billing month = when they started
    FROM historical_usage_logs
    GROUP BY emp_id, tool_name
),

-- ── Step 2: Activity Log ──────────────────────────────────────────────────
-- Join the cohort month back onto every usage row.
-- Then calculate "months_active" = how many months since they started.
-- Example: cohort_month = 2024-01, billing_month = 2024-03 → months_active = 2
Activity_Log AS (
    SELECT
        h.emp_id,
        h.tool_name,
        c.cohort_month,
        h.billing_month,
        -- Date math: (year difference × 12) + month difference = months elapsed
        (
            (CAST(strftime('%Y', h.billing_month) AS INTEGER) -
             CAST(strftime('%Y', c.cohort_month)  AS INTEGER)) * 12
        )
        +
        (
            CAST(strftime('%m', h.billing_month) AS INTEGER) -
            CAST(strftime('%m', c.cohort_month)  AS INTEGER)
        ) AS months_active,
        h.login_count
    FROM historical_usage_logs h
    -- Connect each usage row to its cohort start date
    JOIN Cohort_Setup c
        ON  h.emp_id    = c.emp_id
        AND h.tool_name = c.tool_name
),

-- ── Step 3: Retention Calculation ────────────────────────────────────────
-- For each cohort + tool + month bucket, count:
--   total_users  = everyone who was supposed to be active that month
--   active_users = only those with at least 1 login that month
Retention_Calculation AS (
    SELECT
        cohort_month,
        tool_name,
        months_active,
        -- COUNT(CASE WHEN ...) = count only rows where the condition is true
        COUNT(CASE WHEN login_count > 0 THEN emp_id END) AS active_users,
        COUNT(emp_id)                                     AS total_users
    FROM Activity_Log
    GROUP BY cohort_month, tool_name, months_active
)

-- ── Final Output: Add Retention Percentage ────────────────────────────────
-- Divide active_users by total_users and multiply by 100.
-- CAST(...AS FLOAT) prevents integer division (e.g. 3/10 = 0 without it).
-- ROUND(..., 2) keeps it to 2 decimal places.
SELECT
    cohort_month,
    tool_name,
    months_active,
    active_users,
    total_users,
    ROUND(
        CAST(active_users AS FLOAT) / total_users * 100,
        2
    ) AS retention_percentage
FROM Retention_Calculation
-- Optional: only show months 0–11 to keep Power BI chart clean
WHERE months_active BETWEEN 0 AND 11
ORDER BY cohort_month, tool_name, months_active;