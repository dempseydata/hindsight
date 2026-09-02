#!/usr/bin/env python3
"""Run the status-narrative eval: every case through the pinned model, then score.

Usage: eval/run.py PROMPT_FILE TAG        (outputs in local-data/eval/runs/TAG/)
PROMPT_FILE is the narrative prompt; the case ledger is appended as JSON.
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "eval"))
from score import ledger_prompt, parse, score  # noqa: E402

CASES = json.loads((REPO / "eval" / "cases.json").read_text())


def run_case(prompt, model, cid, out_dir):
    case = CASES["cases"][cid]
    ledger = {k: case[k] for k in ("project", "as_of", "stages", "runs")}
    r = subprocess.run(["claude", "-p", "--model", model],
                       input=ledger_prompt(prompt, ledger),
                       capture_output=True, text=True, timeout=300)
    (out_dir / f"{cid}.json").write_text(r.stdout)
    try:
        return (cid, *score(case, parse(r.stdout)))
    except ValueError:
        return cid, {"pass": False, "error": "not JSON"}, [r.stdout[:200]]


def main():
    prompt, tag = Path(sys.argv[1]).read_text(), sys.argv[2]
    model = CASES["model"]
    out_dir = REPO / "local-data" / "eval" / "runs" / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(lambda c: run_case(prompt, model, c, out_dir), CASES["cases"]))
    passed = 0
    for cid, s, detail in results:
        print(f"== {cid}"); print("\n".join(detail))
        print("SCORE", " ".join(f"{k}={v}" for k, v in s.items()))
        passed += bool(s.get("pass"))
    print(f"TOTAL {tag} model={model} cases_passed={passed}/{len(results)}"
          f" -> {'ACCEPT' if passed == len(results) else 'REJECT'}")


if __name__ == "__main__":
    main()
