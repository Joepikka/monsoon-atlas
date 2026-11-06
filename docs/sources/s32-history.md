# S32 daily gap census (T227)

**Status: complete availability census, 6 November 2026.** All **700** requested
dates returned correctly dated, validated header-only reports: **700 empty,
0 populated, 0 failed, 0 unattempted**. No dam observations were synthesized.

Evidence: [`s32_history_manifest.json`](../../tests/fixtures/s32_history_manifest.json).
All cited local report bytes and the robots artifact passed SHA256 recomputation.
The census reused 47 previously captured reports and fetched 653 additional
reports. The 700 cited report bodies total 91.63 MiB. Current robots.txt permitted
the path. Every date in the range was accounted for, rather than inferred from
the earlier twice-monthly sample.

This proves that these public KSEB report requests supplied no dam rows for the
checked dates. It does not prove that KSEB holds no underlying observations, and
it never represents an empty report as zero water level or zero storage. M07
requires another verified historical source (S34 OCR is next), plus a known
vertical datum and its other data/evaluation gates.

## Protocol

The requested range is 15 August 2024 through 15 July 2026, inclusive: 700 dates.
`scripts/s32_history.py` uses the verified KSEB GET date form, shared Fetcher and
the T114 parser. Current robots.txt is checked before requests. Every live HTTP
attempt, including redirects and retries, starts at least three seconds after
the previous one. Hash-checked existing report captures may be reused.

Run from the repository with its Python 3.12 interpreter, with TEMP and TMP set
to `D:\monsoon-atlas\.cache\tmp`:

```powershell
.\.venv\Scripts\python scripts/s32_history.py
```

The default checkpoint is `data/manifests/S32/history.json` (local, ignored).
Each date is checkpointed atomically. Re-running rebuilds the census from the
immutable raw ledger and fetches uncaptured dates. Raw report paths in the public
audit manifest are relative to `data/raw`; the legacy ledger can retain relative
or absolute paths. Every cited artifact keeps its original SHA256 and fetch time.

Limits per run: 1,000 HTTP attempts, 1 MiB per response, 256 MiB fetched artifacts,
and a 20 GiB free-space preflight. Three consecutive failures stop new requests.
The remaining dates are marked unattempted with the stopping cause. No TLS,
authentication or robots restriction is bypassed.

## Meaning of outcomes

| Outcome | Meaning |
|---|---|
| `empty` | Correctly dated, complete report with the verified headers and zero dam rows |
| `data` | Report contains dam rows; valid, quarantined and incomplete counts are separate |
| `failed` | Fetch, date/layout, hash or parsing failure; it is not evidence of an empty day |
| `not_attempted` | Requests stopped; the recorded cause explains why this date remains unknown |

`complete` is true only when all 700 dates are classified as validated reports.
An audit with failures can explain its limitations but cannot establish a complete
availability census. No daily observations are interpolated or invented.

The test fixture `tests/fixtures/s32_history_manifest.json` contains only
provenance and counts from this run. Production code never reads test data.
The raw HTML stays in `data/raw/S32` under the existing KSEB attribution/share-alike
policy. T114's quarantine rules and M07's known-datum requirement remain in force.

Acceptance command:

```powershell
.\.venv\Scripts\python -m pytest tests/sources/test_s32_history.py -q
```

Result: **7 passed in 1.08s**. These include real-date accounting, local hash
recomputation, resume without re-fetching, explicit failure/unattempted states,
request pacing and legacy relative-path handling. Independent code review found
no actionable defect. Final full-suite results are recorded in HANDOFF.
