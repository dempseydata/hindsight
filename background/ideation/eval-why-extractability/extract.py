#!/usr/bin/env python3
"""Extract conversational text from a Claude Code session .jsonl for the why-extractability eval.

Keeps user text and assistant text blocks; drops tool results and meta lines;
keeps Edit/Write targets as one-line markers. Chunks output to fit a model context.

Usage: extract.py SESSION.jsonl OUTDIR/PREFIX
Writes PREFIX.part1.txt, PREFIX.part2.txt, ...
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
    pieces = []
    for line in src.open():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        for role, text in msg_texts(entry):
            text = text.strip()
            if not text or text.startswith("<command-name>") or text.startswith("<local-command"):
                continue
            if len(text) > PER_MSG_CAP:
                text = text[:PER_MSG_CAP] + " [...truncated]"
            pieces.append(f"{role}: {text}")

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


if __name__ == "__main__":
    main()
