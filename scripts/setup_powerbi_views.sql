-- ====================================================================
-- SAAS WASTE ANALYTICS: POWER BI VIEWS
-- Target DB: company_database.db (SQLite)
-- ====================================================================

-- 1. Clean up existing views if re-running
DROP VIEW IF EXISTS vw_executive_waste_summary;
DROP VIEW IF EXISTS vw_wasted_licenses_detail;

-- 2. Create the Detail View (Bulletproofed for SQLite string matching)
CREATE VIEW vw_wasted_licenses_detail AS
SELECT 
    e.emp_id,
    e.name AS employee_name,
    e.department,
    s.tool_name,
    s.monthly_cost,
    u.last_login_date,
    CAST(u.logins_last_30_days AS INTEGER) AS logins_last_30_days
FROM 
    employees e
JOIN 
    subscriptions s ON e.emp_id = s.emp_id
JOIN 
    usage_logs u ON s.sub_id = u.sub_id
WHERE 
    CAST(u.logins_last_30_days AS INTEGER) <= 0 
    AND LOWER(TRIM(e.status)) = 'active' 
    AND LOWER(TRIM(s.license_status)) = 'active';

-- 3. Create the Executive Summary View (Pre-calculated financials)
CREATE VIEW vw_executive_waste_summary AS
SELECT 
    tool_name,
    COUNT(emp_id) AS unused_license_count,
    SUM(monthly_cost) AS total_monthly_waste,
    (SUM(monthly_cost) * 12) AS total_annualized_waste
FROM 
    vw_wasted_licenses_detail
GROUP BY 
    tool_name
ORDER BY 
    total_monthly_waste DESC;