-- Q6: Closure performance ranking by firm (latest period, avg % closed within 3 days)
SELECT
    firm_name,
    reporting_period,
    ROUND(AVG(pct_closed_3days) * 100, 2)       AS avg_pct_closed_3days,
    ROUND(AVG(pct_closed_3to8weeks) * 100, 2)   AS avg_pct_closed_3to8weeks,
    ROUND(AVG(pct_closed_3days + pct_closed_3to8weeks) * 100, 2)
                                                 AS avg_pct_within_8weeks,
    SUM(complaints_opened)                       AS complaints_opened,
    RANK() OVER (ORDER BY AVG(pct_closed_3days) DESC)
                                                 AS fast_closure_rank
FROM complaints
WHERE pct_closed_3days IS NOT NULL
  AND reporting_period = '2025H2'
GROUP BY firm_name, reporting_period
ORDER BY avg_pct_closed_3days DESC;
