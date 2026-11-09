-- question: Which Karnataka districts have the most unstable annual rain, and how wet was the wettest year compared with the driest?
-- source: S29 KSNDMC annual district totals republished by OpenCity (public domain), via reports/eda/02_ka_rain/district_year_comparison.csv
-- unit: ratio of the wettest to the driest annual total (no unit), plus millimetres for the gap
-- range: 2020, 2021, 2022 and 2024 (4 annual totals per district)
-- denominator: 29 of 31 published districts with 4 like-for-like years (Ballari and Vijayanagara excluded, boundary change in 2021)
-- caveat: Only 4 years, so the ratio describes this window and not the long-run variability; 8 districts shown.
-- inputs: committed
SELECT
    district,
    arg_max(year, gauge_mm) AS wettest_year,
    arg_min(year, gauge_mm) AS driest_year,
    round(max(gauge_mm) - min(gauge_mm), 0)::INTEGER AS gap_mm,
    round(max(gauge_mm) / min(gauge_mm), 2) AS wet_to_dry_ratio
FROM s29_gauge
WHERE district NOT IN ('BALLARI', 'VIJAYANAGAR')
GROUP BY district
HAVING count(*) = 4
ORDER BY wet_to_dry_ratio DESC, district
LIMIT 8;
