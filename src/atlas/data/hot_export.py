"""T044: verified daily export of hot snapshots to an archive (D184).

Reads new rows from the Worker's signed, read-only `/internal/export` after the archive's cursor,
checks that every stored payload gunzips to bytes whose SHA-256 equals both the row ID and the
stored digest, writes one immutable Parquet file per source per run (named by its own SHA-256),
and commits the files with an updated manifest in one archive commit. It then downloads every new
file at that commit and checks its SHA-256 before reporting success. The archive is the owner's
private Hugging Face dataset (or a local directory for tests and offline runs).

Nothing is deleted from the Worker: purge needs a separate decision, because the D1 cap guard
counts the database file size, which does not shrink after deletes (D184). The manifest keeps a
capacity forecast so the cap is seen coming. Rows stay in the private archive; a public subset
needs the owner's release approval (H11).
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import hmac
import io
import json
import os
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pyarrow as pa
import pyarrow.parquet as pq

EXPORT_PATH = "/internal/export"
MAX_RESPONSE = 6 * 1024 * 1024
MAX_PAGES = 50
MANIFEST = "hot/manifest.json"
SOURCES = ("S01", "S09")
SCHEMA = pa.schema(
    [
        pa.field("snapshot_id", pa.string(), False),
        pa.field("source_id", pa.string(), False),
        pa.field("as_of", pa.timestamp("ms", tz="UTC"), False),
        pa.field("sha256", pa.string(), False),
        pa.field("canonical_json", pa.string(), False),
        pa.field("payload_gzip", pa.binary(), False),
    ]
)


class ArchiveError(Exception):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def signed_post(client: httpx.Client, origin: str, key: str, body: bytes) -> dict:
    """One signed POST with the Worker's upload message format; bounded response."""
    timestamp = str(int(time.time()))
    message = f"{timestamp}\nPOST\n{EXPORT_PATH}\n{sha256(body)}"
    signature = hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Atlas-Timestamp": timestamp,
        "X-Atlas-Signature": signature,
    }
    with client.stream("POST", origin + EXPORT_PATH, content=body, headers=headers) as r:
        if r.status_code != 200:
            raise ArchiveError(f"export failed with HTTP {r.status_code}")
        data = bytearray()
        for chunk in r.iter_bytes():
            data.extend(chunk)
            if len(data) > MAX_RESPONSE:
                raise ArchiveError("export page exceeds the byte bound")
    return json.loads(data)


def verify_row(row: dict) -> dict:
    """Exact stored bytes: gunzip, hash, identity; reject anything else."""
    if set(row) != {"id", "source_id", "as_of_ms", "sha256", "payload_gzip_base64"}:
        raise ArchiveError("unexpected export row fields")
    if row["source_id"] not in SOURCES or row["id"] != row["sha256"]:
        raise ArchiveError("unknown source or mismatched identity")
    payload = base64.b64decode(row["payload_gzip_base64"], validate=True)
    canonical = gzip.decompress(payload)
    if sha256(canonical) != row["sha256"]:
        raise ArchiveError(f"stored payload {row['id'][:12]} does not match its SHA-256")
    envelope = json.loads(canonical)
    if envelope.get("source_id") != row["source_id"]:
        raise ArchiveError("payload source does not match the row")
    return {
        "snapshot_id": row["id"],
        "source_id": row["source_id"],
        "as_of": datetime.fromtimestamp(row["as_of_ms"] / 1000, UTC),
        "sha256": row["sha256"],
        "canonical_json": canonical.decode("utf-8"),
        "payload_gzip": payload,
    }


def fetch_new(
    client: httpx.Client, origin: str, key: str, cursor: dict
) -> tuple[list[dict], dict, dict]:
    rows: list[dict] = []
    capacity: dict = {}
    for _ in range(MAX_PAGES):
        page = signed_post(client, origin, key, json.dumps(cursor, separators=(",", ":")).encode())
        rows.extend(verify_row(r) for r in page["rows"])
        capacity, cursor = page["capacity"], page["next"]
        if not page["more"]:
            return rows, cursor, capacity
    raise ArchiveError(f"more than {MAX_PAGES} export pages; run again to continue")


def parquet_bytes(rows: list[dict]) -> bytes:
    rows = sorted(rows, key=lambda r: (r["as_of"], r["snapshot_id"]))
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    out = io.BytesIO()
    pq.write_table(table, out, compression="zstd")
    return out.getvalue()


def forecast(history: list[dict]) -> dict:
    """Days to the 400 MB cap from the reserved-bytes growth across recorded runs."""
    if not history:
        return {"bytes_per_day": None, "days_to_cap": None}
    first, last = history[0], history[-1]
    days = (
        datetime.fromisoformat(last["at"]) - datetime.fromisoformat(first["at"])
    ).total_seconds() / 86400
    if days < 0.5 or last["allocated_bytes"] <= first["allocated_bytes"]:
        return {"bytes_per_day": None, "days_to_cap": None}
    rate = (last["allocated_bytes"] - first["allocated_bytes"]) / days
    left = last["cap_bytes"] - last["allocated_bytes"]
    return {"bytes_per_day": round(rate), "days_to_cap": round(left / rate, 1)}


def plan_commit(
    manifest: dict, rows: list[dict], cursor: dict, capacity: dict, now: datetime
) -> tuple[dict, dict[str, bytes]]:
    """New manifest and files {path: bytes}; one immutable file per source with new rows."""
    files: dict[str, bytes] = {}
    entries = list(manifest.get("files", []))
    for source in SOURCES:
        part = [r for r in rows if r["source_id"] == source]
        if not part:
            continue
        data = parquet_bytes(part)
        digest = sha256(data)
        path = f"hot/ka/{now:%Y-%m-%d}/{source}-{digest[:16]}.parquet"
        files[path] = data
        entries.append(
            {
                "path": path,
                "sha256": digest,
                "bytes": len(data),
                "rows": len(part),
                "source_id": source,
                "first_as_of": min(r["as_of"] for r in part).isoformat(),
                "last_as_of": max(r["as_of"] for r in part).isoformat(),
                "snapshot_ids": sorted(r["snapshot_id"] for r in part),
            }
        )
    history = list(manifest.get("capacity_history", []))[-29:]
    history.append(
        {"at": now.isoformat(), **{k: capacity[k] for k in ("allocated_bytes", "cap_bytes")}}
    )
    new = {
        "schema_version": 1,
        "state": "ka",
        "cursor": cursor,
        "files": entries,
        "capacity_history": history,
        "capacity_forecast": forecast(history),
        "licence": {  # configs/sources/s01.yaml, s09.yaml
            "S01": "CC BY 4.0, free API for non-commercial use; credit Open-Meteo and ECMWF",
            "S09": "public domain (Sachet CAP feed channel)",
        },
        "purge": "none: rows stay in the Worker until a purge decision (D184)",
    }
    return new, files


class LocalArchive:
    def __init__(self, root: Path):
        self.root = Path(root)

    def read(self, path: str) -> bytes | None:
        p = self.root / path
        return p.read_bytes() if p.exists() else None

    def commit(self, files: dict[str, bytes], message: str) -> str:
        for path, data in files.items():
            p = self.root / path
            if p.exists() and path != MANIFEST and p.read_bytes() != data:
                raise ArchiveError(f"immutable file {path} would change")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        return sha256(files[MANIFEST])

    def read_at(self, path: str, revision: str) -> bytes:
        return (self.root / path).read_bytes()


class HfArchive:  # pragma: no cover - needs the owner's token and network
    def __init__(self, repo: str, token: str):
        from huggingface_hub import HfApi

        self.repo, self.api = repo, HfApi(token=token)

    def read(self, path: str) -> bytes | None:
        from huggingface_hub.errors import EntryNotFoundError

        try:
            return self.read_at(path, "main")
        except EntryNotFoundError:
            return None

    def commit(self, files: dict[str, bytes], message: str) -> str:
        from huggingface_hub import CommitOperationAdd

        ops = [CommitOperationAdd(path_in_repo=p, path_or_fileobj=d) for p, d in files.items()]
        info = self.api.create_commit(self.repo, ops, commit_message=message, repo_type="dataset")
        return info.oid

    def read_at(self, path: str, revision: str) -> bytes:
        with tempfile.TemporaryDirectory(dir=os.environ.get("TEMP")) as tmp:
            got = self.api.hf_hub_download(
                self.repo, path, repo_type="dataset", revision=revision, local_dir=tmp
            )
            return Path(got).read_bytes()


def run(archive, client: httpx.Client, origin: str, key: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    raw = archive.read(MANIFEST)
    manifest = json.loads(raw) if raw else {"cursor": {"after_ms": -1, "after_id": ""}, "files": []}
    rows, cursor, capacity = fetch_new(client, origin, key, manifest["cursor"])
    new, files = plan_commit(manifest, rows, cursor, capacity, now)
    text = json.dumps(new, indent=1, sort_keys=True) + "\n"
    files[MANIFEST] = text.encode()
    revision = archive.commit(files, f"hot export {now:%Y-%m-%dT%H:%MZ}: {len(rows)} snapshots")
    for path, data in files.items():  # read back what this commit claims
        if sha256(archive.read_at(path, revision)) != sha256(data):
            raise ArchiveError(f"read-back of {path} does not match")
    return {
        "status": "archived",
        "snapshots": len(rows),
        "files": sorted(p for p in files if p != MANIFEST),
        "revision": revision,
        "capacity_forecast": new["capacity_forecast"],
    }


def main(argv: list[str] | None = None) -> int:
    from atlas.ingest.upload import signing_key

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--hf-repo")
    where.add_argument("--local-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        key = signing_key(args.origin)
        archive = (
            HfArchive(args.hf_repo, os.environ["HF_TOKEN"])
            if args.hf_repo
            else LocalArchive(args.local_dir)
        )
        with httpx.Client(
            trust_env=False,
            follow_redirects=False,
            timeout=httpx.Timeout(30.0, connect=5.0),
            headers={"User-Agent": "monsoon-atlas-archive/1", "Accept-Encoding": "identity"},
        ) as client:
            result = run(archive, client, args.origin, key)
    except Exception as error:  # noqa: BLE001 - one bounded report; logs are public (D184)
        # Only this module's own messages are printed: library errors can carry the repo name.
        detail = str(error)[:200] if isinstance(error, ArchiveError) else None
        result = {"status": "failed", "error_type": type(error).__name__, "detail": detail}
    print(json.dumps(result))
    return 0 if result["status"] == "archived" else 1


if __name__ == "__main__":
    sys.exit(main())
