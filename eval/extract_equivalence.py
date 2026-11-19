#!/usr/bin/env python3
"""The what-pass input equivalence check (issue #79, ticket #91): for every
session with a parent transcript on disk, the extract and piece map built
from its raw records equal the ones built from the file, byte for byte.

Local only, over real data: it opens the store read-only, builds both sides
in a temporary directory that is deleted on exit, and prints counts and the
ids of any session that differs, never session content. Commit nothing it
produces.

The file side reads the transcript's first high-water bytes, the prefix the
records claim to hold; a transcript that grew since its last capture is
compared on what was captured.

Usage: eval/extract_equivalence.py [--db PATH]     exit 1 if any differ
"""
import argparse
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "cli"))
import analyze  # noqa: E402


def built(tmp, side, sid, data):
    d = Path(tmp) / side
    d.mkdir(exist_ok=True)
    try:
        analyze.run_extract(data, d / sid)
    except analyze.ExtractionFailed:
        return "failed"  # v1 failed on the same bytes too: equal if both do
    return {p.name.removeprefix(sid): p.read_bytes() for p in d.glob(f"{sid}.*")}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(analyze.DEFAULT_DB))
    db = ap.parse_args(argv).db
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    compared, differ = 0, []
    try:
        for sid, path, hw in conn.execute(
                "SELECT session_id, path, high_water FROM transcripts"
                " WHERE agent_id IS NULL AND high_water > 0 ORDER BY session_id").fetchall():
            if not Path(path).is_file():
                continue
            with open(path, "rb") as f:
                on_disk = f.read(hw)
            with tempfile.TemporaryDirectory() as tmp:
                compared += 1
                if (built(tmp, "raw", sid, analyze.parent_lines(conn, sid))
                        != built(tmp, "file", sid, on_disk)):
                    differ.append(sid)
    finally:
        conn.close()
    print(f"compared {compared} session(s): {compared - len(differ)} equal,"
          f" {len(differ)} differ")
    for sid in differ:
        print(f"  differs: {sid}")
    return 1 if differ else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
