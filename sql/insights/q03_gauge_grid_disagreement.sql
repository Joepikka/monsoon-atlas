-- question: In which Karnataka districts does the IMD grid most often read more than 10 percent wetter or drier than the district gauges?
-- source: S29 KSNDMC gauge totals (public domain) compared with the S08 IMD 0.25 degree grid (restricted, local only); only the per-district mean grid-to-gauge ratio over several years is used, from reports/eda/02_ka_rain/district_ratio_summary.csv
-- unit: ratio of the grid annual total to the gauge annual total (index; 1.00 means equal)
-- range: 2020, 2021, 2022 and 2024
-- denominator: 117 compared district-years in 30 districts; 6 district-years (Ballari 2021 and later, Vijayanagara) are excluded as not like for like
-- caveat: The grid is itself interpolated from gauges, so this is not an independent test; the S08 licence forbids showing area rainfall in millimetres, so only the ratio is shown and H11 item 3 decides on any wider use; Ballari has one compared year, so no mean is published; 8 districts shown.
-- inputs: committed
SELECT
    district,
    years_compared,
    grid_wetter_years,
    grid_drier_years,
    round(mean_ratio, 2) AS mean_ratio
FROM s08_ratio_by_district
WHERE grid_wetter_years + grid_drier_years > 0
ORDER BY grid_wetter_years + grid_drier_years DESC, abs(mean_ratio - 1) DESC, district
LIMIT 8;
