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


def groups_of(out, names=BOUNDS):
    """The three bounded groups, normalised. A group that is missing, null or
    not a list reads as empty here so a malformed shape can be *judged*
    rather than raise (ticket #77) — `bounded` is what then rejects it. The
    common invited shape is {"Reversed": null} for "nothing reversed"; the
    contract says [], and null is off-contract, not a synonym."""
    groups = {}
    for g in names:
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


# --- status-v2 (ADR-0035, #73, #95): Standing / Superseded / Now over the
# run ledger plus the project's ADR headers. v1 above stays as the record.

BOUNDS_V2 = {"Standing": (3, 8), "Superseded": (0, 6), "Now": (1, 3)}
ADR_NUM = re.compile(r"\badr[- ]?0*(\d+)\b")


# ADR-0040: the closed verb list, as whole words in any tense. Here, not in
# cli/how.py, because the gate needs it and how imports analyze imports score.
STRONG = re.compile(r"\b(drop(s|ped|ping)?|kill(s|ed|ing)?|retir(e|es|ed|ing)|remov(e|es|ed|ing)"
                    r"|replac(e|es|ed|ing)|invert(s|ed|ing)?)\b", re.I)
CLOSE = re.compile(r"\bclos(e|es|ed|ing)\b", re.I)
FINISHED = re.compile(r"\b(tickets?|maps?|issues?|phases?)\b|#\d", re.I)
# ADR-0041: closing an inquiry is finished work too; "grill" is the operator's word for a decision session
INQUIRY = re.compile(r"\b(research|decisions?|questions?|grill(ed|ing)?)\b|\bclose-out\b", re.I)


def _finished_close(part):
    """ADR-0040/0041: a close on a ticket or an inquiry, or one naming no thing ("close it")."""
    return (FINISHED.search(part) or INQUIRY.search(part)
            or not {w for w in words(part) if not CLOSE.fullmatch(w)})


def title_changes(runs):
    """ADR-0040, amended by ADR-0041: every title part (split on ";" and ",")
    that states a change — drop/kill/retire/remove/replace/invert, or a close
    that is not finished work. Every one is mandatory under Superseded (M7).
    -> [{start, end, part}] in ledger order."""
    found = []
    for r in runs:
        for t in r["titles"]:
            for part in (p.strip() for p in re.split(r"[;,]", t)):
                if STRONG.search(part) or (CLOSE.search(part) and not _finished_close(part)):
                    found.append({"start": r["start"], "end": r["end"], "part": part})
    return found


def contract_v2(runs, adrs, out):
    """M3–M6, ground-truth-free — the status-v2 write-time gate (#96 imports
    this; no second implementation). M3: a line shares ≥ TRACE_WORDS content
    words with the ledger, or with ledger + ADR titles while naming an ADR
    number; every number it names is in the input. M4: every date is in the
    ledger span or an ADR's date — Standing/Now need one, Superseded two, in
    order (order binds Superseded only). M5: unchanged. M6: BOUNDS_V2, every group a list.
    -> ({untraced, undated, now_ok, bounded, ok}, detail)"""
    ledger_words = words(" ".join(r["stage"] + " " + " ".join(r["titles"]) for r in runs))
    adr_words = words(" ".join(a["title"] for a in adrs))
    numbers = {int(ADR_NUM.search(norm(a["number"]))[1]) for a in adrs}
    span = (md(runs[0]["start"]), md(runs[-1]["end"]))
    adr_days = {md(a["date"]) for a in adrs if a.get("date")}
    groups = groups_of(out, BOUNDS_V2)
    detail, untraced, undated = [], 0, 0
    for g in BOUNDS_V2:
        for l in groups[g]:
            named = {int(n) for n in ADR_NUM.findall(l)}
            w = words(l)
            if named - numbers or not (len(w & ledger_words) >= TRACE_WORDS or
                                       (named and len(w & (ledger_words | adr_words)) >= TRACE_WORDS)):
                untraced += 1; detail.append(f"UNTRACED  {g}: {l}")
            ds = dates_in(l)
            sup = g == "Superseded"
            if (len(ds) < (2 if sup else 1) or (sup and ds != sorted(ds))
                    or not all(span[0] <= d <= span[1] or d in adr_days for d in ds)):
                undated += 1; detail.append(f"UNDATED   {g}: {l}")
    unlisted = 0
    for c in title_changes(runs):
        w = words(c["part"])
        if not any(len(w & words(l)) >= min(TRACE_WORDS, len(w)) for l in groups["Superseded"]):
            unlisted += 1; detail.append(f"UNLISTED  {c['part']}")
    cur = runs[-1]
    now_ok = any(norm(cur["stage"]) in l and md(cur["start"]) in dates_in(l) for l in groups["Now"])
    bounded = all(isinstance(out.get(g), list) and lo <= len(out[g]) <= hi
                  for g, (lo, hi) in BOUNDS_V2.items())
    ok = untraced == 0 and undated == 0 and unlisted == 0 and now_ok and bounded
    return {"untraced": untraced, "undated": undated, "unlisted": unlisted, "now_ok": now_ok,
            "bounded": bounded, "ok": ok}, detail


def _hits(case, out):
    """Expected fact id -> the groups its anchors land in."""
    groups = groups_of(out, BOUNDS_V2)
    return {f["id"]: {g for g in BOUNDS_V2 for l in groups[g]
                      if any(norm(a) in l for a in f["anchors"])} for f in case["expected"]}


def score_v2(case, out):
    """M1–M6 for one case. M1: ≥ RECALL_FLOOR of facts in the right group
    and every Superseded fact. M2: lines hitting a forbidden anchor — a
    string anywhere, or {"anchor", "group"} only in that group (the empty
    anchor matches every line: that group must be [])."""
    groups = groups_of(out, BOUNDS_V2)
    where, detail = _hits(case, out), []
    hit = sup = 0
    for f in case["expected"]:
        if f["group"] in where[f["id"]]:
            hit += 1; sup += f["group"] == "Superseded"
            detail.append(f"HIT       {f['group']:10} {f['id']} {f['name']}")
        elif where[f["id"]]:
            detail.append(f"MISPLACED {f['group']:10} {f['id']} {f['name']} -> {sorted(where[f['id']])}")
        else:
            detail.append(f"MISS      {f['group']:10} {f['id']} {f['name']}")
    forbidden = 0
    for g in BOUNDS_V2:
        for l in groups[g]:
            for fb in case.get("forbidden", []):
                a, scope = (fb, g) if isinstance(fb, str) else (fb["anchor"], fb["group"])
                if scope == g and norm(a) in l:
                    forbidden += 1; detail.append(f"FORBIDDEN {g}: {l}"); break
    c, cdetail = contract_v2(case["runs"], case["adrs"], out)
    n = len(case["expected"])
    n_sup = sum(f["group"] == "Superseded" for f in case["expected"])
    ok = hit >= n * RECALL_FLOOR - 1e-9 and sup == n_sup and forbidden == 0 and c["ok"]
    return {"recall": f"{hit}/{n}", "superseded": f"{sup}/{n_sup}", "forbidden": forbidden,
            **{k: c[k] for k in ("untraced", "undated", "unlisted", "now_ok", "bounded")},
            "lines": sum(map(len, groups.values())), "pass": ok}, detail + cdetail


def hit_rates(case, outs):
    """Each expected Superseded fact's hit rate across runs (#73 §5)."""
    hits = [_hits(case, o) for o in outs]
    return {f["id"]: f"{sum('Superseded' in h[f['id']] for h in hits)}/{len(outs)}"
            for f in case["expected"] if f["group"] == "Superseded"}


def selfcheck_v2():
    """status-v2 floors (#73, #95): one rule per assertion."""
    runs = [{"stage": "Build", "start": "2026-09-08", "end": "2026-09-11",
             "titles": ["Implement presence history and renamed projects trail"]},
            {"stage": "Plan", "start": "2026-09-11", "end": "2026-09-16",
             "titles": ["Charting so-what view, prototype Stage A signals"]}]
    adrs = [{"number": "ADR-0005", "date": "2026-08-17", "title": "Hook self-instrumentation source and bounds",
             "status": "superseded by ADR-0033", "touches": ""},
            {"number": "ADR-0033", "date": "2026-11-15", "title": "Capture runs on Stop, one owning source",
             "status": "accepted", "touches": "Supersedes: ADR-0005"}]
    case = {"runs": runs, "adrs": adrs,
            "expected": [{"id": "S1", "name": "hook", "group": "Superseded", "anchors": ["self-instrument"]},
                         {"id": "T1", "name": "so-what", "group": "Standing", "anchors": ["so-what"]}],
            "forbidden": [{"anchor": "so-what", "group": "Superseded"}, "adr-0026"]}
    good = {"Standing": ["Presence history and renamed projects trail implemented (Sep 8)",
                         "Charting the so-what view, Stage A signals prototyped (Sep 11)",
                         "ADR-0033: capture runs on Stop, one owning source per field (Nov 15)"],
            "Superseded": ["Hook self-instrumentation source (Aug 17) → ADR-0033 capture on Stop (Nov 15)"],
            "Now": ["Plan, since Sep 11: charting the so-what view"]}
    base, d = score_v2(case, good)
    assert base["pass"] and base["recall"] == "2/2" and base["superseded"] == "1/1", (base, d)

    def fails(out, key, **kw):
        s, d = score_v2({**case, **kw}, out)
        assert not s["pass"] and s[key] != base[key], (key, s, d)

    swap = lambda g, lines: {**good, g: lines}
    fails(swap("Superseded", []), "superseded")                       # M1: 100% of Superseded
    fails(swap("Superseded", good["Superseded"] + ["The so-what view (Sep 11) → nothing (Sep 16)"]),
          "forbidden")                                                # M2: group-scoped
    s, _ = score_v2(case, swap("Standing", good["Standing"][:2] + ["Hook self-instrumentation so-what (Aug 17)"]))
    assert s["forbidden"] == 0, s                                     # ...and only in its group
    fails(good, "forbidden", forbidden=[{"anchor": "", "group": "Superseded"}])  # empty anchor: Superseded must be []
    fails(swap("Standing", good["Standing"][:2] + ["ADR-0023 capture runs on Stop (Nov 15)"]),
          "untraced")                                                 # M3: ADR number not in the input
    fails(swap("Standing", good["Standing"][:2] + ["Capture runs on Stop, owning source (Nov 15)"]),
          "untraced")                                                 # M3: ADR-only words need the number
    fails(swap("Superseded", ["Hook self-instrumentation source (Aug 17) → ADR-0033 capture on Stop"]),
          "undated")                                                  # M4: Superseded needs two dates
    fails(swap("Superseded", ["Hook self-instrumentation source (Nov 15) → ADR-0033 capture on Stop (Aug 17)"]),
          "undated")                                                  # M4: ...in order
    fails(swap("Standing", good["Standing"][:2] + ["ADR-0033: capture runs on Stop, one owning source (Oct 2)"]),
          "undated")                                                  # M4: not in span, not an ADR date
    s, _ = score_v2(case, swap("Standing", good["Standing"][:2] + ["Presence history (Sep 11) and renamed projects trail (Sep 8)"]))
    assert s["undated"] == 0, s                                       # ...order binds Superseded only
    fails(swap("Now", ["Build, since Sep 8: presence history trail"]), "now_ok")  # M5
    fails(swap("Standing", good["Standing"][:2]), "bounded")          # M6: Standing 3-8
    fails(swap("Now", []), "bounded")                                 # M6: Now 1-3
    fails({k: v for k, v in good.items() if k != "Superseded"}, "bounded")  # M6: all groups present
    killed = [{**runs[0], "titles": runs[0]["titles"] + ["killed the polling sync daemon"]}, runs[1]]
    fails(good, "unlisted", runs=killed)                              # M7: a strong change needs its line
    closed = [{**runs[0], "titles": runs[0]["titles"] + ["close the polling sync daemon"]}, runs[1]]
    fails(good, "unlisted", runs=closed)                              # ADR-0041: so does a close of a thing
    for t in ("close it", "Sync research closes", "Grilled and closed: sync cadence", "Sync close-out: docs"):
        assert not title_changes([{**runs[0], "titles": [t]}]), t     # ...but not finished work
    listed = swap("Superseded", good["Superseded"] + ["polling sync daemon (Sep 8) → killed the polling sync daemon (Sep 11)"])
    assert contract_v2(killed, adrs, listed)[0]["ok"], contract_v2(killed, adrs, listed)
    c, _ = contract_v2(runs, adrs, good)
    assert c["ok"], c                                                 # the write-time gate, no ground truth
    stub = {"Standing": [], "Superseded": [], "Now": []}
    assert not score_v2(case, stub)[0]["pass"]
    assert hit_rates(case, [good, swap("Superseded", []), good]) == {"S1": "2/3"}


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
        selfcheck_v2()
        print("selfcheck ok"); return
    cases = json.loads(Path(sys.argv[1]).read_text())
    case = cases["cases"][sys.argv[2]]
    s, detail = score(case, parse(Path(sys.argv[3]).read_text()))
    print("\n".join(detail))
    print("SCORE", sys.argv[2], " ".join(f"{k}={v}" for k, v in s.items()))


if __name__ == "__main__":
    main()
