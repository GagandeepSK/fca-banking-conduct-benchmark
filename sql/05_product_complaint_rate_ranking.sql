-- Q5: Product complaint-rate ranking (latest period, weighted by denominator)
SELECT
    product_group,
    reporting_period,
    SUM(complaints_opened)   AS total_complaints,
    SUM(denominator)         AS total_denominator_k,
    ROUND(SUM(complaints_opened) / NULLIF(SUM(denominator), 0), 4)
                             AS complaint_rate_per_1k,
    RANK() OVER (ORDER BY SUM(complaints_opened) / NULLIF(SUM(denominator), 0) DESC)
                             AS rate_rank
FROM complaints
WHERE denominator IS NOT NULL AND denominator > 0
  AND reporting_period = '2025H2'
GROUP BY product_group, reporting_period
ORDER BY complaint_rate_per_1k DESC NULLS LAST;
