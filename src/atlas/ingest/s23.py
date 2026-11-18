"""S23 data.gov.in variety-wise mandi prices (T270). Field map: configs/sources/s23.yaml.

Scope is State=Karnataka, Commodity=Onion only: units are per commodity and only Onion has a
verified unit (Rs./Quintal, D201, T269); any other commodity is refused until owner step H16.
Offset paging duplicates and drops rows (D212), so the backfill sends ONE request per
filters[Arrival_Date] day, at least 2 s apart, and checks that each day's rows equal the API
`total`. A mismatch is recorded in the checkpoint, never filled in. The key goes only into the
request (Fetcher secret_params); stored URLs, the ledger and the checkpoint carry public
parameters only.

    python -m atlas.ingest.s23 backfill [--start 2001-01-10] [--end YYYY-MM-DD] [--max-days N]
    python -m atlas.ingest.s23 build    # data/clean/S23/onion.parquet + manifest.json

The checkpoint (data/raw/S23/checkpoint.jsonl) gets one line per completed day, so a stopped
backfill resumes where it stopped and a re-run downloads nothing. Days on or after the
resource's last update date are not checkpointed: the history lags about one day (e24), so those
answers may still grow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pyarrow as pa
import pyarrow.parquet as pq

from atlas import jsonl
from atlas.config import SourceConfig, load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import CircuitOpen, FetchError, IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore

SOURCE_ID = "S23"
RESOURCE = "35985678-0d79-46b4-9ed6-6f13308a1d24"
URL = f"https://api.data.gov.in/resource/{RESOURCE}"
HOSTS = {"api.data.gov.in"}
MAPPING_VERSION = "s23-v1"
LICENCE_ID = "godl-india-data-gov-in"
SECRET_ENV = "DATA_GOV_IN_API_KEY"
STATE_NAME = "Karnataka"
# commodity -> verified price unit. Units are per commodity (D201); others wait for H16.
UNITS = {"Onion": "Rs./Quintal"}
FIRST_DAY = date(2001, 1, 10)  # earliest Karnataka onion row (T269 e09 to e19)
LIMIT = 1000  # far above any one day's rows; a larger total is recorded as a mismatch
PAUSE_S = 2.0
ROOT = Path(__file__).resolve().parents[3]
RAW_ROOT = ROOT / "data/raw"
CHECKPOINT = RAW_ROOT / SOURCE_ID / "checkpoint.jsonl"
CLEAN = ROOT / "data/clean" / SOURCE_ID
MEASURES = pa.schema(
    [
        pa.field("market_id", pa.string(), False),
        pa.field("district_name", pa.string(), False),
        pa.field("market_name", pa.string(), False),
        pa.field("commodity", pa.string(), False),
        pa.field("commodity_code", pa.string(), True),
        pa.field("variety", pa.string(), True),
        pa.field("grade", pa.string(), True),
        pa.field("date_local", pa.date32(), False),
        pa.field("min_inr_quintal", pa.float64(), True),
        pa.field("max_inr_quintal", pa.float64(), True),
        pa.field("modal_inr_quintal", pa.float64(), True),
        pa.field("price_unit", pa.string(), False),
    ]
)
FIELD_MAP = {
    "State + District + Market": "market_id",
    "District": "district_name",
    "Market": "market_name",
    "Commodity": "commodity",
    "Commodity_Code": "commodity_code",
    "Variety": "variety",
    "Grade": "grade",
    "Arrival_Date": "date_local",
    "Min_Price": "min_inr_quintal",
    "Max_Price": "max_inr_quintal",
    "Modal_Price": "modal_inr_quintal",
}


def _check_commodity(commodity: str) -> None:
    if commodity not in UNITS:
        raise SourceUnavailable(
            f"{SOURCE_ID}: {commodity!r} has no verified price unit; only "
            f"{sorted(UNITS)} until owner step H16 records it"
        )


def day_params(day: date, commodity: str = "Onion") -> dict[str, str]:
    _check_commodity(commodity)
    return {
        "filters[State]": STATE_NAME,
        "filters[Commodity]": commodity,
        "filters[Arrival_Date]": day.strftime("%d/%m/%Y"),
        "format": "json",
        "limit": str(LIMIT),
        "offset": "0",
    }


def _query(raw: RawArtifact) -> dict[str, str]:
    q = {k: v[0] for k, v in parse_qs(urlsplit(raw.source_url).query).items()}
    if not raw.source_url.startswith(f"{URL}?") or "filters[Arrival_Date]" not in q:
        raise SourceUnavailable(
            f"{SOURCE_ID}: only per-day queries of resource {RESOURCE} are verified (T269, D212)"
        )
    return q


def read_day(raw: RawArtifact) -> tuple[date, dict]:
    """(requested day, body) after the resource, status and scope checks."""
    q = _query(raw)
    _check_commodity(q.get("filters[Commodity]", ""))
    if q.get("filters[State]") != STATE_NAME:
        raise SourceUnavailable(f"{SOURCE_ID}: only State={STATE_NAME} is in scope")
    day = datetime.strptime(q["filters[Arrival_Date]"], "%d/%m/%Y").date()
    body = json.loads(raw.path.read_bytes())
    if body.get("index_name") != RESOURCE or body.get("status") != "ok":
        raise IngestError(f"{SOURCE_ID}: unexpected response for {raw.source_url}")
    return day, body


def day_check(raw: RawArtifact) -> dict:
    """Row count against the API total for one day; `ok` is False on any mismatch."""
    day, body = read_day(raw)
    total, rows = int(body["total"]), len(body["records"])
    return {
        "date": day.isoformat(),
        "total": total,
        "rows": rows,
        "ok": total == rows == int(body["count"]),
        "updated_date": body.get("updated_date"),
    }


def _price(value) -> tuple[float | None, str | None]:
    """Value as given (no cleaning; zero stays zero). Missing is never 0."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, "not_reported"
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None, "quality_rejected"
    return (x, None) if math.isfinite(x) else (None, "quality_rejected")


def _text(value) -> str | None:
    s = " ".join(str(value).split()) if value is not None else ""
    return s or None


class S23:
    def __init__(
        self,
        days: Sequence[date] = (),
        *,
        commodity: str = "Onion",
        state: str = "ka",
        fetcher: Fetcher | None = None,
        pause_s: float = PAUSE_S,
        sleep: Callable[[float], None] = time.sleep,
    ):
        _check_commodity(commodity)
        if state != "ka":
            raise SourceUnavailable(f"{SOURCE_ID}: only Karnataka is verified (T269)")
        self.days, self.commodity, self.state = list(days), commodity, state
        self.fetcher, self.pause_s, self.sleep = fetcher, pause_s, sleep

    def fetch_day(self, ctx: FetchContext, day: date) -> RawArtifact:
        return self.fetcher.fetch_bytes(
            ctx,
            URL,
            mapping_version=MAPPING_VERSION,
            params=day_params(day, self.commodity),
            secret_params={"api-key": SECRET_ENV},
        )

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """One request per day, at least `pause_s` apart (D212)."""
        out = []
        for i, day in enumerate(self.days):
            if i:
                self.sleep(self.pause_s)
            out.append(self.fetch_day(ctx, day))
        return out

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        day, body = read_day(raw)
        records = body["records"]
        cols: dict[str, list] = {f.name: [] for f in MEASURES}
        ids, flags, reasons = [], [], []
        seen: Counter[str] = Counter()
        for rec in records:
            if rec.get("State") != STATE_NAME or rec.get("Commodity") != self.commodity:
                raise IngestError(f"{SOURCE_ID} {day}: row outside the requested scope")
            got = datetime.strptime(str(rec.get("Arrival_Date")), "%d/%m/%Y").date()
            if got != day:
                raise IngestError(f"{SOURCE_ID} {day}: row dated {got}")
            district, market = _text(rec.get("District")), _text(rec.get("Market"))
            if not district or not market:
                raise IngestError(f"{SOURCE_ID} {day}: row without district or market")
            # Identical rows (same values) get an occurrence number, so none is merged away.
            key = json.dumps(rec, sort_keys=True, default=str)
            seen[key] += 1
            ids.append(hashlib.sha256(f"{key}#{seen[key]}".encode()).hexdigest())
            cols["market_id"].append(f"{STATE_NAME}/{district}/{market}".lower())
            cols["district_name"].append(district)
            cols["market_name"].append(market)
            cols["commodity"].append(self.commodity)
            cols["commodity_code"].append(_text(rec.get("Commodity_Code")))
            cols["variety"].append(_text(rec.get("Variety")))
            cols["grade"].append(_text(rec.get("Grade")))
            cols["date_local"].append(day)
            cols["min_inr_quintal"].append(_price(rec.get("Min_Price"))[0])
            cols["max_inr_quintal"].append(_price(rec.get("Max_Price"))[0])
            modal, reason = _price(rec.get("Modal_Price"))
            cols["modal_inr_quintal"].append(modal)
            cols["price_unit"].append(UNITS[self.commodity])
            reasons.append(reason)
            flags.append(
                ["missing"] if reason == "not_reported" else ["out_of_range"] if reason else []
            )
        n = len(records)
        ts = pa.timestamp("us", tz="UTC")
        common = {
            "source_id": pa.array([SOURCE_ID] * n, pa.string()),
            "state": pa.array([self.state] * n, pa.string()),
            "record_id": pa.array(ids, pa.string()),
            "snapshot_id": pa.array([f"{SOURCE_ID}-{day}-{raw.sha256[:16]}"] * n, pa.string()),
            "observed_at": pa.nulls(n, ts),
            "valid_at": pa.nulls(n, ts),
            "issued_at": pa.nulls(n, ts),
            "available_at": pa.array([raw.fetched_at] * n, ts),
            "fetched_at": pa.array([raw.fetched_at] * n, ts),
            "published_at": pa.nulls(n, ts),
            "source_url": pa.array([raw.source_url] * n, pa.string()),
            "raw_sha256": pa.array([raw.sha256] * n, pa.string()),
            "schema_version": pa.array([1] * n, pa.int64()),
            "mapping_version": pa.array([MAPPING_VERSION] * n, pa.string()),
            "provenance": pa.array(["official"] * n, pa.string()),
            "quality_flags": pa.array(flags, pa.list_(pa.string())),
            "licence_id": pa.array([LICENCE_ID] * n, pa.string()),
            "redistribution_allowed": pa.array([True] * n),  # GODL-India with attribution (e06)
            "place_id": pa.nulls(n, pa.string()),
            "boundary_version": pa.nulls(n, pa.string()),
            "missing_reason": pa.array(reasons, pa.string()),
        }
        measures = {f.name: pa.array(cols[f.name], f.type) for f in MEASURES}
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | measures, schema=schema)
        validate_table(table, measures=["modal_inr_quintal"])
        return with_mapping(table, FIELD_MAP, MAPPING_VERSION)


# --- backfill and build -------------------------------------------------------------------------


def _api_key() -> str:
    """The key from the environment or .env; never printed, logged or stored."""
    if key := os.environ.get(SECRET_ENV):
        return key
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == SECRET_ENV and value.strip():
                return value.strip().strip("\"'")
    raise SourceUnavailable(f"{SOURCE_ID}: {SECRET_ENV} is not set")


def done_days(checkpoint: Path = CHECKPOINT) -> dict[str, dict]:
    """Latest checkpoint line per day."""
    return {e["date"]: e for e in jsonl.read(checkpoint)}


def _artifact(entry: dict, raw_root: Path) -> RawArtifact:
    return RawArtifact(
        sha256=entry["sha256"],
        path=raw_root / entry["raw_path"],
        fetched_at=datetime.fromisoformat(entry["fetched_at"]),
        media_type="application/json",
        response_status=200,
        source_url=entry["source_url"],
        schema_mapping_version=MAPPING_VERSION,
    )


def backfill(
    days: Iterable[date],
    *,
    fetcher: Fetcher,
    secrets: dict[str, str],
    raw_root: Path = RAW_ROOT,
    checkpoint: Path = CHECKPOINT,
    max_days: int | None = None,
    pause_s: float = PAUSE_S,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = lambda s: None,
) -> dict:
    """Fetch every day not yet in the checkpoint; one line per completed day. Resumable."""
    done = done_days(checkpoint)
    todo = [d for d in days if d.isoformat() not in done][:max_days]
    now = datetime.now(UTC)
    ctx = FetchContext(
        source_id=SOURCE_ID,
        state="ka",
        run_id=f"s23-backfill-{now:%Y%m%dT%H%M%SZ}",
        requested_at=now,
        budget=Budget(max_requests=4 * len(todo) + 4, max_bytes=8 * 1024**2),
        raw_root=raw_root,
        secrets=secrets,
    )
    adapter = S23(fetcher=fetcher)
    out = {"todo": len(todo), "done": 0, "rows": 0, "mismatch": 0, "failed": 0, "provisional": 0}
    for i, day in enumerate(todo):
        if i:
            sleep(pause_s)
        try:
            raw = adapter.fetch_day(ctx, day)
            check = day_check(raw)
        except CircuitOpen:
            out["stopped"] = "circuit open after 3 consecutive failures"
            break
        except (FetchError, IngestError) as exc:
            out["failed"] += 1
            log(f"{day} failed: {exc}")
            continue
        # The history lags about a day: a day the resource has not finished is not final.
        updated = (check["updated_date"] or "")[:10]
        if not updated or day.isoformat() >= updated:
            out["provisional"] += 1
            continue
        jsonl.append(
            checkpoint,
            check
            | {
                "sha256": raw.sha256,
                "raw_path": Path(raw.path).relative_to(raw_root).as_posix(),
                "fetched_at": raw.fetched_at.isoformat(),
                "source_url": raw.source_url,
            },
        )
        out["done"] += 1
        out["rows"] += check["rows"]
        out["mismatch"] += not check["ok"]
        if not check["ok"]:
            log(f"{day} mismatch: total {check['total']}, rows {check['rows']}")
        if out["done"] % 100 == 0:
            log(f"{day}: {out['done']}/{len(todo)} days, {out['rows']} rows")
    return out


def build(
    config: SourceConfig,
    *,
    raw_root: Path = RAW_ROOT,
    checkpoint: Path = CHECKPOINT,
    clean: Path = CLEAN,
) -> dict:
    """Parse every checkpointed day into one Parquet file plus a manifest (no cleaning rules)."""
    entries = sorted(done_days(checkpoint).values(), key=lambda e: e["date"])
    adapter = S23()
    tables = [
        adapter.parse(_artifact(e, raw_root), config)
        for e in entries
        if e["rows"]  # an empty day has no row to parse
    ]
    table = pa.concat_tables(tables) if tables else None
    if table is None:
        raise IngestError(f"{SOURCE_ID}: no checkpointed rows to build")
    clean.mkdir(parents=True, exist_ok=True)
    out = clean / "onion.parquet"
    pq.write_table(table, out)
    years: Counter[str] = Counter()
    for e in entries:
        years[e["date"][:4]] += e["rows"]
    manifest = {
        "source_id": SOURCE_ID,
        "resource": RESOURCE,
        "scope": {"state": STATE_NAME, "commodity": "Onion", "price_unit": UNITS["Onion"]},
        "mapping_version": MAPPING_VERSION,
        "file": out.name,
        "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "rows": table.num_rows,
        "days_checked": len(entries),
        "days_with_rows": sum(1 for e in entries if e["rows"]),
        "first_day": entries[0]["date"],
        "last_day": entries[-1]["date"],
        "rows_per_year": dict(sorted(years.items())),
        "mismatched_days": [
            {k: e[k] for k in ("date", "total", "rows")} for e in entries if not e["ok"]
        ],
        "cleaning": "none beyond schema validity; T271 cleans and quarantines",
    }
    (clean / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - network and local data
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("backfill")
    b.add_argument("--start", type=date.fromisoformat, default=FIRST_DAY)
    b.add_argument("--end", type=date.fromisoformat, default=date.today() - timedelta(days=1))
    b.add_argument("--max-days", type=int, default=None)
    sub.add_parser("build")
    args = parser.parse_args(argv)
    if args.command == "build":
        config = load_state(ROOT / "configs/states/ka.yaml").source(SOURCE_ID)
        print(json.dumps(build(config), indent=2))
        return 0
    days = [args.start + timedelta(n) for n in range((args.end - args.start).days + 1)]
    fetcher = Fetcher(RawStore(RAW_ROOT), HOSTS)
    result = backfill(
        days,
        fetcher=fetcher,
        secrets={SECRET_ENV: _api_key()},
        max_days=args.max_days,
        log=lambda s: print(s, flush=True),
    )
    print(json.dumps(result), flush=True)
    return 1 if result.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())
