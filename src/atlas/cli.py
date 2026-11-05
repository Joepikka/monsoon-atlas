"""Command-line skeleton (plan section 4 "CLI"). Every command exists with its real options.

No empty successful commands: a command that is not implemented yet exits with code 2 and says
which task implements it.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

app = typer.Typer(
    help="Monsoon Atlas pipeline. All errors exit nonzero.",
    no_args_is_help=True,
    add_completion=False,
)

NOT_IMPLEMENTED = 2


def _not_implemented(command: str, task: str) -> None:
    typer.echo(f"atlas {command}: not implemented yet (planned in {task}).", err=True)
    raise typer.Exit(code=NOT_IMPLEMENTED)


@app.command()
def ingest(
    source: str = typer.Option(..., help="Source ID, e.g. S01"),
    state: str = typer.Option(..., help="State ID: ka, kl or dl"),
    as_of: str = typer.Option(..., "--as-of", help="ISO 8601 UTC timestamp"),
) -> None:
    """Fetch and store raw artifacts for one source."""
    _not_implemented("ingest", "T004 and the source adapter tasks")


@app.command()
def validate(manifest: Path = typer.Option(..., help="Path to a dataset manifest")) -> None:
    """Validate a dataset manifest and its files."""
    _not_implemented("validate", "T005/T006")


@app.command()
def features(
    model: str = typer.Option(..., help="Model ID, e.g. M06"),
    as_of: str = typer.Option(..., "--as-of", help="Issue time, ISO 8601 UTC"),
) -> None:
    """Build point-in-time features for a model."""
    _not_implemented("features", "T033")


@app.command()
def train(
    model: str = typer.Option(..., help="Model ID"),
    split: Path = typer.Option(..., help="Path to a frozen split manifest"),
) -> None:
    """Fit baseline and candidate on train/tune periods only."""
    _not_implemented("train", "T034")


@app.command()
def evaluate(run: str = typer.Option(..., help="Run ID")) -> None:
    """Score a run against its baseline with paired bootstrap CIs."""
    _not_implemented("evaluate", "T034")


@app.command()
def publish(manifest: Path = typer.Option(..., help="Path to a dataset manifest")) -> None:
    """Publish artifacts, manifest last."""
    _not_implemented("publish", "T045")


@app.command()
def replay(
    place: str = typer.Option(..., help="Place ID"),
    as_of: str = typer.Option(..., "--as-of", help="ISO 8601 UTC timestamp"),
) -> None:
    """Show what was known about a place at a past time."""
    _not_implemented("replay", "T045")


@app.command()
def audit(scope: str = typer.Option("all", help="Audit scope")) -> None:
    """Audit sources, licences and data quality."""
    _not_implemented("audit", "T006/T007")


QUOTA_EXCEEDED = 3


@app.command()
def quota(
    check: bool = typer.Option(False, "--check", help="Exit 3 if any budget is exceeded"),
    data_root: Path = typer.Option(Path("data"), help="Data root holding clean/ and manifests/"),
    budgets: Path = typer.Option(Path("configs/budgets.yaml"), help="Budgets file"),
    day: str = typer.Option("", help="UTC day YYYY-MM-DD (default: today)"),
) -> None:
    """Report storage status and today's free-tier usage against budgets.yaml."""
    from datetime import UTC, date, datetime

    from atlas.config import load_budgets
    from atlas.data.budget import QuotaLedger, StorageQuota
    from atlas.data.budget import check as check_budgets

    b = load_budgets(budgets)
    storage = StorageQuota.from_budget([data_root / "clean", data_root / "manifests"], b.storage)
    ledger = QuotaLedger(data_root / "quota" / "ledger.jsonl")
    when = date.fromisoformat(day) if day else datetime.now(UTC).date()
    report = check_budgets(b, ledger, storage, when)
    typer.echo(json.dumps(report, indent=2))
    over = [s for s in report["services"] if s["over"]]
    if report["storage_status"] == "warn":
        typer.echo("warning: storage above warn threshold; reduce capture cadence", err=True)
    if check and (over or report["storage_status"] == "archive_only"):
        raise typer.Exit(code=QUOTA_EXCEEDED)
