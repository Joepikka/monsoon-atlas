"""T239: explicitly local, signed transport of immutable prepared snapshots."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import hmac
import json
import os
import re
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from atlas.config import load_state
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.prepared import MAX_BYTES
from atlas.ingest.schedule import run_bounded

ROOT = Path(__file__).resolve().parents[3]
INGEST_PATH = "/internal/ingest"
MAX_REPLY = 4096
DEADLINE_S = 15
DIGEST = re.compile(r"[0-9a-f]{64}")


HOSTED = re.compile(r"https://[a-z0-9-]+\.[a-z0-9-]+\.workers\.dev")


def signing_key(origin: str) -> str:
    """The key, for a loopback test Worker or the one configured hosted Worker (D182).

    A hosted origin must equal ATLAS_HOT_ORIGIN exactly and be an https workers.dev origin with no
    path, so a command-line or upstream value cannot redirect signed uploads elsewhere."""
    match = re.fullmatch(r"http://127\.0\.0\.1:([0-9]{1,5})", origin)
    local = match is not None and 1 <= int(match[1]) <= 65535
    hosted = HOSTED.fullmatch(origin) is not None and origin == os.environ.get("ATLAS_HOT_ORIGIN")
    if not (local or hosted):
        raise ValueError("A loopback origin or the configured hosted Worker origin is required")
    key = os.environ.get("ATLAS_INGEST_HMAC_KEY", "")
    if len(key) < 32:
        raise ValueError("Local signing key is unavailable")
    return key


def post_local_signed(
    origin: str,
    path: str,
    body: bytes,
    content_type: str,
    *,
    key: str,
    transport: httpx.BaseTransport | None,
) -> tuple[int, bytes]:
    """Post once to an origin already checked by signing_key."""
    timestamp = str(int(time.time()))
    message = f"{timestamp}\nPOST\n{path}\n{hashlib.sha256(body).hexdigest()}"
    signature = hmac.new(key.encode("utf-8"), message.encode(), hashlib.sha256).hexdigest()
    with httpx.Client(
        transport=transport,
        trust_env=False,
        follow_redirects=False,
        timeout=httpx.Timeout(5.0, connect=2.0),
        headers={"Accept-Encoding": "identity", "User-Agent": "monsoon-atlas-feeds/1"},
    ) as client:
        with client.stream(
            "POST",
            origin + path,
            content=body,
            headers={
                "Content-Type": content_type,
                "X-Atlas-Timestamp": timestamp,
                "X-Atlas-Signature": signature,
            },
        ) as response:
            if response.status_code not in {200, 201}:
                return response.status_code, b""
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise IngestError("Invalid acknowledgement encoding")
            reply = bytearray()
            for chunk in response.iter_bytes(chunk_size=MAX_REPLY + 1):
                reply.extend(chunk)
                if len(reply) > MAX_REPLY:
                    raise IngestError("Acknowledgement exceeds the byte bound")
            return response.status_code, bytes(reply)


def cutoff(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() != timedelta(0) or parsed > datetime.now(UTC):
        raise ValueError("Invalid prepared cutoff")
    return parsed


def prepared_payload(root: Path, source_id: str) -> tuple[dict, bytes]:
    if source_id not in {"S01", "S09"}:
        raise ValueError("Unsupported local source")
    config = load_state(ROOT / "configs/states/ka.yaml").source(source_id)
    if not config.enabled:
        raise SourceUnavailable("Source is disabled")
    root = Path(root).resolve()
    output = root / ("weather/prepared" if source_id == "S01" else "prepared")
    # Resolve only after checking the selected tree: a symlink cannot redirect a
    # source's prepared directory outside the explicitly supplied feed root.
    output = output.resolve()
    if not output.is_relative_to(root):
        raise IngestError("Prepared path is outside the feed root")
    head = output / "prepared.json"
    if not head.resolve().is_relative_to(output):
        raise IngestError("Prepared pointer is outside the selected output")
    with head.open("rb") as stream:
        encoded = stream.read(MAX_REPLY + 1)
    if len(encoded) > MAX_REPLY:
        raise IngestError("Prepared pointer exceeds its byte bound")
    pointer = json.loads(encoded)
    if (
        type(pointer["schema_version"]) is not int
        or pointer["schema_version"] != 1
        or pointer["status"] != "prepared_only"
        or pointer["state"] != "ka"
        or pointer["source_id"] != source_id
    ):
        raise IngestError("Invalid prepared pointer")
    cutoff(pointer["as_of"])
    for field, name, suffix in (
        ("sha256", "payload", ".json"),
        ("inputs_sha256", "inputs", ".inputs.json"),
    ):
        digest = pointer[field]
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise IngestError("Invalid prepared digest")
        if pointer[name] != digest + suffix:
            raise IngestError("Invalid prepared filename")
        if not (output / pointer[name]).resolve().is_relative_to(output):
            raise IngestError("Prepared file is outside the selected output")
    # Manifests can outgrow the transport payload; hash them with bounded memory.
    with (output / pointer["inputs"]).open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != pointer["inputs_sha256"]:
        raise IngestError("Prepared input manifest failed verification")
    with (output / pointer["payload"]).open("rb") as stream:
        payload = stream.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES or hashlib.sha256(payload).hexdigest() != pointer["sha256"]:
        raise IngestError("Prepared payload failed verification")
    envelope = json.loads(payload)
    snapshot = envelope["snapshot"]
    if (
        envelope["source_id"] != source_id
        or snapshot["state"] != "ka"
        or snapshot["as_of"] != pointer["as_of"]
        or snapshot["data_revision"] != pointer["inputs_sha256"]
    ):
        raise IngestError("Prepared payload disagrees with its pointer")
    return pointer, payload


def upload_local(
    root: Path,
    *,
    source_id: str,
    origin: str,
    transport: httpx.BaseTransport | None = None,
) -> dict:
    """Send once, with no preparation mutation, retry, redirect or environment proxy."""
    try:
        key = signing_key(origin)
        pointer, payload = prepared_payload(root, source_id)
        compressed = gzip.compress(payload, mtime=0)
        if len(compressed) > MAX_BYTES:
            raise IngestError("Compressed prepared payload exceeds the byte bound")
        http_status, reply = post_local_signed(
            origin, INGEST_PATH, compressed, "application/gzip", key=key, transport=transport
        )
        if http_status not in {200, 201}:
            return {"status": "failed", "stage": "upload", "http_status": http_status}
        value = json.loads(reply)
        status = "stored" if http_status == 201 else "unchanged"
        if (
            value["status"] != status
            or not isinstance(value["snapshot_id"], str)
            or not DIGEST.fullmatch(value["snapshot_id"])
            or (status == "stored" and value["as_of"] != pointer["as_of"])
        ):
            raise IngestError("Invalid Worker acknowledgement")
        return {
            "status": status,
            "source_id": source_id,
            "snapshot_id": value["snapshot_id"],
            "prepared_sha256": pointer["sha256"],
        }
    except (
        IngestError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        httpx.HTTPError,
    ) as error:
        # Neither upstream bodies nor exception messages are trusted output.
        return {"status": "failed", "stage": "upload", "error_type": type(error).__name__}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / ".cache/feeds")
    parser.add_argument("--source", required=True, choices=["S01", "S09"])
    parser.add_argument("--origin", required=True)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        signing_key(args.origin)  # Fail before spawning or connecting.
    except ValueError:
        result = {"status": "failed", "stage": "upload", "error_type": "ValueError"}
    else:
        if args.child:
            result = upload_local(args.root, source_id=args.source, origin=args.origin)
        else:
            result = run_bounded(
                [
                    sys.executable,
                    "-m",
                    "atlas.ingest.upload",
                    "--child",
                    "--root",
                    str(args.root.resolve()),
                    "--source",
                    args.source,
                    "--origin",
                    args.origin,
                ],
                timeout=DEADLINE_S,
            )
    print(json.dumps(result))
    if not args.child and result["status"] not in {"stored", "unchanged"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
