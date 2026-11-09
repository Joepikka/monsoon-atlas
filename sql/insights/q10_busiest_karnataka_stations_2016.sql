-- question: Which Karnataka railway stations were called at by the most scheduled trains in the 2016 timetable?
-- source: S21 Datameet railway schedules (CC0), pinned commit of 8 Aug 2016
-- unit: number of distinct trains with a scheduled stop at the station
-- range: the timetable as of 8 Aug 2016 (historical, not today's service)
-- denominator: 9697 scheduled stops at 300 Karnataka stations by 422 trains
-- caveat: Historical 2016 data; a scheduled call is not ridership; station codes are shown because the adapter keeps no names; 10 stations shown.
-- inputs: local
SELECT
    station_id AS station_code,
    count(DISTINCT train_id) AS trains,
    round(100.0 * count(DISTINCT train_id) / (SELECT count(DISTINCT train_id) FROM s21_stops), 1) AS share_of_trains_pct,
    (SELECT count(DISTINCT station_id) FROM s21_stops) AS stations
FROM s21_stops
GROUP BY station_id
ORDER BY trains DESC, station_code
LIMIT 10;
