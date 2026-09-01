-- Q4: Firm complaint-rate ranking (complaints per 1,000 relevant accounts)
-- Only for firms with denominator data; latest period
SELECT
    firm_name,
    reporting_period,
    product_group,
    SUM(complaints_opened)          AS complaints_opened,
    SUM(denominator)                AS total_denominator_k,
    ROUND(SUM(complaints_opened) / NULLIF(SUM(denominator), 0), 4)
                                    AS complaint_rate_per_1k,
    RANK() OVER (
        PARTITION BY reporting_period
        ORDER BY SUM(complaints_opened) / NULLIF(SUM(denominator), 0) DESC
    )                               AS rate_rank
FROM complaints
WHERE denominator IS NOT NULL AND denominator > 0
  AND reporting_period = '2025H2'
GROUP BY firm_name, reporting_period, product_group
ORDER BY complaint_rate_per_1k DESC NULLS LAST
LIMIT 50;
