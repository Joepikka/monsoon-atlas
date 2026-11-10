# Delhi collection benchmark and readiness gate (T152)

**Gate result: failed (not run).** There is no approved S38 access and no real position sample
(owner step H04, D135), so nothing was benchmarked. **Continuous capture: unavailable. Live mode:
disabled.** No GPS history exists and none will be manufactured. Registration:
[delhi.md](delhi.md).

## Benchmark with a real sample

| Quantity | Plan section 5 cap | Measured |
|---|---|---|
| Worker CPU per request | 10 ms | not measured |
| Worker memory | 128 MB | not measured |
| Compressed snapshot blob | 1 MB | not measured |
| Compressed daily history | 40 MB | not measured |
| Hot, archive, replay counts | equal | not run |

## Quota simulation (arithmetic from `configs/budgets.yaml`; no feed involved)

| Quantity | Simulated | Configured cap |
|---|---|---|
| Polls per day (16 h at one per 60 s) | 960 | 960 |
| D1 writes per day (one snapshot per tick) | 960 | 10000 |
| Worker requests per day (one per tick) | 960 | 20000 |
| Hot history, 7 days at 40 MB per day | 280 MB | 400 MB |

This shows the plan fits the caps if a feed ever exists. It says nothing about the real size of a
snapshot, which stays unmeasured.

## Chronology

| Item | Status |
|---|---|
| First collection day | not frozen |
| Train, tune, calibration and test periods | not frozen |
| Study manifest | not written |

Nothing earlier than the day collection really starts may be used; the whole chronology shifts
with the approval date (D137).

## Fallback

Owner-run capture windows with narrower claims, available only after H04. Until then the Delhi
bus view shows the static schedule only (and the static times are a rough estimate, S38 e05).

## Retry condition

The owner completes H04 (key, Terms, static GTFS) and T148 re-runs with a real sample. Then run
the benchmark on that sample, record the measurements here, write the study manifest and only
then reopen T151's live poller.
