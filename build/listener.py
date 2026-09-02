#!/usr/bin/env python3
"""Hindsight ingest listener — the one sanctioned background process (ADR-0001).

Receives OTLP/HTTP JSON on /v1/logs and /v1/metrics, writes otel_events and
otel_metrics rows to the local SQLite store, and does nothing else. Ingest
contract (ADR-0003, definition/ingest-schema-verification.md): chunked bodies
handled explicitly, every attribute optional-by-default kept as JSON, per-row
count-and-skip, always return 200. Stdlib only.

Usage:
  listener.py [--port N] [--db PATH]   run in the foreground (default :4318)
  listener.py install                  write launchd plist + start the agent
  listener.py uninstall                stop the agent + remove the plist
"""
import gzip
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO / "local-data" / "hindsight.db"
DEFAULT_PORT = 4318
LAUNCHD_LABEL = "com.hindsight.ingest"

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
    conn = sqlite3.connect(db_path)
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
        for sl in _items(rl, "scopeLogs"):
            for rec in _items(sl, "logRecords"):
                try:
                    attrs = attr_dict(rec.get("attributes"))
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
                body += self.rfile.read(size)
                self.rfile.readline()
            return body
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def do_POST(self):
        rejected_key = ("rejectedDataPoints" if self.path == "/v1/metrics"
                        else "rejectedLogRecords")
        bad = 0
        try:
            body = self._read_body()
            if self.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
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
            print(f"ingest error on {self.path}: {e}", file=sys.stderr, flush=True)
        if bad:
            print(f"{self.path}: skipped {bad} row(s)", file=sys.stderr, flush=True)
        resp = json.dumps(
            {"partialSuccess": {rejected_key: bad}} if bad else {}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp)))
        self.end_headers()
        self.wfile.write(resp)

    def log_message(self, *args):
        pass


def make_server(port=DEFAULT_PORT, db_path=DEFAULT_DB):
    init_db(db_path)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.db_path = str(db_path)
    return server


PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{python}</string>
    <string>{script}</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict>
</plist>
"""


def install():
    log = REPO / "local-data" / "listener.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(PLIST.format(
        label=LAUNCHD_LABEL, python=sys.executable,
        script=str(Path(__file__).resolve()), log=log))
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(PLIST_PATH)],
                   capture_output=True)
    subprocess.run(["launchctl", "bootstrap", domain, str(PLIST_PATH)], check=True)
    print(f"installed {PLIST_PATH}, listening on :{DEFAULT_PORT}")


def uninstall():
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(PLIST_PATH)],
                   capture_output=True)
    PLIST_PATH.unlink(missing_ok=True)
    print(f"removed {PLIST_PATH}")


def main(argv):
    if argv[:1] == ["install"]:
        return install()
    if argv[:1] == ["uninstall"]:
        return uninstall()
    port, db = DEFAULT_PORT, DEFAULT_DB
    args = iter(argv)
    for a in args:
        if a == "--port":
            port = int(next(args))
        elif a == "--db":
            db = Path(next(args))
        else:
            sys.exit(__doc__)
    server = make_server(port, db)
    print(f"ingest listener on :{server.server_address[1]}, store {db}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main(sys.argv[1:])
