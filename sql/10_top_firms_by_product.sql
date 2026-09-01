-- Q10: Top 10 firms by complaint volume for each product group (latest period)
SELECT *
FROM (
    SELECT
        product_group,
        firm_name,
        complaints_opened,
        RANK() OVER (PARTITION BY product_group ORDER BY complaints_opened DESC)
            AS product_rank
    FROM complaints
    WHERE reporting_period = '2025H2'
      AND complaints_opened IS NOT NULL
)
WHERE product_rank <= 10
ORDER BY product_group, product_rank;
