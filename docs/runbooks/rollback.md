# Rollback and correction runbook (T219)

Owner-run. Nothing here sends a message to anyone. `tests/test_monitor.py` runs every command
below on a temporary store, so this page cannot drift from the code.

## Principles

- A rollback moves one pointer (`manifests/latest.json`) to the prior release. It never edits or
  deletes a prediction file, the ledger, an old manifest or a data file.
- A wrong label is corrected by adding a new revision. The old ledger line and the old report stay.
- An alert is a line in an owner-run log or a row in a job summary. It is never a private message.

## 1. See what the monitor says

```powershell
.\.venv\Scripts\python -m atlas.monitoring          # committed-state checks, as a table
.\.venv\Scripts\python -m atlas quota --check       # storage (80% warn, 95% archive-only) and daily caps
```

The GitHub workflow `monitor` runs the first command on the committed state and writes the table to
its job summary. Dispatch it by hand (Actions, monitor, Run workflow). It has no schedule.

Alert thresholds: feed stale after two stated cadences without a success; PSI above 0.2 in two
consecutive windows; residual MAE above 1.2 times the frozen baseline MAE over the latest 14
labelled days; storage at 80% (warn) and 95% (archive-only), D24. A stale feed stops the models
that read it (`stopped_models`, from `configs/models/*.yaml`).

## 2. A release is corrupted: roll back

```python
from pathlib import Path
from atlas.data.manifest import ManifestStore
from atlas.monitoring import rollback_if_corrupt

store = ManifestStore(Path("data/manifests"), Path("data/clean"))
rollback_if_corrupt(store)  # None if the current release verifies; else the move it made
```

`rollback_if_corrupt` verifies the current release's files against its manifest. If they fail, it
checks the prior release, then points `latest.json` at it (`ManifestStore.rollback`, two releases
deep). If there is no prior release, or the prior one is also bad, it raises and moves nothing.
The corrupted release's manifest stays on disk. After a rollback, confirm with
`store.current().data_revision`, then fix forward by publishing a new release.

## 3. A label was wrong: re-score with a new revision

```python
from datetime import UTC, datetime
from pathlib import Path
from atlas.monitoring import append_correction, current_label, write_report_revision

ledger = Path("data/ledger/m05.jsonl")
append_correction(ledger, "p1", 0.7, "label source corrected", datetime.now(UTC))  # revision 1
write_report_revision(Path("reports/eval"), "m05-eval", {"mae": 0.3})  # m05-eval.r2.json
current_label(ledger, "p1")  # latest revision
```

The ledger keeps the prediction, the original label and every correction. `write_report_revision`
writes the next `name.rN.json` and never overwrites an earlier one.

## 4. Record it

Add a dated entry to `docs/decisions.md` with the release IDs, the cause and the evidence.
