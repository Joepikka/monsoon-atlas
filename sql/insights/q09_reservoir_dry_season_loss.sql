-- question: Which Kerala reservoirs lost the most storage through the 2023-24 dry season, from 1 December 2023 to 1 June 2024?
-- source: S32 KSEB daily water level reports (CC BY-SA 2.5 India, credit KSEB; a published copy of these results must carry the same licence)
-- unit: live storage as percent of live storage at full reservoir level (percentage points for the loss)
-- range: report dates 1 Dec 2023 to 1 Jun 2024 (about every 15 days)
-- denominator: 8 of 16 listed reservoirs have a complete valid reading on both 1 Dec 2023 and 1 Jun 2024; the rest are quarantined or missing and are not filled
-- caveat: Sampled about every 15 days, not daily; storage falls with both use and evaporation and rises with summer rain, so the loss is net; no rain or inflow is joined.
-- inputs: local
WITH p AS (
    SELECT reservoir_name, date_local, 100.0 * storage_mcm / capacity_mcm AS pct
    FROM s32_reservoir
    WHERE date_local BETWEEN DATE '2023-12-01' AND DATE '2024-06-01' AND level_m IS NOT NULL
), b AS (
    SELECT
        reservoir_name,
        max(pct) FILTER (WHERE date_local = DATE '2023-12-01') AS start_pct,
        max(pct) FILTER (WHERE date_local = DATE '2024-06-01') AS end_pct,
        min(pct) AS lowest_pct,
        arg_min(date_local, pct) AS lowest_date
    FROM p
    GROUP BY reservoir_name
)
SELECT
    reservoir_name,
    round(start_pct, 1) AS pct_1_dec,
    round(end_pct, 1) AS pct_1_jun,
    round(start_pct - end_pct, 1) AS loss_points,
    round(lowest_pct, 1) AS lowest_pct,
    lowest_date
FROM b
WHERE start_pct IS NOT NULL AND end_pct IS NOT NULL
ORDER BY loss_points DESC, reservoir_name;
