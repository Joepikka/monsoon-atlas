-- question: Which Karnataka districts hold the most rain-gauge stations, and what share of the state network is that?
-- source: S29 KSNDMC station totals republished by OpenCity (public domain), via reports/eda/02_ka_rain/station_coverage_2023.csv
-- unit: number of stations; share of all stations in percent
-- range: calendar year 2023 (the only station file)
-- denominator: 5266 stations in 30 districts, all with a 2023 total
-- caveat: Station counts, not density (no district areas are used); a station with a total is not proof it works all year; 8 districts shown.
-- inputs: committed
SELECT
    district,
    stations,
    with_value,
    round(100.0 * stations / sum(stations) OVER (), 1) AS share_of_state_pct,
    sum(stations) OVER () AS state_stations
FROM s29_stations_2023
ORDER BY stations DESC, district
LIMIT 8;
