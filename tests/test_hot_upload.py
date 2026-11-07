"""T239: local transport of genuine source projections; mutations are failure controls."""

import gzip
import hashlib
import hmac
import importlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest.discovery import load_manifest
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s01_collect import collect_weather
from atlas.ingest.s01_prepare import prepare_weather
from atlas.ingest.s09 import BASE
from atlas.ingest.s09_prepare import prepare

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"
CUTOFF = datetime(2026, 11, 5, 14, tzinfo=UTC)
KEY = "test-only-local-signing-value-" * 2
WORKER_ID = "a" * 64  # Protocol acknowledgement control, not a source observation.


@pytest.fixture
def uploader(monkeypatch):
    monkeypatch.setenv("ATLAS_INGEST_HMAC_KEY", KEY)
    return importlib.import_module("atlas.ingest.upload")


def prepared(root, source="S09"):
    if source == "S01":

        def response(request):
            name = (
                "s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json"
                if request.url.path.endswith("meta.json")
                else "s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json"
            )
            return httpx.Response(200, content=(FIXTURES / name).read_bytes())

        collect_weather(
            root,
            clock=lambda: CUTOFF,
            sleep=lambda _: None,
            transport=httpx.MockTransport(response),
        )
        result = prepare_weather(root, as_of=CUTOFF)
    else:
        evidence = next(
            e
            for e in load_manifest(FIXTURES / "s09/manifest.json").evidence
            if e.url == f"{BASE}/FetchXMLFile?identifier=1793881986295019"
        )
        store = RawStore(root / "raw")
        path, digest = store.put(
            (FIXTURES / "s09_sachet_cap_1793881986295019.xml").read_bytes(),
            "S09",
            evidence.fetched_at,
            "xml",
        )
        assert digest == evidence.sha256
        raw = RawArtifact(
            sha256=digest,
            path=path,
            fetched_at=evidence.fetched_at,
            media_type=evidence.media_type,
            response_status=200,
            source_url=evidence.url,
            schema_mapping_version="s09-v1",
        )
        store.record(raw, {"status": 200})
        result = prepare(store.root, root / "prepared", as_of=CUTOFF)
    output = Path(result["payload_path"]).parent
    return output, json.loads((output / "prepared.json").read_bytes())


def retained(output):
    return {p.name: p.read_bytes() for p in output.iterdir() if p.is_file()}


def acknowledgement(http_status=201, **change):
    value = {"status": "stored", "snapshot_id": WORKER_ID, "as_of": "2026-11-05T14:00:00Z"}
    if http_status == 200:
        value = {"status": "unchanged", "snapshot_id": WORKER_ID}
    return httpx.Response(http_status, json=value | change)


def send(uploader, root, handler, source="S09", origin="http://127.0.0.1:8123"):
    return uploader.upload_local(
        root, source_id=source, origin=origin, transport=httpx.MockTransport(handler)
    )


@pytest.mark.parametrize("source", ["S01", "S09"])
def test_exact_prepared_bytes_signed_once_and_repeat_unchanged(uploader, tmp_path, source):
    output, pointer = prepared(tmp_path, source)
    before, calls = retained(output), []
    payload = (output / pointer["payload"]).read_bytes()

    def response(request):
        calls.append(request)
        assert str(request.url) == "http://127.0.0.1:8123/internal/ingest"
        assert request.method == "POST" and request.headers["content-type"] == "application/gzip"
        assert gzip.decompress(request.content) == payload
        assert request.content == gzip.compress(payload, mtime=0)
        timestamp = request.headers["X-Atlas-Timestamp"]
        assert abs(int(timestamp) - time.time()) < 5
        message = (
            f"{timestamp}\nPOST\n/internal/ingest\n{hashlib.sha256(request.content).hexdigest()}"
        )
        assert (
            request.headers["X-Atlas-Signature"]
            == hmac.new(KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
        )
        return acknowledgement(201 if len(calls) == 1 else 200)

    first = send(uploader, tmp_path, response, source)
    second = send(uploader, tmp_path, response, source)
    assert first["status"] == "stored" and second["status"] == "unchanged"
    assert first["snapshot_id"] == WORKER_ID
    assert first["prepared_sha256"] == pointer["sha256"] != WORKER_ID
    assert len(calls) == 2 and calls[0].content == calls[1].content
    assert retained(output) == before


@pytest.mark.parametrize(
    "origin",
    [
        "https://127.0.0.1:8123",
        "http://localhost:8123",
        "http://127.0.0.2:8123",
        "http://127.0.0.1",
        "http://127.0.0.1:0",
        "http://127.0.0.1:65536",
        "http://user:password@127.0.0.1:8123",
        "http://127.0.0.1:8123/",
        "http://127.0.0.1:8123/path",
        "http://127.0.0.1:8123?q=1",
        "http://127.0.0.1:8123#fragment",
        "http://127.0.0.1:8123\n",
        "http://127.0.0.1:8123?",
        "http://127.0.0.1:8123#",
        "http://127.0.0.1:8123\\path",
    ],
)
def test_non_explicit_loopback_origin_fails_before_network(uploader, tmp_path, origin):
    def unexpected(_):
        pytest.fail("Invalid origin reached transport")

    assert send(uploader, tmp_path, unexpected, origin=origin)["status"] == "failed"


@pytest.mark.parametrize("key", [None, "short"])
def test_missing_key_fails_before_network(uploader, tmp_path, monkeypatch, key):
    monkeypatch.delenv("ATLAS_INGEST_HMAC_KEY")
    if key is not None:
        monkeypatch.setenv("ATLAS_INGEST_HMAC_KEY", key)
    assert (
        send(uploader, tmp_path, lambda _: pytest.fail("Missing key reached network"))["status"]
        == "failed"
    )


def test_disabled_source_stops_before_reading_preparation(uploader, tmp_path, monkeypatch):
    state = load_state(ROOT / "configs/states/ka.yaml")
    state = state.model_copy(
        update={
            "sources": tuple(
                s.model_copy(update={"enabled": False}) if s.source_id == "S09" else s
                for s in state.sources
            )
        }
    )
    monkeypatch.setattr(uploader, "load_state", lambda _: state)
    result = send(uploader, tmp_path, lambda _: pytest.fail("Disabled source reached network"))
    assert result["status"] == "failed" and result["error_type"] == "SourceUnavailable"


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "invalid_json",
        "schema",
        "status",
        "source",
        "state",
        "cutoff",
        "payload_name",
        "inputs_name",
        "payload_hash",
        "inputs_hash",
        "payload_source",
        "payload_state",
        "payload_cutoff",
        "revision",
        "oversized",
        "compressed",
    ],
)
def test_damaged_preparation_never_sent_or_modified(uploader, tmp_path, damage, monkeypatch):
    output, pointer = prepared(tmp_path)
    path = output / "prepared.json"
    if damage == "missing":
        path.unlink()
    elif damage == "invalid_json":
        path.write_bytes(b"[]")
    elif damage in {"schema", "status", "source", "state", "cutoff", "payload_name", "inputs_name"}:
        field, value = {
            "schema": ("schema_version", True),
            "status": ("status", "published"),
            "source": ("source_id", "S01"),
            "state": ("state", "kl"),
            "cutoff": ("as_of", "2099-01-01T00:00:00Z"),
            "payload_name": ("payload", "../" + pointer["payload"]),
            "inputs_name": ("inputs", "../" + pointer["inputs"]),
        }[damage]
        pointer[field] = value
        path.write_text(json.dumps(pointer), "utf-8")
    elif damage in {"payload_hash", "inputs_hash"}:
        (output / pointer["payload" if damage == "payload_hash" else "inputs"]).write_bytes(
            b"damaged-test-copy"
        )
    elif damage == "compressed":
        monkeypatch.setattr(uploader.gzip, "compress", lambda *_, **__: b"x" * (1048576 + 1))
    else:
        payload = json.loads((output / pointer["payload"]).read_bytes())
        if damage == "payload_source":
            payload["source_id"] = "S01"
        else:
            field, value = {
                "payload_state": ("state", "kl"),
                "payload_cutoff": ("as_of", "2026-11-05T13:00:00Z"),
                "revision": ("data_revision", "b" * 64),
                "oversized": ("extra", "x" * 1048576),
            }[damage]
            payload["snapshot"][field] = value
        encoded = json.dumps(payload).encode()
        pointer["sha256"] = hashlib.sha256(encoded).hexdigest()
        pointer["payload"] = pointer["sha256"] + ".json"
        (output / pointer["payload"]).write_bytes(encoded)
        path.write_text(json.dumps(pointer), "utf-8")
    before = retained(output)
    result = send(uploader, tmp_path, lambda _: pytest.fail("Damaged preparation reached network"))
    assert result["status"] == "failed" and retained(output) == before


@pytest.mark.parametrize("status", [301, 307, 401, 409, 429, 503, 507])
def test_http_failures_are_sanitized_single_attempt_and_preserve_state(uploader, tmp_path, status):
    output, _ = prepared(tmp_path)
    before, calls = retained(output), []

    def response(request):
        calls.append(request)
        return httpx.Response(status, text=KEY, headers={"location": "https://example.invalid/"})

    result = send(uploader, tmp_path, response)
    assert result["status"] == "failed" and len(calls) == 1
    assert KEY not in json.dumps(result) and len(json.dumps(result)) < 400
    assert retained(output) == before


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(201, text="not JSON"),
        httpx.Response(201, json=[]),
        acknowledgement(snapshot_id="not-a-worker-hash"),
        acknowledgement(as_of="2026-11-05T13:00:00Z"),
        acknowledgement(200, status="stored"),
        acknowledgement(201, status="unchanged"),
        httpx.Response(201, content=b"x" * 4097),
        httpx.Response(
            201, content=gzip.compress(b"x" * 100000), headers={"content-encoding": "gzip"}
        ),
    ],
)
def test_invalid_or_oversized_acknowledgement_fails(uploader, tmp_path, response):
    output, _ = prepared(tmp_path)
    before = retained(output)
    assert send(uploader, tmp_path, lambda _: response)["status"] == "failed"
    assert retained(output) == before


@pytest.mark.parametrize("error", [httpx.ReadTimeout, httpx.ConnectError])
def test_transport_errors_are_bounded_and_sanitized(uploader, tmp_path, error):
    output, _ = prepared(tmp_path)
    before, calls = retained(output), []

    def response(request):
        calls.append(request)
        raise error(KEY, request=request)

    result = send(uploader, tmp_path, response)
    assert result["status"] == "failed" and len(calls) == 1
    assert KEY not in json.dumps(result) and retained(output) == before


def test_deeply_nested_acknowledgement_is_sanitized(uploader, tmp_path):
    output, _ = prepared(tmp_path)
    before = retained(output)
    response = httpx.Response(201, content=b"[" * 2000 + b"]" * 2000)
    assert send(uploader, tmp_path, lambda _: response)["status"] == "failed"
    assert retained(output) == before


def test_deeply_nested_damaged_pointer_is_sanitized(uploader, tmp_path):
    output, _ = prepared(tmp_path)
    (output / "prepared.json").write_bytes(b"[" * 2000 + b"]" * 2000)
    before = retained(output)
    assert (
        send(uploader, tmp_path, lambda _: pytest.fail("Damaged pointer sent"))["status"]
        == "failed"
    )
    assert retained(output) == before


def test_deeply_nested_payload_recursion_is_sanitized(uploader, tmp_path):
    output, pointer = prepared(tmp_path)
    encoded = b"[" * 10000 + b"]" * 10000
    pointer["sha256"] = hashlib.sha256(encoded).hexdigest()
    pointer["payload"] = pointer["sha256"] + ".json"
    (output / pointer["payload"]).write_bytes(encoded)
    (output / "prepared.json").write_text(json.dumps(pointer), "utf-8")
    before = retained(output)
    result = send(uploader, tmp_path, lambda _: pytest.fail("Malformed payload sent"))
    assert result["status"] == "failed" and result["error_type"] == "RecursionError"
    assert retained(output) == before


def test_streamed_acknowledgement_stops_at_cap(uploader, tmp_path):
    prepared(tmp_path)

    class Oversized(httpx.SyncByteStream):
        def __iter__(self):
            yield b"x" * 4097
            pytest.fail("Oversized reply was read past its cap")

    result = send(uploader, tmp_path, lambda _: httpx.Response(201, stream=Oversized()))
    assert result["status"] == "failed"


def test_parent_routes_only_one_http_child_with_deadline_and_no_secret_argv(
    uploader, tmp_path, monkeypatch, capsys
):
    calls = []

    def bounded(command, *, timeout):
        calls.append((command, timeout))
        return {"status": "deadline", "coverage": "partial"}

    monkeypatch.setattr(uploader, "run_bounded", bounded)
    monkeypatch.setattr(
        sys,
        "argv",
        ["upload", "--root", str(tmp_path), "--source", "S09", "--origin", "http://127.0.0.1:8123"],
    )
    with pytest.raises(SystemExit) as stopped:
        uploader.main()
    assert stopped.value.code == 1 and len(calls) == 1
    command, timeout = calls[0]
    assert timeout == 15 and command[:4] == [sys.executable, "-m", "atlas.ingest.upload", "--child"]
    assert KEY not in " ".join(command)
    assert json.loads(capsys.readouterr().out)["status"] == "deadline"


@contextmanager
def local_server(respond):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["content-length"]))
            calls.append((self.path, dict(self.headers), body))
            status, reply = respond(body)
            self.send_response(status)
            self.send_header("Content-Length", str(len(reply)))
            self.end_headers()
            try:
                self.wfile.write(reply)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_public_cli_loopback_ignores_proxy_environment(uploader, tmp_path):
    output, pointer = prepared(tmp_path)
    before = retained(output)
    env = os.environ | {
        "HTTP_PROXY": "http://127.0.0.1:1",
        "ALL_PROXY": "http://127.0.0.1:1",
        "NO_PROXY": "",
    }
    reply = json.dumps(
        {"status": "stored", "snapshot_id": WORKER_ID, "as_of": pointer["as_of"]}
    ).encode()
    command = [sys.executable, "-m", "atlas.ingest.upload"]
    powershell = shutil.which("powershell")
    if powershell and (ROOT / ".venv/Scripts/python.exe").is_file():
        command = [
            powershell,
            "-NoProfile",
            "-File",
            str(ROOT / "scripts/feeds.ps1"),
            "upload-local",
        ]
    with local_server(lambda _: (201, reply)) as (origin, calls):
        result = subprocess.run(
            [*command, "--source", "S09", "--origin", origin, "--root", str(tmp_path)],
            env=env,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=25,
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["snapshot_id"] == WORKER_ID
    assert len(calls) == 1 and gzip.decompress(calls[0][2]) == before[pointer["payload"]]
    assert KEY not in result.stdout + result.stderr and retained(output) == before


def test_public_cli_times_out_local_silent_worker(uploader, tmp_path):
    output, _ = prepared(tmp_path)
    before = retained(output)

    def silent(_):
        time.sleep(7)
        return 503, b"test-only-late-reply"

    started = time.monotonic()
    with local_server(silent) as (origin, calls):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "atlas.ingest.upload",
                "--source",
                "S09",
                "--origin",
                origin,
                "--root",
                str(tmp_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=25,
        )
    assert 0 < time.monotonic() - started < 20
    assert result.returncode == 1 and json.loads(result.stdout)["status"] == "failed"
    assert json.loads(result.stdout)["error_type"] == "ReadTimeout"
    assert len(calls) == 1 and retained(output) == before


def test_public_cli_preserves_sanitized_http_failure(uploader, tmp_path):
    output, _ = prepared(tmp_path)
    before = retained(output)
    with local_server(lambda _: (503, KEY.encode())) as (origin, calls):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "atlas.ingest.upload",
                "--source",
                "S09",
                "--origin",
                origin,
                "--root",
                str(tmp_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=25,
        )
    assert result.returncode == 1
    assert json.loads(result.stdout)["http_status"] == 503
    assert KEY not in result.stdout + result.stderr
    assert len(calls) == 1 and retained(output) == before


def test_python_signature_and_gzip_pass_actual_worker_authenticate_and_decode(uploader, tmp_path):
    node = ROOT / ".tools/node/node-v22.16.0-win-x64/node.exe"
    if not node.is_file():
        pytest.skip("Optional pinned local Node is absent in core-only CI")
    output, pointer = prepared(tmp_path)
    captured = []

    def response(request):
        captured.append(request)
        return acknowledgement()

    assert send(uploader, tmp_path, response)["status"] == "stored"
    request = captured[0]
    packet = tmp_path / "test-upload.gz"
    packet.write_bytes(request.content)
    validator = json.dumps((ROOT / "worker/src/ingest.ts").as_uri())
    script = (
        "import {readFileSync} from 'node:fs';"
        f"import {{authenticate,decodeUpload}} from {validator};"
        "const bytes=readFileSync(process.argv[1]);"
        "const headers=JSON.parse(process.env.TEST_HEADERS);"
        "const request=new Request('http://127.0.0.1:8123/internal/ingest',{method:'POST',headers,body:bytes});"
        "if(!await authenticate(request,bytes,process.env.ATLAS_INGEST_HMAC_KEY,Date.now()))"
        "throw Error('HMAC');"
        "const decoded=await decodeUpload(bytes,Date.now());"
        "console.log(JSON.stringify({id:decoded.sha256,"
        "warning:decoded.snapshot.records[0].warning_text,status:decoded.snapshot.sources[0].status}));"
    )
    result = subprocess.run(
        [str(node), "--experimental-strip-types", "--input-type=module", "-e", script, str(packet)],
        cwd=ROOT,
        env=os.environ
        | {
            "TEST_HEADERS": json.dumps(dict(request.headers)),
            "TEMP": str(ROOT / ".cache/tmp"),
            "TMP": str(ROOT / ".cache/tmp"),
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    decoded = json.loads(result.stdout)
    assert len(decoded["id"]) == 64 and decoded["id"] != pointer["sha256"]
    assert (
        decoded["warning"]
        == json.loads((output / pointer["payload"]).read_bytes())["snapshot"]["records"][0][
            "warning_text"
        ]
    )
    assert decoded["status"] == "partial"
