-- Q8: Redress proxy — high uphold rate + high volume = highest redress risk
-- (Monetary redress not available at firm level in FCA data; this is a risk proxy)
SELECT
    firm_name,
    reporting_period,
    product_group,
    complaints_opened,
    ROUND(uphold_rate * 100, 2)          AS uphold_rate_pct,
    ROUND(complaints_opened * uphold_rate, 0)
                                         AS estimated_upheld_complaints,
    RANK() OVER (
        PARTITION BY reporting_period
        ORDER BY complaints_opened * uphold_rate DESC
    )                                    AS redress_risk_rank
FROM complaints
WHERE uphold_rate IS NOT NULL AND complaints_opened IS NOT NULL
  AND reporting_period = '2025H2'
ORDER BY estimated_upheld_complaints DESC NULLS LAST
LIMIT 50;
