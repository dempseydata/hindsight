#!/usr/bin/env python3
"""Backfill history import (ticket #20) — the full-history backfill's cached
model outputs (local-data/backfill/) assembled into the store under their
original prompt version: import, not re-extraction, so 207 sessions of
history cost no second pass through subscription limits.

Each inventory session's status is re-derived from the cached files alone:
every extract part needs a non-empty what output, multi-part sessions
additionally the merged what. Complete sessions import as `done` with
what-v1 audit rows and the model recorded in the backfill's inventory;
incomplete or never-extracted sessions enter `sessions` as `pending` for the
ordinary analysis run to process fresh; sessions post-dating the snapshot
are not in the inventory and reach `sessions` through the ordinary sync.
The backfill's why outputs are no longer imported (ADR-0006, ticket #43) —
they stay cached on disk only.

Idempotent: session ids already present in `sessions` are never touched, so
re-running is a no-op and imported rows never clobber (or get clobbered by)
fresh analysis.

Usage: import_backfill.py [--db PATH] [--backfill-dir DIR]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze  # noqa: E402
from analyze import (DEFAULT_DB, init_db, insert_results,  # noqa: E402
                     part_files, strip_fences, valid_entry)

DEFAULT_BACKFILL = analyze.REPO / "local-data" / "backfill"
# The frozen v1 prompt the backfill ran: rows import under their original
# version so v1 history and v2 fresh analysis coexist legibly.
WHAT_VERSION = "what-v1"


def _cached(path):
    return path.exists() and path.stat().st_size > 0


def classify(bf, sid):
    """('done' | 'empty' | 'pending', parts) from the cached files alone.
    'pending' covers both never-extracted and incomplete (the backfill's
    'partial') sessions — fresh analysis re-extracts either way."""
    if not (bf / "extracts" / f"{sid}.map.json").exists():
        return "pending", []
    parts = part_files(bf / "extracts", sid)
    if not parts:
        return "empty", []
    ok = all(_cached(bf / "what" / f"{p.stem}.md") for p in parts)
    if len(parts) > 1:
        ok = ok and _cached(bf / "what" / f"{sid}.merged.md")
    return ("done" if ok else "pending"), parts


def import_backfill(db_path=DEFAULT_DB, backfill_dir=DEFAULT_BACKFILL):
    bf = Path(backfill_dir)
    inv = json.loads((bf / "inventory.json").read_text())
    model = inv["model"]
    conn = init_db(db_path)
    try:
        seen = {r[0] for r in conn.execute("SELECT id FROM sessions")}
        imported = 0
        statuses = {"done": 0, "empty": 0, "pending": 0, "already_present": 0}
        for s in inv["sessions"]:
            sid = s["id"]
            if sid in seen:
                statuses["already_present"] += 1  # never touched — idempotency
                continue
            status, parts = classify(bf, sid)
            md = None
            if status == "done":
                src = (bf / "what" / f"{sid}.merged.md" if len(parts) > 1
                       else bf / "what" / f"{parts[0].stem}.md")
                md = strip_fences(src.read_text()).strip()
                if not valid_entry(md):
                    status = "pending"  # cached refusal prose (ticket #38)
            statuses[status] += 1
            # ponytail: the inventory's date is the archive's UTC day, not
            # the local bucket ADR-0014 wants. Migration 5 heals any imported
            # session whose transcript survives; the rest keep an
            # off-by-up-to-one-day date. Re-derive here if this one-shot
            # historical import is ever run again on live transcripts.
            conn.execute(
                "INSERT INTO sessions (id, project, transcript_path, date, size, status)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (sid, s["project"], s["path"], s["date"], s["size"], status))
            if status != "done":
                continue
            insert_results(conn, s, md.startswith("SKIP"), md, WHAT_VERSION, model)
            imported += 1
        conn.commit()
        return {"imported": imported, "statuses": statuses}
    finally:
        conn.close()


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--backfill-dir", type=Path, default=DEFAULT_BACKFILL)
    args = ap.parse_args(argv)
    r = import_backfill(args.db, args.backfill_dir)
    print(f"imported {r['imported']} sessions"
          f" ({r['statuses']['pending']} left pending, {r['statuses']['empty']} empty,"
          f" {r['statuses']['already_present']} already present)")


if __name__ == "__main__":
    main(sys.argv[1:])
