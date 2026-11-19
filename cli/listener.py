#!/usr/bin/env python3
"""Hindsight ingest listener — the one sanctioned background process (ADR-0001).

Receives OTLP/HTTP JSON on /v1/logs and /v1/metrics, writes otel_events and
otel_metrics rows to the local SQLite store, and its `listener` health row (#93). Ingest
contract (ADR-0003, definition/ingest-schema-verification.md): chunked bodies
handled explicitly, every attribute optional-by-default kept as JSON, per-row
count-and-skip, always return 200 once a body is accepted. Two guards run
before the body is read (#34): Content-Type must be application/json (415)
and the declared, chunked or inflated body must fit MAX_BODY (413 / dropped).
The one GET, /health, is a liveness probe (#37) and touches nothing.
Stdlib only.

Usage:
  listener.py [--port N] [--db PATH] [--log]   run in the foreground (default :4318);
                                               --log appends to <Hindsight home>/logs
The launchd agent (`com.hindsight.ingest`) is written by `/hindsight:ops install`.
"""
import json
import sqlite3
import sys
import zlib
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from capture import write_health
from home import home, log_to

DEFAULT_DB = home() / "hindsight.db"
DEFAULT_PORT = 4318
MAX_BODY = 8 * 1024 * 1024   # #34: declared, chunked and inflated body ceiling

SCHEMA = """
CREATE TABLE IF NOT EXISTS otel_events (
  id INTEGER PRIMARY KEY,
  event_name TEXT,
  session_id TEXT,
  timestamp TEXT,
  attributes TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_otel_events_session ON otel_events(session_id);
CREATE TABLE IF NOT EXISTS otel_metrics (
  id INTEGER PRIMARY KEY,
  metric_name TEXT,
  timestamp TEXT,
  value REAL,
  attributes TEXT NOT NULL
);
"""


def init_db(db_path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # launchd restarts the listener whenever it exits, nightly run or not:
    # the schema DDL must wait for an analyze.py write, not fail at 5 s.
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")   # issue #12; see analyze.init_db
    conn.executescript(SCHEMA)
    conn.close()


def attr_dict(attr_list):
    """OTLP [{key, value: {stringValue|intValue|...}}] -> plain dict."""
    out = {}
    for a in attr_list or []:
        v = a.get("value", {})
        out[a["key"]] = next(iter(v.values()), None)
    return out


def iso(unix_nano):
    if not unix_nano:
        return None
    dt = datetime.fromtimestamp(int(unix_nano) / 1e9, tz=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _items(container, key):
    """Tolerant nested lookup: [] unless container is a dict holding a list.
    Keeps a malformed container from raising outside the per-row try, which
    would roll back the batch's good rows."""
    x = container.get(key) if isinstance(container, dict) else None
    return x if isinstance(x, list) else []


def ingest_logs(payload, conn):
    ok = bad = 0
    for rl in _items(payload, "resourceLogs"):
        # the OTel histogram's version key (ADR-0037 §4) is a resource
        # attribute; a malformed resource must not cost its records
        try:
            res = attr_dict(_items(rl.get("resource"), "attributes"))
            res = {k: res[k] for k in ("service.name", "service.version") if k in res}
        except Exception:
            res = {}
        for sl in _items(rl, "scopeLogs"):
            for rec in _items(sl, "logRecords"):
                try:
                    # the record's own attributes win on a clash
                    attrs = res | attr_dict(rec.get("attributes"))
                    name = attrs.get("event.name") or (
                        str((rec.get("body") or {}).get("stringValue", ""))
                        .removeprefix("claude_code.") or None)
                    ts = attrs.get("event.timestamp") or iso(rec.get("timeUnixNano"))
                    conn.execute(
                        "INSERT INTO otel_events (event_name, session_id, timestamp, attributes)"
                        " VALUES (?, ?, ?, ?)",
                        (name, attrs.get("session.id"), ts, json.dumps(attrs)))
                    ok += 1
                except Exception:
                    bad += 1
    return ok, bad


def ingest_metrics(payload, conn):
    ok = bad = 0
    for rm in _items(payload, "resourceMetrics"):
        for sm in _items(rm, "scopeMetrics"):
            for metric in _items(sm, "metrics"):
                if not isinstance(metric, dict):
                    bad += 1
                    continue
                name = metric.get("name")
                for kind in ("sum", "gauge", "histogram"):
                    for dp in _items(metric.get(kind), "dataPoints"):
                        try:
                            attrs = attr_dict(dp.get("attributes"))
                            val = dp.get("asDouble", dp.get("asInt", dp.get("sum")))
                            conn.execute(
                                "INSERT INTO otel_metrics (metric_name, timestamp, value, attributes)"
                                " VALUES (?, ?, ?, ?)",
                                (name, iso(dp.get("timeUnixNano")),
                                 None if val is None else float(val), json.dumps(attrs)))
                            ok += 1
                        except Exception:
                            bad += 1
    return ok, bad


class Handler(BaseHTTPRequestHandler):
    def _read_body(self):
        # The zero-byte-body regression: Claude Code sends chunked transfer
        # encoding with no Content-Length; reading by Content-Length gets b"".
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            body = b""
            while True:
                size = int(self.rfile.readline().split(b";")[0].strip(), 16)
                if size == 0:
                    self.rfile.readline()
                    break
                if len(body) + size > MAX_BODY:
                    raise ValueError(f"chunked body over {MAX_BODY} bytes")
                body += self.rfile.read(size)
                self.rfile.readline()
            return body
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def _refuse(self, status, why):
        print(f"{self.path}: refused {status}, {why}", file=sys.stderr, flush=True)
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        # #34: both guards run before the body is read. A browser cannot send
        # application/json cross-origin without a preflight, and there is no
        # OPTIONS handler, so the type check alone closes the page vector.
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return self._refuse(415, "content-type not application/json")
        length = self.headers.get("Content-Length", "")
        if length.isdecimal() and int(length) > MAX_BODY:
            return self._refuse(413, f"content-length over {MAX_BODY} bytes")
        rejected_key = ("rejectedDataPoints" if self.path == "/v1/metrics"
                        else "rejectedLogRecords")
        bad, error = 0, None
        try:
            body = self._read_body()
            if self.headers.get("Content-Encoding") == "gzip":
                z = zlib.decompressobj(31)
                body = z.decompress(body, MAX_BODY + 1)
                if len(body) > MAX_BODY:
                    raise ValueError(f"inflated body over {MAX_BODY} bytes")
                if not z.eof:
                    raise ValueError("truncated gzip stream")
            payload = json.loads(body)
            conn = sqlite3.connect(self.server.db_path)
            conn.execute("PRAGMA busy_timeout = 5000")
            try:
                with conn:
                    if self.path == "/v1/logs":
                        _, bad = ingest_logs(payload, conn)
                    elif self.path == "/v1/metrics":
                        _, bad = ingest_metrics(payload, conn)
            finally:
                conn.close()
        except Exception as e:
            bad += 1
            error = f"{self.path}: {type(e).__name__}: {e}"
            print(f"ingest error on {self.path}: {e}", file=sys.stderr, flush=True)
        self._health(error)
        if bad:
            print(f"{self.path}: skipped {bad} row(s)", file=sys.stderr, flush=True)
        resp = json.dumps(
            {"partialSuccess": {rejected_key: bad}} if bad else {}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp)))
        self.end_headers()
        self.wfile.write(resp)

    def _health(self, error):
        """The `listener` health row (#93). Per-row skips are the ingest
        contract's count-and-skip, not an error; a body that failed is."""
        try:
            conn = sqlite3.connect(self.server.db_path, timeout=5)
            try:
                write_health(conn, error, source="listener")
            finally:
                conn.close()
        except sqlite3.Error:
            pass  # no health table until the analysis run migrates the store

    def do_GET(self):
        # #37: the liveness probe. The one GET, no DB touch.
        ok = self.path == "/health"
        body = b'{"ok": true}' if ok else b""
        self.send_response(200 if ok else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def make_server(port=DEFAULT_PORT, db_path=DEFAULT_DB):
    init_db(db_path)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.db_path = str(db_path)
    return server


def main(argv):
    port, db = DEFAULT_PORT, DEFAULT_DB
    args = iter(argv)
    for a in args:
        if a == "--port":
            port = int(next(args))
        elif a == "--db":
            db = Path(next(args))
        elif a == "--log":
            log_to("listener.log")
        else:
            sys.exit(__doc__)
    server = make_server(port, db)
    print(f"ingest listener on :{server.server_address[1]}, store {db}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main(sys.argv[1:])
