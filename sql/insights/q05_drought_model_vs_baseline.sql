-- question: Does the M05 drought outlook beat the strongest simple baseline, and is the gain clearly above zero?
-- source: M05 registry records models/registry/M05/v1.evaluation.json and v1.monitor-2025.json (inputs derived from S08, accuracy figures only)
-- unit: mean absolute error of the SPI-3 forecast (SPI units, lower is better); improvement is baseline minus ridge
-- range: locked test 2020-2024 (60 months) and the 2025 hindcast monitor (12 months)
-- denominator: 1800 district-months (30 districts x 60 months) in the test, 360 (30 x 12) in 2025
-- caveat: Hindcast, because IMD publishes the grid yearly (D39); the baseline is persistence; the 95 percent bounds come from a paired block bootstrap over months; 2025 IMD data is provisional.
-- inputs: committed
SELECT
    '2020-2024 locked test' AS period,
    rows AS district_months,
    round(mae.persistence, 3) AS mae_baseline,
    round(mae.ridge, 3) AS mae_ridge,
    round(improvement.mean, 3) AS improvement,
    round(improvement.lower95, 3) AS lower95,
    round(improvement.upper95, 3) AS upper95,
    improvement.lower95 > 0 AS clearly_above_zero
FROM m05_eval
UNION ALL
SELECT
    '2025 hindcast monitor',
    rows,
    round(mae.persistence, 3),
    round(mae.ridge, 3),
    round(improvement.mean, 3),
    round(improvement.lower95, 3),
    round(improvement.upper95, 3),
    improvement.lower95 > 0
FROM m05_2025
ORDER BY 1;
