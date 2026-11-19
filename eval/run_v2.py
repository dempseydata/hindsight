#!/usr/bin/env python3
"""Run the status-v2 eval (#73, #95): three consecutive rounds of every case
through the pinned model, M1–M6 per case, each Superseded fact's hit rate.

Usage: eval/run_v2.py PROMPT_FILE TAG [MODEL]   (outputs in local-data/eval/runs/TAG/rN/)
MODEL overrides the pin for a comparison run; ACCEPT counts only on the pin.
The case's ledger plus ADR headers is appended as JSON. ACCEPT needs every
case passing in all three rounds (15 calls).
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "eval"))
sys.path.insert(0, str(REPO / "cli"))
import analyze  # noqa: E402  the restricted call: no tools, no repo cwd
from score import hit_rates, ledger_prompt, parse, score_v2  # noqa: E402

CASES = json.loads((REPO / "eval" / "status_v2_cases.json").read_text())
ROUNDS = 3


def run_case(prompt, cid, out_dir, model):
    case = CASES["cases"][cid]
    sent = {k: case[k] for k in ("project", "as_of", "stages", "runs", "adrs")}
    text = analyze.default_model_runner(ledger_prompt(prompt, sent), model) or ""
    (out_dir / f"{cid}.json").write_text(text)
    try:
        out = parse(text)
        return (cid, out, *score_v2(case, out))
    except ValueError:
        return cid, {}, {"pass": False, "error": "not JSON"}, [text[:200]]


def main():
    prompt, tag = Path(sys.argv[1]).read_text(), sys.argv[2]
    assert CASES["model"] == analyze.MODEL, (CASES["model"], analyze.MODEL)  # the pin the call uses
    model = sys.argv[3] if len(sys.argv) > 3 else analyze.MODEL
    outs, passed = {cid: [] for cid in CASES["cases"]}, 0
    for n in range(1, ROUNDS + 1):
        out_dir = REPO / "local-data" / "eval" / "runs" / tag / f"r{n}"
        out_dir.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(5) as ex:
            results = list(ex.map(lambda c: run_case(prompt, c, out_dir, model), CASES["cases"]))
        for cid, out, s, detail in results:
            print(f"== r{n} {cid}"); print("\n".join(detail))
            print("SCORE", " ".join(f"{k}={v}" for k, v in s.items()))
            outs[cid].append(out); passed += bool(s.get("pass"))
    for cid, case in CASES["cases"].items():
        if rates := hit_rates(case, outs[cid]):
            print("SUPERSEDED", cid, " ".join(f"{k}={v}" for k, v in rates.items()))
    total = ROUNDS * len(CASES["cases"])
    print(f"TOTAL {tag} model={model} cases_passed={passed}/{total}"
          f" -> {'ACCEPT' if passed == total else 'REJECT'}")


if __name__ == "__main__":
    main()
