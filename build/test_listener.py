"""Seam-1 tests for the ingest listener (ticket #16).

External behaviour at the HTTP boundary only: POST OTLP payloads at a
listener on an ephemeral localhost port, assert SQLite rows, skip counters
(OTLP partialSuccess), and unconditional 200s. No network beyond localhost.

Fixtures mirror the verified 2.1.91 shapes (definition/ingest-schema-
verification.md) with identifiers scrubbed; when the real gitignored
captures exist locally they are replayed too.
"""
import http.client
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

import listener

REPO = Path(__file__).resolve().parent.parent
REAL_CAPTURES = REPO / "local-data" / "otel-capture"


def log_record(event_name="user_prompt", session_id="sess-1", **extra):
    attrs = {"event.name": event_name, "session.id": session_id,
             "event.timestamp": "2026-08-01T14:30:16.543Z", **extra}
    return {
        "timeUnixNano": "1785594616543000000",
        "body": {"stringValue": f"claude_code.{event_name}"},
        "attributes": [{"key": k, "value": {"stringValue": v}}
                       for k, v in attrs.items() if v is not None],
    }


def logs_payload(*records):
    return {"resourceLogs": [{"resource": {"attributes": []},
                              "scopeLogs": [{"scope": {"name": "com.anthropic.claude_code.events"},
                                             "logRecords": list(records)}]}]}


METRICS_PAYLOAD = {
    "resourceMetrics": [{"scopeMetrics": [{"metrics": [{
        "name": "claude_code.token.usage",
        "sum": {"aggregationTemporality": 1, "isMonotonic": True,
                "dataPoints": [{
                    "attributes": [
                        {"key": "session.id", "value": {"stringValue": "sess-1"}},
                        {"key": "type", "value": {"stringValue": "input"}}],
                    "timeUnixNano": "1785594619306000000",
                    "asDouble": 42}]}}]}]}]}


class ListenerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "test.db"
        cls.server = listener.make_server(port=0, db_path=cls.db)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def post(self, path, body, chunked=False, raw=False):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        data = body if raw else json.dumps(body).encode()
        if chunked:
            conn.request("POST", path, iter([data]), {"Content-Type": "application/json"},
                         encode_chunked=True)
        else:
            conn.request("POST", path, data, {"Content-Type": "application/json"})
        resp = conn.getresponse()
        out = (resp.status, json.loads(resp.read() or b"{}"))
        conn.close()
        return out

    def rows(self, table):
        db = sqlite3.connect(self.db)
        try:
            return db.execute(f"SELECT * FROM {table}").fetchall()
        finally:
            db.close()

    def count(self, table):
        return len(self.rows(table))

    def test_chunked_body_not_read_as_zero_bytes(self):
        # The named zero-byte-body regression: chunked transfer encoding,
        # no Content-Length header, must still persist rows.
        before = self.count("otel_events")
        status, body = self.post("/v1/logs", logs_payload(log_record()), chunked=True)
        self.assertEqual(status, 200)
        self.assertEqual(body, {})
        self.assertEqual(self.count("otel_events"), before + 1)

    def test_real_captured_payload_chunked(self):
        captures = sorted(REAL_CAPTURES.glob("*_v1_logs.json"))
        if not captures:
            self.skipTest("real captures not present (gitignored)")
        before = self.count("otel_events")
        status, _ = self.post("/v1/logs", captures[0].read_bytes(), chunked=True, raw=True)
        self.assertEqual(status, 200)
        new = self.count("otel_events") - before
        self.assertGreater(new, 0)
        db = sqlite3.connect(self.db)
        name, sid, attrs = db.execute(
            "SELECT event_name, session_id, attributes FROM otel_events "
            "ORDER BY id DESC LIMIT 1").fetchone()
        db.close()
        self.assertTrue(name)
        self.assertTrue(sid)
        self.assertIn("event.name", json.loads(attrs))

    def test_event_row_fields(self):
        self.post("/v1/logs", logs_payload(log_record("tool_decision", "sess-2",
                                                      tool_name="Edit", decision="accept")))
        db = sqlite3.connect(self.db)
        row = db.execute(
            "SELECT event_name, session_id, timestamp, attributes FROM otel_events "
            "WHERE session_id='sess-2'").fetchone()
        db.close()
        self.assertEqual(row[0], "tool_decision")
        self.assertEqual(row[2], "2026-08-01T14:30:16.543Z")
        self.assertEqual(json.loads(row[3])["decision"], "accept")

    def test_metrics_payload_persists(self):
        status, body = self.post("/v1/metrics", METRICS_PAYLOAD, chunked=True)
        self.assertEqual(status, 200)
        self.assertEqual(body, {})
        db = sqlite3.connect(self.db)
        row = db.execute(
            "SELECT metric_name, timestamp, value, attributes FROM otel_metrics "
            "ORDER BY id DESC LIMIT 1").fetchone()
        db.close()
        self.assertEqual(row[0], "claude_code.token.usage")
        self.assertTrue(row[1])
        self.assertEqual(row[2], 42.0)
        self.assertEqual(json.loads(row[3])["session.id"], "sess-1")

    def test_malformed_row_counted_and_skipped(self):
        good1, good2 = log_record(session_id="sess-3"), log_record(session_id="sess-4")
        bad = {"attributes": "not-a-list"}
        before = self.count("otel_events")
        status, body = self.post("/v1/logs", logs_payload(good1, bad, good2))
        self.assertEqual(status, 200)
        self.assertEqual(body, {"partialSuccess": {"rejectedLogRecords": 1}})
        self.assertEqual(self.count("otel_events"), before + 2)

    def test_malformed_container_does_not_roll_back_batch(self):
        # A structural fault above row level must not discard the batch's
        # good rows (per-row commit was the review's one confirmed defect).
        payload = {"resourceLogs": [
            {"scopeLogs": "garbage"},
            logs_payload(log_record(session_id="sess-container"))["resourceLogs"][0],
        ]}
        status, _ = self.post("/v1/logs", payload)
        self.assertEqual(status, 200)
        db = sqlite3.connect(self.db)
        n = db.execute("SELECT COUNT(*) FROM otel_events "
                       "WHERE session_id='sess-container'").fetchone()[0]
        db.close()
        self.assertEqual(n, 1)

    def test_malformed_metric_does_not_roll_back_batch(self):
        payload = {"resourceMetrics": [{"scopeMetrics": [{"metrics": [
            {"name": "bad.metric", "sum": "garbage"},
            "not-a-metric",
            METRICS_PAYLOAD["resourceMetrics"][0]["scopeMetrics"][0]["metrics"][0],
        ]}]}]}
        before = self.count("otel_metrics")
        status, body = self.post("/v1/metrics", payload)
        self.assertEqual(status, 200)
        self.assertEqual(body, {"partialSuccess": {"rejectedDataPoints": 1}})
        self.assertEqual(self.count("otel_metrics"), before + 1)

    def test_unknown_event_name_and_missing_attributes_persist(self):
        rec = {"timeUnixNano": "1785594616543000000",
               "attributes": [{"key": "event.name",
                               "value": {"stringValue": "some_future_event"}}]}
        before = self.count("otel_events")
        status, body = self.post("/v1/logs", logs_payload(rec))
        self.assertEqual(status, 200)
        self.assertEqual(body, {})
        self.assertEqual(self.count("otel_events"), before + 1)

    def test_garbage_body_still_200(self):
        status, body = self.post("/v1/logs", b"not json at all", raw=True)
        self.assertEqual(status, 200)
        self.assertEqual(body, {"partialSuccess": {"rejectedLogRecords": 1}})

    def test_unknown_path_still_200(self):
        status, _ = self.post("/v1/traces", {"resourceSpans": []})
        self.assertEqual(status, 200)

    def test_store_init_idempotent(self):
        listener.init_db(self.db)
        listener.init_db(self.db)
        status, _ = self.post("/v1/logs", logs_payload(log_record(session_id="sess-idem")))
        self.assertEqual(status, 200)
        db = sqlite3.connect(self.db)
        n = db.execute("SELECT COUNT(*) FROM otel_events "
                       "WHERE session_id='sess-idem'").fetchone()[0]
        mode = db.execute("PRAGMA journal_mode").fetchone()[0]   # issue #12
        db.close()
        self.assertEqual(n, 1)
        self.assertEqual(mode, "wal")


if __name__ == "__main__":
    unittest.main()
