-- question: Which Kerala reservoirs gained the most storage between 1 August and 1 November 2026?
-- source: S32 KSEB daily water level reports (CC BY-SA 2.5 India, credit KSEB; a published copy of these results must carry the same licence)
-- unit: live storage as percent of live storage at full reservoir level (percentage points for the gain)
-- range: report dates 1 Aug, 15 Aug, 1 Sep, 15 Sep, 1 Oct, 15 Oct and 1 Nov 2026
-- denominator: 8 of 16 listed reservoirs have a complete valid reading (level, storage, capacity) on both 1 Aug and 1 Nov 2026; the other 8 are quarantined or missing on a date and are not filled
-- caveat: Only about 15-day samples were captured, so peaks between them are missed; the gain mixes rain and operating choices (releases, generation); rain and inflow are not in this table, so it does not say how fast a dam filled after rain.
-- inputs: local
WITH p AS (
    SELECT reservoir_name, date_local, 100.0 * storage_mcm / capacity_mcm AS pct
    FROM s32_reservoir
    WHERE date_local BETWEEN DATE '2026-08-01' AND DATE '2026-11-01' AND level_m IS NOT NULL
), b AS (
    SELECT
        reservoir_name,
        max(pct) FILTER (WHERE date_local = DATE '2026-08-01') AS start_pct,
        max(pct) FILTER (WHERE date_local = DATE '2026-11-01') AS end_pct,
        max(pct) AS peak_pct,
        arg_max(date_local, pct) AS peak_date
    FROM p
    GROUP BY reservoir_name
)
SELECT
    reservoir_name,
    round(start_pct, 1) AS pct_1_aug,
    round(end_pct, 1) AS pct_1_nov,
    round(end_pct - start_pct, 1) AS gain_points,
    round(peak_pct, 1) AS peak_pct,
    peak_date
FROM b
WHERE start_pct IS NOT NULL AND end_pct IS NOT NULL
ORDER BY gain_points DESC, reservoir_name;
