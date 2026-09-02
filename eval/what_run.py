#!/usr/bin/env python3
"""Run the what-pass regression set (ticket #79): every frozen extract through
the pinned model with PROMPT_FILE, scored by the production gate.

Usage: eval/what_run.py PROMPT_FILE TAG        (outputs in local-data/eval/what/runs/TAG/)

Floors, all required for ACCEPT: every output passes valid_entry; an expected
SKIP stays SKIP and an expected entry stays an entry ("any" cases only need
to pass the gate). Scoring is the gate itself — no judge.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "build"))
import analyze  # noqa: E402

CASES = json.loads((REPO / "eval" / "what_cases.json").read_text())
EXTRACTS = REPO / "local-data" / "eval" / "what" / "extracts"


def verdict(text):
    if not text or not analyze.valid_entry(text):
        return "invalid"
    return "SKIP" if analyze.strip_fences(text).startswith("SKIP") else "entry"


def run_case(template, cid, out_dir):
    text = analyze.default_model_runner(
        analyze.what_prompt((EXTRACTS / f"{cid}.txt").read_text(), template)) or ""
    (out_dir / f"{cid}.md").write_text(text)
    got, want = verdict(text), CASES["cases"][cid]["expected"]
    ok = got != "invalid" and want in ("any", got)
    return cid, want, got, ok, " ".join(text.split())[:80]


def main():
    template, tag = Path(sys.argv[1]).read_text(), sys.argv[2]
    out_dir = REPO / "local-data" / "eval" / "what" / "runs" / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(lambda c: run_case(template, c, out_dir), CASES["cases"]))
    passed = 0
    for cid, want, got, ok, head in results:
        print(f"{'PASS' if ok else 'FAIL'} {cid[:8]}.{cid.split('.')[1]:6} want={want:5} got={got:7} {head!r}")
        passed += ok
    print(f"TOTAL {tag} model={analyze.MODEL} cases_passed={passed}/{len(results)}"
          f" -> {'ACCEPT' if passed == len(results) else 'REJECT'}")


if __name__ == "__main__":
    main()
