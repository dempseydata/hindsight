#!/usr/bin/env python3
"""Score haiku extraction outputs: evidence integrity via normalised substring matching.

Usage: score.py OUTPUT.json EXTRACT.txt [EXTRACT2.txt ...]
"""
import json
import re
import sys
from pathlib import Path


def norm(s):
    return re.sub(r"\s+", " ", s.lower()).strip()


def main():
    out_path = Path(sys.argv[1])
    corpus = norm(" ".join(Path(p).read_text() for p in sys.argv[2:]))
    raw = out_path.read_text().strip()
    raw = re.sub(r"^```(json)?\s*|\s*```$", "", raw)
    findings = json.loads(raw)

    total = passed = 0
    print(f"== {out_path.name}: {len(findings)} changes reported ==")
    for f in findings:
        marks = []
        for q in f.get("evidence", []):
            total += 1
            ok = norm(q) in corpus
            passed += ok
            marks.append("PASS" if ok else "FAIL")
        print(f"[{'/'.join(marks) or 'no evidence'}] {f.get('change')}")
        print(f"    why: {f.get('why')}")
        for q, m in zip(f.get("evidence", []), marks):
            if m == "FAIL":
                print(f"    FAILED QUOTE: {q[:120]}")
    if total:
        print(f"evidence: {passed}/{total} = {100*passed/total:.0f}%")
    else:
        print("evidence: none quoted")


if __name__ == "__main__":
    main()
