-- Q7: Uphold rate ranking by firm (weighted by complaints_opened, latest period)
SELECT
    firm_name,
    reporting_period,
    SUM(complaints_opened)                                          AS complaints_opened,
    ROUND(SUM(uphold_rate * complaints_opened) /
          NULLIF(SUM(complaints_opened), 0) * 100, 2)             AS uphold_rate_weighted_pct,
    RANK() OVER (
        ORDER BY SUM(uphold_rate * complaints_opened) /
                 NULLIF(SUM(complaints_opened), 0) DESC
    )                                                              AS uphold_rank
FROM complaints
WHERE uphold_rate IS NOT NULL AND complaints_opened IS NOT NULL
  AND reporting_period = '2025H2'
GROUP BY firm_name, reporting_period
ORDER BY uphold_rate_weighted_pct DESC;
