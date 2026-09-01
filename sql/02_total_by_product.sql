-- Q2: Total complaints by product group (all periods)
SELECT
    product_group,
    SUM(complaints_opened)  AS total_complaints,
    ROUND(SUM(complaints_opened) * 100.0 /
          SUM(SUM(complaints_opened)) OVER (), 2) AS market_share_pct
FROM complaints
GROUP BY product_group
ORDER BY total_complaints DESC;
