#!/usr/bin/env python3
"""Indexed extractor — the ADR-0002 extract format.

Keeps user text and assistant text blocks; drops tool results and meta lines;
keeps Edit/Write targets as one-line markers. Every piece is numbered
`[n] ROLE: text`, sequentially per session, continuous across chunk parts.
Writes a sidecar map piece-index -> source jsonl message uuid.

Usage: extract.py SESSION.jsonl OUTDIR/PREFIX
Writes PREFIX.part1.txt, ... and PREFIX.map.json
"""
import json
import sys
from pathlib import Path

PER_MSG_CAP = 1500
CHUNK_CAP = 180_000  # chars per output file, ~45k tokens

FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def msg_texts(entry):
    t = entry.get("type")
    msg = entry.get("message") or {}
    content = msg.get("content")
    if t == "user":
        if entry.get("isMeta"):
            return
        if isinstance(content, str):
            yield "USER", content
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    yield "USER", item.get("text", "")
    elif t == "assistant":
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text":
                    yield "ASSISTANT", item.get("text", "")
                elif item.get("type") == "tool_use" and item.get("name") in FILE_TOOLS:
                    fp = (item.get("input") or {}).get("file_path", "?")
                    yield "TOOL", f"[{item['name']}: {fp}]"


def main():
    src, prefix = Path(sys.argv[1]), sys.argv[2]
    pieces, index_map, n = [], {}, 0
    for line in src.open():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        for role, text in msg_texts(entry):
            text = text.strip()
            # `<command-` covers name/message/args: a slash-command message
            # leads with whichever of them the client emitted first, so a
            # single-tag check (ticket #66) let <command-message>-leading
            # messages through. Same rule ticket #61's parse uses.
            if not text or text.startswith("<command-") or text.startswith("<local-command"):
                continue
            if len(text) > PER_MSG_CAP:
                text = text[:PER_MSG_CAP] + " [...truncated]"
            n += 1
            pieces.append(f"[{n}] {role}: {text}")
            index_map[n] = {"uuid": entry.get("uuid"), "role": role}

    chunks, cur, cur_len = [], [], 0
    for p in pieces:
        if cur_len + len(p) > CHUNK_CAP and cur:
            chunks.append("\n\n".join(cur))
            cur, cur_len = [], 0
        cur.append(p)
        cur_len += len(p) + 2
    if cur:
        chunks.append("\n\n".join(cur))

    for i, chunk in enumerate(chunks, 1):
        out = Path(f"{prefix}.part{i}.txt")
        out.write_text(chunk)
        print(f"{out}  {len(chunk)} chars")
    Path(f"{prefix}.map.json").write_text(json.dumps(index_map))


if __name__ == "__main__":
    main()
