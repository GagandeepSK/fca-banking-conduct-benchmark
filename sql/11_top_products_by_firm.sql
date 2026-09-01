-- Q11: Top products by firm (latest period, firms with >1000 complaints)
SELECT
    firm_name,
    product_group,
    complaints_opened,
    ROUND(complaints_opened * 100.0 /
          SUM(complaints_opened) OVER (PARTITION BY firm_name), 2)
        AS pct_of_firm_total
FROM complaints
WHERE reporting_period = '2025H2'
  AND firm_name IN (
      SELECT firm_name FROM complaints
      WHERE reporting_period = '2025H2'
      GROUP BY firm_name
      HAVING SUM(complaints_opened) > 1000
  )
ORDER BY firm_name, complaints_opened DESC;
