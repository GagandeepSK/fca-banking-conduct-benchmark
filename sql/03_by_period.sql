-- Q3: Complaints by reporting period (market totals)
SELECT
    reporting_period,
    SUM(complaints_opened)  AS total_complaints,
    SUM(complaints_closed)  AS total_closed,
    COUNT(DISTINCT firm_name) AS firms_reporting
FROM complaints
GROUP BY reporting_period
ORDER BY reporting_period;
