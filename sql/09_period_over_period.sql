-- Q9: Period-over-period complaint volume change by firm
WITH pivoted AS (
    SELECT
        firm_name,
        SUM(CASE WHEN reporting_period='2024H1' THEN complaints_opened END) AS vol_2024H1,
        SUM(CASE WHEN reporting_period='2024H2' THEN complaints_opened END) AS vol_2024H2,
        SUM(CASE WHEN reporting_period='2025H1' THEN complaints_opened END) AS vol_2025H1,
        SUM(CASE WHEN reporting_period='2025H2' THEN complaints_opened END) AS vol_2025H2
    FROM complaints
    GROUP BY firm_name
)
SELECT
    firm_name,
    vol_2024H1, vol_2024H2, vol_2025H1, vol_2025H2,
    ROUND((vol_2025H2 - vol_2025H1) * 100.0 / NULLIF(vol_2025H1, 0), 2)
        AS pct_change_2025H2_vs_2025H1,
    ROUND((vol_2025H2 - vol_2024H2) * 100.0 / NULLIF(vol_2024H2, 0), 2)
        AS pct_change_yoy
FROM pivoted
WHERE vol_2025H2 IS NOT NULL
ORDER BY ABS(pct_change_2025H2_vs_2025H1) DESC NULLS LAST;
