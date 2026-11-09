-- question: Do the CMIP6 models agree on whether annual rain at Thiruvananthapuram and Kozhikode will rise or fall?
-- source: S06 Open-Meteo CMIP6 climate projections (open), via reports/eda/07_climate/s06_model_change.csv
-- unit: percent change in mean annual rain, future years against base years
-- range: base and future periods of 30 years each, as in the file
-- denominator: 7 climate models at each of 2 points, 14 model-point results
-- caveat: Climate projection, not a forecast; two points are not the state; the models are not independent; the spread, not the median, is the message.
-- inputs: committed
SELECT
    point,
    count(*) AS models,
    sum((change_pct > 0)::INTEGER) AS models_wetter,
    sum((change_pct < 0)::INTEGER) AS models_drier,
    round(median(change_pct), 1) AS median_change_pct,
    min(change_pct) AS lowest_change_pct,
    max(change_pct) AS highest_change_pct
FROM s06_model_change
GROUP BY point
ORDER BY point;
