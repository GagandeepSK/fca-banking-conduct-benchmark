-- Q12: Largest deteriorations in complaint volume (2025H2 vs 2025H1)
WITH changes AS (
    SELECT
        firm_name,
        SUM(CASE WHEN reporting_period='2025H1' THEN complaints_opened END) AS vol_prior,
        SUM(CASE WHEN reporting_period='2025H2' THEN complaints_opened END) AS vol_curr
    FROM complaints
    GROUP BY firm_name
)
SELECT
    firm_name,
    vol_prior,
    vol_curr,
    (vol_curr - vol_prior)  AS abs_change,
    ROUND((vol_curr - vol_prior) * 100.0 / NULLIF(vol_prior, 0), 2)
                            AS pct_change
FROM changes
WHERE vol_prior IS NOT NULL AND vol_curr IS NOT NULL
  AND vol_curr > vol_prior
ORDER BY abs_change DESC
LIMIT 20;
