#!/usr/bin/env python3
"""Score one status-narrative output against a frozen case (ADR-0012, ticket #67).

Output contract (the narrative pass must emit exactly this):
    {"Built": [str, ...], "Reversed": [str, ...], "Now": [str, ...]}

Per case:
  recall     expected facts whose anchor appears in a line of the RIGHT group
  misplaced  expected facts found only in another group
  forbidden  lines containing a forbidden anchor (post-snapshot or invented)
  untraced   lines sharing fewer than TRACE_WORDS content words with the ledger
  undated    lines without a date inside the ledger span
  now_ok     a Now line names the current stage and its start date
  bounded    group sizes within BOUNDS and no group missing

Usage: score.py cases.json CASE_ID OUTPUT.json   → prints detail + a SCORE line
       score.py --selfcheck
"""
import json
import re
import sys
from pathlib import Path

BOUNDS = {"Built": 8, "Reversed": 4, "Now": 3}
TRACE_WORDS = 2          # content words a line must share with the ledger
MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()
_MON = (r"((?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
        r"|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b\.?)")  # not 'decisions' 
STOP = set("the and with for from into over that this then than was were has have "
           "been being are its via per not but also under after before while".split())


def norm(s):
    return re.sub(r"\s+", " ", str(s).lower()).strip()


def words(s):
    return {w for w in re.findall(r"[a-z][a-z0-9\-]{3,}", norm(s)) if w not in STOP}


def dates_in(line):
    """Day-of-year ints for every 'Aug 20', '20 Aug', '08-20' or '2026-08-20' in line."""
    t = norm(line)
    out = []
    for m, d in re.findall(r"\b" + _MON + r" (\d{1,2})\b", t):
        out.append((MONTHS.index(m[:3]) + 1, int(d)))
    for d, m in re.findall(r"\b(\d{1,2}) " + _MON, t):
        out.append((MONTHS.index(m[:3]) + 1, int(d)))
    for m, d in re.findall(r"\b(?:\d{4}-)?(0[1-9]|1[0-2])-(\d{2})\b", t):
        out.append((int(m), int(d)))  # MM-DD only — '#18-19' is a ticket range, not a date
    return out


def md(iso):
    return (int(iso[5:7]), int(iso[8:10]))


def ledger_prompt(prompt, ledger):
    """The exact model input — one assembly shared by the eval runner and
    the live pass, so the eval scores what production sends."""
    return prompt + "\n\n" + json.dumps(ledger, indent=1)


def parse(raw):
    """Model output → dict, tolerating a ```json fence."""
    return json.loads(re.sub(r"^```(json)?\s*|\s*```$", "", raw.strip()))


def groups_of(out):
    """The three bounded groups, normalised. A group that is missing, null or
    not a list reads as empty here so a malformed shape can be *judged*
    rather than raise (ticket #77) — `bounded` is what then rejects it. The
    common invited shape is {"Reversed": null} for "nothing reversed"; the
    contract says [], and null is off-contract, not a synonym."""
    groups = {}
    for g in BOUNDS:
        v = out.get(g)
        groups[g] = [norm(l) for l in v] if isinstance(v, list) else []
    return groups


def score(case, out):
    runs = case["runs"]
    groups = groups_of(out)
    lines = [(g, l) for g in BOUNDS for l in groups[g]]
    detail = []

    hit = misplaced = 0
    for f in case["expected"]:
        anchors = [norm(a) for a in f["anchors"]]
        where = {g for g, l in lines if any(a in l for a in anchors)}
        if f["group"] in where:
            hit += 1; detail.append(f"HIT       {f['group']:8} {f['id']} {f['name']}")
        elif where:
            misplaced += 1; detail.append(f"MISPLACED {f['group']:8} {f['id']} {f['name']} -> {sorted(where)}")
        else:
            detail.append(f"MISS      {f['group']:8} {f['id']} {f['name']}")

    forb = [norm(a) for a in case.get("forbidden", [])]
    forbidden = 0
    for g, l in lines:
        if any(a in l for a in forb):
            forbidden += 1; detail.append(f"FORBIDDEN {g}: {l}")
    c, cdetail = contract(runs, out)
    detail += cdetail
    untraced, undated, now_ok, bounded = c["untraced"], c["undated"], c["now_ok"], c["bounded"]

    n = len(case["expected"])
    ok = (hit >= n * case.get("recall_floor", RECALL_FLOOR) - 1e-9 and forbidden == 0
          and untraced == 0 and undated == 0 and now_ok and bounded)
    return {"recall": f"{hit}/{n}", "misplaced": misplaced, "forbidden": forbidden,
            "untraced": untraced, "undated": undated, "now_ok": now_ok,
            "bounded": bounded, "lines": len(lines), "pass": ok}, detail


RECALL_FLOOR = 0.8


def contract(runs, out):
    """The ground-truth-free floors M3–M6 — the write-time gate the narrative
    pass runs against the live ledger (ADR-0012; same functions as the eval,
    no second implementation). -> ({untraced, undated, now_ok, bounded, ok}, detail)"""
    ledger_words = words(" ".join(r["stage"] + " " + " ".join(r["titles"]) for r in runs))
    span = (md(runs[0]["start"]), md(runs[-1]["end"]))
    groups = groups_of(out)
    lines = [(g, l) for g in BOUNDS for l in groups[g]]
    detail, untraced, undated = [], 0, 0
    for g, l in lines:
        if len(words(l) & ledger_words) < TRACE_WORDS:
            untraced += 1; detail.append(f"UNTRACED  {g}: {l}")
        ds = dates_in(l)
        if not ds or not all(span[0] <= d <= span[1] for d in ds):
            undated += 1; detail.append(f"UNDATED   {g}: {l}")
    cur = runs[-1]
    now_ok = any(norm(cur["stage"]) in l and md(cur["start"]) in dates_in(l) for l in groups["Now"])
    bounded = all(isinstance(out.get(g), list) and len(out[g]) <= n
                  for g, n in BOUNDS.items()) \
        and bool(groups["Built"]) and bool(groups["Now"])
    ok = untraced == 0 and undated == 0 and now_ok and bounded
    return {"untraced": untraced, "undated": undated, "now_ok": now_ok,
            "bounded": bounded, "ok": ok}, detail


def main():
    if sys.argv[1:] == ["--selfcheck"]:
        case = {"runs": [{"stage": "Plan", "start": "2026-08-01", "end": "2026-08-16",
                          "titles": ["Locked extraction contract via grilling"]},
                         {"stage": "Build", "start": "2026-08-16", "end": "2026-08-20",
                          "titles": ["Ship OTLP listener and wire telemetry"]}],
                "expected": [{"id": "B1", "name": "listener", "group": "Built", "anchors": ["listener"]},
                             {"id": "R1", "name": "contract", "group": "Reversed", "anchors": ["contract"]}],
                "forbidden": ["how-view"]}
        good = {"Built": ["OTLP listener shipped, telemetry wired — Aug 16–20"],
                "Reversed": ["Extraction contract locked (Aug 1)"],  # wrong group on purpose? no: expected says Reversed
                "Now": ["Build, since Aug 16: OTLP listener"]}
        s, _ = score(case, good)
        assert s["pass"] and s["recall"] == "2/2" and s["now_ok"], s
        bad = {"Built": ["Locked the contract (Aug 3)", "How-view greybox (Aug 27)", "Sunshine (Aug 5)"],
               "Reversed": [], "Now": ["Plan, since Aug 1"]}
        s, d = score(case, bad)
        assert not s["pass"] and s["misplaced"] == 1 and s["forbidden"] == 1 and s["untraced"] >= 1 \
            and s["undated"] >= 1 and not s["now_ok"], (s, d)
        # ticket #77: a null or non-list group is judged off-contract, never raised
        for shape in ({"Built": good["Built"], "Reversed": None, "Now": good["Now"]},
                      {"Built": "one line", "Reversed": [], "Now": good["Now"]},
                      {"Built": good["Built"], "Now": good["Now"]}):
            c, _ = contract(case["runs"], shape)
            assert not c["bounded"] and not c["ok"], (shape, c)
        assert dates_in("4 decisions, aug 1–16") == [(8, 1)], dates_in("4 decisions, aug 1–16")
        assert dates_in("August 20 and 3 Sept.") == [(8, 20), (9, 3)]
        assert dates_in("tickets (#18-19), 2026-08-20") == [(8, 20)]
        print("selfcheck ok"); return
    cases = json.loads(Path(sys.argv[1]).read_text())
    case = cases["cases"][sys.argv[2]]
    s, detail = score(case, parse(Path(sys.argv[3]).read_text()))
    print("\n".join(detail))
    print("SCORE", sys.argv[2], " ".join(f"{k}={v}" for k, v in s.items()))


if __name__ == "__main__":
    main()
