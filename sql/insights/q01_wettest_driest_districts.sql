-- question: Which Karnataka districts were the wettest and the driest in 2020-2024, by mean annual rain at the gauges?
-- source: S29 KSNDMC annual district totals republished by OpenCity (public domain), via reports/eda/02_ka_rain/district_year_comparison.csv
-- unit: millimetres per calendar year (mean of the available years)
-- range: 2020, 2021, 2022 and 2024 (no district rows for 2023; the 2025 file is refused by the adapter, D113)
-- denominator: 29 of 31 published districts, each with 4 of 4 years like for like; Ballari and Vijayanagara are left out because S29 moved Vijayanagara out of Ballari from 2021
-- caveat: Annual gauge totals only, so no season or wet-spell result; the mean of 4 years is not a climate normal; 5 wettest and 5 driest shown.
-- inputs: committed
WITH d AS (
    SELECT district, count(*) AS years, avg(gauge_mm) AS mean_mm
    FROM s29_gauge
    WHERE district NOT IN ('BALLARI', 'VIJAYANAGAR')
    GROUP BY district
    HAVING count(*) = 4
), r AS (
    SELECT *, rank() OVER (ORDER BY mean_mm DESC, district) AS rank_wettest, count(*) OVER () AS districts
    FROM d
)
SELECT rank_wettest, district, years, round(mean_mm, 0)::INTEGER AS mean_mm, districts
FROM r
WHERE rank_wettest <= 5 OR rank_wettest > districts - 5
ORDER BY rank_wettest;
