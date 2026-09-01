-- Q1: Total complaints by firm (all periods)
SELECT
    firm_name,
    SUM(complaints_opened)                          AS total_complaints_all_periods,
    SUM(CASE WHEN reporting_period='2025H2' THEN complaints_opened ELSE 0 END) AS complaints_2025H2,
    SUM(CASE WHEN reporting_period='2025H1' THEN complaints_opened ELSE 0 END) AS complaints_2025H1,
    SUM(CASE WHEN reporting_period='2024H2' THEN complaints_opened ELSE 0 END) AS complaints_2024H2,
    SUM(CASE WHEN reporting_period='2024H1' THEN complaints_opened ELSE 0 END) AS complaints_2024H1
FROM complaints
GROUP BY firm_name
ORDER BY total_complaints_all_periods DESC;
