"""The only network boundary for ingestion (plan T004).

- https only, allowlisted hosts, redirects followed manually and re-checked against the allowlist
- 30 s timeout; up to 3 retries at 2/8/30 s plus jitter; Retry-After honoured (capped)
- conditional GET (ETag / Last-Modified); 304 reuses the stored artifact, no duplicate file
- byte budget enforced while streaming; request budget per run
- circuit breaker: after 3 consecutive failed fetches for a source, no further requests
- secrets come from ctx.secrets and are never logged, stored or put in source_url
- offline replay: pass FixtureTransport to run against recorded fixtures with no network
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx

from atlas import __version__
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import (
    BudgetExceeded,
    CircuitOpen,
    FetchError,
    HostNotAllowed,
    SourceUnavailable,
    TooLarge,
)
from atlas.ingest.raw_store import RawStore

log = logging.getLogger(__name__)

_SECRET_IN_URL = re.compile(r"(?i)([?&](?:api[_-]?key|key|token|access_token|map_key)=)[^&\s\"']+")


class _RedactUrls(logging.Filter):
    """httpx logs full request URLs at INFO; strip key-like query values before any handler."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _SECRET_IN_URL.sub(r"\1REDACTED", record.getMessage())
        record.args = ()
        return True


for _name in ("httpx", "httpcore"):
    # Quiet by default and redacted even if someone turns INFO back on for debugging.
    logging.getLogger(_name).setLevel(logging.WARNING)
    logging.getLogger(_name).addFilter(_RedactUrls())

USER_AGENT = f"MonsoonAtlas/{__version__} (+https://github.com/Joepikka/monsoon-atlas)"
TIMEOUT_S = 30.0
RETRY_DELAYS_S = (2.0, 8.0, 30.0)
# shortcut: Retry-After above 5 minutes fails the fetch instead of blocking a scheduled job.
MAX_RETRY_AFTER_S = 300.0
MAX_REDIRECTS = 5
BREAKER_THRESHOLD = 3
RETRY_STATUS = {429, 500, 502, 503, 504}
KEPT_HEADERS = ("etag", "last-modified", "content-type", "content-length", "date", "cache-control")
EXT = {
    "application/json": "json",
    "application/geo+json": "geojson",
    "application/xml": "xml",
    "text/xml": "xml",
    "application/rss+xml": "xml",
    "text/html": "html",
    "text/csv": "csv",
    "application/zip": "zip",
    "application/pdf": "pdf",
    "application/vnd.google-earth.kml+xml": "kml",
    "image/png": "png",
    "image/jpeg": "jpg",
}


def _retry_after_s(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        return max(0.0, (when - datetime.now(UTC)).total_seconds())


class Fetcher:
    def __init__(
        self,
        store: RawStore,
        allowed_hosts: set[str],
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        retry_delays: tuple[float, ...] = RETRY_DELAYS_S,
    ):
        self.store = store
        self.retry_delays = retry_delays  # () for providers that forbid retries (D109)
        self.allowed_hosts = {h.lower() for h in allowed_hosts}
        self.client = httpx.Client(
            transport=transport,
            timeout=TIMEOUT_S,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
        )
        self.sleep = sleep
        self.rng = rng or random.Random()
        self.clock = clock
        self._failures: dict[str, int] = {}
        self._requests: dict[str, int] = {}

    def _check_url(self, url: str) -> None:
        parts = urlsplit(url)
        if parts.scheme != "https" or (parts.hostname or "").lower() not in self.allowed_hosts:
            raise HostNotAllowed(f"blocked URL host or scheme: {parts.scheme}://{parts.hostname}")

    def fetch_bytes(
        self,
        ctx: FetchContext,
        url: str,
        *,
        mapping_version: str,
        params: Mapping[str, str] | None = None,
        secret_params: Mapping[str, str] | None = None,
    ) -> RawArtifact:
        """Fetch one URL and store it. `secret_params` maps query name -> ctx.secrets key."""
        if self._failures.get(ctx.source_id, 0) >= BREAKER_THRESHOLD:
            raise CircuitOpen(f"{ctx.source_id}: {BREAKER_THRESHOLD} consecutive failures")
        # The recorded URL carries only public params; secrets are added to the request only.
        public_url = f"{url}?{urlencode(sorted(params.items()))}" if params else url
        missing = [key for key in (secret_params or {}).values() if key not in ctx.secrets]
        if missing:
            raise SourceUnavailable(f"{ctx.source_id}: secret not configured: {missing}")
        secrets = {name: ctx.secrets[key] for name, key in (secret_params or {}).items()}
        try:
            artifact = self._fetch(ctx, public_url, secrets, mapping_version)
        except FetchError:
            self._failures[ctx.source_id] = self._failures.get(ctx.source_id, 0) + 1
            raise
        except httpx.HTTPError as exc:
            self._failures[ctx.source_id] = self._failures.get(ctx.source_id, 0) + 1
            raise FetchError(f"{ctx.source_id}: {type(exc).__name__}") from None
        self._failures[ctx.source_id] = 0
        return artifact

    def _fetch(
        self, ctx: FetchContext, public_url: str, secrets: dict[str, str], mapping_version: str
    ) -> RawArtifact:
        self._check_url(public_url)
        prior = self.store.latest_ok(public_url)
        headers = {}
        if prior:
            if etag := prior["http"].get("etag"):
                headers["If-None-Match"] = etag
            if modified := prior["http"].get("last-modified"):
                headers["If-Modified-Since"] = modified

        for attempt in range(len(self.retry_delays) + 1):
            try:
                status, body, resp_headers, final_url = self._request(
                    ctx, public_url, secrets, headers
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt == len(self.retry_delays):
                    raise FetchError(
                        f"{ctx.source_id}: {type(exc).__name__} after retries"
                    ) from None
                self._wait(ctx, self.retry_delays[attempt], None)
                continue
            if status in RETRY_STATUS and attempt < len(self.retry_delays):
                self._wait(ctx, self.retry_delays[attempt], resp_headers.get("retry-after"))
                continue
            break

        fetched_at = self.clock()
        http_meta = {"status": status, "final_url": final_url} | {
            k: resp_headers[k] for k in KEPT_HEADERS if k in resp_headers
        }
        if status == 304 and prior:
            old = prior["artifact"]
            artifact = RawArtifact(
                sha256=old["sha256"],
                path=Path(old["path"]),
                fetched_at=fetched_at,
                media_type=old["media_type"],
                response_status=304,
                source_url=public_url,
                schema_mapping_version=mapping_version,
            )
            http_meta |= {
                k: prior["http"][k] for k in ("etag", "last-modified") if k in prior["http"]
            }
            self.store.record(artifact, http_meta)
            log.info("%s not modified: %s", ctx.source_id, public_url)
            return artifact
        if status != 200:
            raise FetchError(f"{ctx.source_id}: HTTP {status} for {public_url}")

        media_type = resp_headers.get("content-type", "application/octet-stream").split(";")[0]
        path, sha = self.store.put(
            body, ctx.source_id, fetched_at, EXT.get(media_type.strip().lower(), "bin")
        )
        artifact = RawArtifact(
            sha256=sha,
            path=path,
            fetched_at=fetched_at,
            media_type=media_type.strip(),
            response_status=200,
            source_url=public_url,
            schema_mapping_version=mapping_version,
        )
        self.store.record(artifact, http_meta)
        log.info("%s stored %s (%d bytes)", ctx.source_id, sha[:12], len(body))
        return artifact

    def fetch_large(self, ctx: FetchContext, url: str, *, mapping_version: str) -> RawArtifact:
        """Stream one large public file straight to the raw store (no memory copy, no retry,
        no conditional GET). The byte budget still applies while streaming."""
        self._check_url(url)
        used = self._requests.get(ctx.run_id, 0)
        if used >= ctx.budget.max_requests:
            raise BudgetExceeded(f"{ctx.source_id}: request budget {used} reached")
        self._requests[ctx.run_id] = used + 1
        try:
            with self.client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    raise FetchError(f"{ctx.source_id}: HTTP {resp.status_code} for {url}")
                headers = {k.lower(): v for k, v in resp.headers.items()}
                declared = int(headers.get("content-length") or 0)
                if declared > ctx.budget.max_bytes:
                    raise TooLarge(f"{ctx.source_id}: {declared} bytes > budget")

                def chunks():
                    size = 0
                    for chunk in resp.iter_bytes(1024 * 1024):
                        size += len(chunk)
                        if size > ctx.budget.max_bytes:
                            raise TooLarge(f"{ctx.source_id}: response exceeded byte budget")
                        yield chunk

                fetched_at = self.clock()
                media_type = headers.get("content-type", "application/octet-stream").split(";")[0]
                ext = EXT.get(media_type.strip().lower(), "bin")
                path, sha, size = self.store.put_stream(
                    chunks(), ctx.source_id, fetched_at, ext, expected_size=declared
                )
        except httpx.HTTPError as exc:
            raise FetchError(f"{ctx.source_id}: {type(exc).__name__}") from None
        artifact = RawArtifact(
            sha256=sha,
            path=path,
            fetched_at=fetched_at,
            media_type=media_type.strip(),
            response_status=200,
            source_url=url,
            schema_mapping_version=mapping_version,
        )
        kept = {k: headers[k] for k in KEPT_HEADERS if k in headers}
        meta = {"status": 200, "final_url": url} | kept
        self.store.record(artifact, meta)
        log.info("%s streamed %s (%d bytes)", ctx.source_id, sha[:12], size)
        return artifact

    def _wait(self, ctx: FetchContext, base: float, retry_after: str | None) -> None:
        delay = _retry_after_s(retry_after)
        if delay is None:
            delay = base + self.rng.uniform(0, 1)
        elif delay > MAX_RETRY_AFTER_S:
            raise FetchError(f"{ctx.source_id}: Retry-After {delay:.0f}s exceeds cap")
        log.info("%s retrying in %.1fs", ctx.source_id, delay)
        self.sleep(delay)

    def _request(
        self, ctx: FetchContext, public_url: str, secrets: dict[str, str], headers: dict[str, str]
    ) -> tuple[int, bytes, dict[str, str], str]:
        url, sep = public_url, "&" if "?" in public_url else "?"
        request_url = f"{url}{sep}{urlencode(secrets)}" if secrets else url
        for _ in range(MAX_REDIRECTS + 1):
            used = self._requests.get(ctx.run_id, 0)
            if used >= ctx.budget.max_requests:
                raise BudgetExceeded(f"{ctx.source_id}: request budget {used} reached")
            self._requests[ctx.run_id] = used + 1
            with self.client.stream("GET", request_url, headers=headers) as resp:
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = str(resp.url.join(resp.headers.get("location", "")))
                    self._check_url(location)
                    request_url = url = location  # redirect targets carry no secrets
                    continue
                declared = int(resp_headers.get("content-length") or 0)
                if declared > ctx.budget.max_bytes:
                    raise TooLarge(f"{ctx.source_id}: {declared} bytes > budget")
                chunks, size = [], 0
                for chunk in resp.iter_bytes():
                    size += len(chunk)
                    if size > ctx.budget.max_bytes:
                        raise TooLarge(f"{ctx.source_id}: response exceeded byte budget")
                    chunks.append(chunk)
                return resp.status_code, b"".join(chunks), resp_headers, url
        raise FetchError(f"{ctx.source_id}: more than {MAX_REDIRECTS} redirects")


class FixtureTransport(httpx.BaseTransport):
    """Offline replay. Serves recorded responses keyed by URL with secret params removed;
    any request without a fixture fails, so tests and replays never touch the network."""

    def __init__(self, fixtures_dir: Path, secret_names: tuple[str, ...] = ()):
        self.dir = Path(fixtures_dir)
        self.secret_names = set(secret_names)

    @staticmethod
    def key(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:24]

    def _public(self, url: httpx.URL) -> str:
        params = [(k, v) for k, v in url.params.multi_items() if k not in self.secret_names]
        base = str(url.copy_with(query=None))
        return f"{base}?{urlencode(sorted(params))}" if params else base

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        key = self.key(self._public(request.url))
        meta_path = self.dir / f"{key}.json"
        if not meta_path.exists():
            raise httpx.ConnectError(f"no fixture for {self._public(request.url)}", request=request)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        body = (self.dir / f"{key}.bin").read_bytes()
        return httpx.Response(meta["status"], headers=meta.get("headers", {}), content=body)

    @classmethod
    def record(
        cls,
        fixtures_dir: Path,
        url: str,
        body: bytes,
        status: int = 200,
        headers: dict | None = None,
    ) -> None:
        d = Path(fixtures_dir)
        d.mkdir(parents=True, exist_ok=True)
        key = cls.key(url)
        (d / f"{key}.bin").write_bytes(body)
        meta = {"url": url, "status": status, "headers": headers or {}}
        (d / f"{key}.json").write_text(json.dumps(meta), encoding="utf-8")
