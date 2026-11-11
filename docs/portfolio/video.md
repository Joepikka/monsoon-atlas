# 3-minute demo: script and shot list

**Status: not recorded: owner step.** This page is a script and a shot list only. No video, screenshot
or recording exists, and no demo URL exists because nothing is deployed ([README](../../README.md)).
Record it on a local machine after the owner has checked each shot below.

Setup: start the local server with `powershell -NoProfile -File scripts/web.ps1 run dev` and open the
pages by query, for example `?page=accuracy`. The four dashboard pages read the committed
`web/src/dashboards.json`, so they need no snapshot. The home map and Ask read a local snapshot and
corpus; this task did not run the server, so the "partly" rows must be checked before recording.

"Shown today" is one of: yes (the page exists and is mounted), partly (the page exists but depends on
local data or shows only a fallback), no (not mounted, hidden or blocked, so it cannot be shown).

## Shot list

| Time | Plan beat | Shown today | What to show | Narration (true statements only) |
|---|---|---|---|---|
| 00:00-00:25 | Open Karnataka and point to source freshness | partly | Home map for Karnataka; then `?page=quality`, the source health table | "This project records what each public source supports. With no released snapshot the map says so. This table shows each source's state and what is blocked." |
| 00:25-00:55 | Place facts, forecast interval and source | no | Not shown: place facts need an approved snapshot, and the M05 forecast intervals are hidden (D42, T262). Show the M05 row on `?page=accuracy` instead | "I am not showing forecast intervals. They did not meet their coverage gate, so they are hidden. This is the drought model's accuracy row." |
| 00:55-01:25 | Model accuracy: baseline, window, 95% CI; a model that stays research-only | yes | `?page=accuracy`: the drought model against persistence on the locked 2020 to 2024 window with the 95% CI and the hindcast label; the anomaly rule as research-only; the blocked models as unavailable | "One model has a measured result, and it is a hindcast. The anomaly rule is research-only because no flag has been adjudicated. The rest are blocked, and none of them has a number." |
| 01:25-01:55 | Kerala 2018 replay and what it is not | no | Not shown: the replay component is built but not mounted (D127). Show `?page=analysis` instead | "The 2018 replay is built but not mounted, so I am not showing it. These are the analysis reports, with the restricted sources marked." |
| 01:55-02:20 | Delhi live or stale state, or the truthful fallback | partly | The state selector, where Kerala and Delhi read "not released"; then `?page=compare` for the source and model counts per state | "Kerala and Delhi are not released. No Delhi source is enabled and no Delhi model has a result. This page compares the catalogues, and says when a metric comparison is not valid." |
| 02:20-02:45 | Ask: a question, a citation, a fallback | partly | `?page=ask` with the research-only note. Ask one answerable project question and open a citation. For the fallback, ask for a number whose data is blocked and show the insufficient-evidence reply | "Ask is research-only. It returns cited excerpts and no language model is connected. Its scores did not reproduce between runs, so I do not quote them as a result." |
| 02:45-03:00 | Pipeline, tests, cost; one measured result, one limit, one next step | yes | A terminal running the Reproduce commands in the README, then the `scripts/audit_dependencies.py --policy` result | "Cost is Rs 0. One measured result: the drought model's MAE of 0.732 against 0.808 for persistence on a locked 2020 to 2024 hindcast. One limit: its intervals are hidden. Next: the owner adjudicates the anomaly flags." |

## Not available and why

- Forecast intervals: hidden for M05 because coverage is below the gate (D42, T262).
- As-known replay and the Kerala 2018 replay: built, not mounted (D127, D162); no snapshot is approved.
- Quota fallback for Ask: Workers AI generation and live usage counters wait for owner step H05, so only the
  insufficient-evidence fallback can be shown.
- Place facts, current state and live markers: need an approved public snapshot (H11).
- Delhi live or stale state: no Delhi source is enabled.

## Before recording

1. Open each page listed as "yes" or "partly" and confirm it shows what the table says; change the row if it does not.
2. Do not add narration that claims a hidden, blocked or unmounted item is shown.
3. If the demo is later published, add its URL here and to the README only after it exists.
