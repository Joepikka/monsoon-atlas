-- question: Which police units registered the most cyber-crime cases in 2024, and what share of the state total is that?
-- source: S44 Karnataka State Police annual tables republished by OpenCity (public domain)
-- unit: registered cases (count); share in percent of the state total row
-- range: calendar year 2024
-- denominator: 22402 registered cyber-crime cases in the state total row, over 31 district units, 6 commissionerates and 3 units without an area
-- caveat: Registered cases are not crime incidence (reporting differs by unit, and a commissionerate city is a separate unit from its district); no population is published, so there is no rate; 8 units shown.
-- inputs: local
WITH c AS (
    SELECT district_id AS unit, unit_kind, count AS cases
    FROM s44_crime
    WHERE year = 2024 AND offence_category = 'CYBER CRIME' AND unit_kind <> 'state_total'
), t AS (
    SELECT count AS total FROM s44_crime
    WHERE year = 2024 AND offence_category = 'CYBER CRIME' AND unit_kind = 'state_total'
)
SELECT unit, unit_kind, cases, round(100.0 * cases / total, 1) AS share_of_state_pct, total AS state_total
FROM c, t
ORDER BY cases DESC, unit
LIMIT 8;
