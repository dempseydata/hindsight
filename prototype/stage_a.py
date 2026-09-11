"""Throwaway: the three v1 Stage A signals on a real window (issue #19).

python3 prototype/stage_a.py <project>[,<project>...] <end-day> [--days N] [--json]

Comma-joined projects are pooled as one lineage (a probe only — ADR-0018
says a fork is a new project; the pooling here is to see what it shows).
Window W = the N local days ending on <end-day>; baseline P = the N days
before W; baseline H = all history before W. Everything is read-only over
local-data/hindsight.db. Code dies on this branch; the answer is on #19.
"""
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
from analyze import DEFAULT_DB, apply_tz, day_sql, local_day  # noqa: E402
from how import _agg, how_data, is_boundary  # noqa: E402

KINDS = ("input", "output", "cache_creation", "cache_read")
MIN_CALLS = 10          # a consumer under this many calls in W is noise, not a pattern
ERR_FLOOR = 0.10        # v2: no consumer-week on this machine exceeds 0.21; 0.10 is the top 7% of cells
COST_SHARE = 0.25       # a consumer invoked by this share of the window's API responses is a cost fact
COST_LIFT = 0.30        # per-active-day work tokens moved by more than this vs baseline
MIN_BASE_DAYS = 5       # a baseline thinner than this is not a baseline
MIN_WRITES = 3          # newly off-script writes under one top-level path
EVIDENCE = 5            # pointers listed per pattern


def days(end, n):
    return [(end - timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]


def in_win(col, lo, hi):
    """SQL predicate for local day of col in [lo, hi]; hi None = open-ended low side."""
    d = day_sql(col)
    return f"{d} >= '{lo}' AND {d} <= '{hi}'" if lo else f"{d} <= '{hi}'"


def consumers(conn, projects, lo, hi):
    """Per consumer in the window: calls, errors, unknown, sessions, sample
    pointers; and message-lens tokens by kind (the #42 join contract)."""
    ph = ",".join("?" * len(projects))
    out = {}
    for ty, c, n, e, nu, sess, tus, mids in conn.execute(f"""
            SELECT COALESCE(t.consumer_type,''), COALESCE(t.consumer,''),
                   COUNT(*), COALESCE(SUM(t.is_error),0), SUM(t.is_error IS NULL),
                   GROUP_CONCAT(DISTINCT t.session_id),
                   GROUP_CONCAT(CASE WHEN t.is_error=1 THEN t.tool_use_id END),
                   GROUP_CONCAT(DISTINCT t.message_id)
            FROM tool_events t JOIN sessions s ON s.id = t.session_id
            WHERE s.project IN ({ph}) AND {in_win('t.at', lo, hi)}
            GROUP BY 1, 2""", projects):
        out[(ty, c)] = {"calls": n, "err": e, "unknown": nu,
                        "sessions": (sess or "").split(","),
                        "err_tool_use_ids": [x for x in (tus or "").split(",") if x][:EVIDENCE],
                        "message_ids": [x for x in (mids or "").split(",") if x][:EVIDENCE],
                        "tokens": dict.fromkeys(KINDS, 0)}
    for ty, c, i, o, cc, cr in conn.execute(f"""
            SELECT g.consumer_type, g.consumer, SUM(u.input_tokens), SUM(u.output_tokens),
                   SUM(u.cache_creation_input_tokens), SUM(u.cache_read_input_tokens)
            FROM (SELECT DISTINCT t.consumer_type, t.consumer, t.message_id
                  FROM tool_events t JOIN sessions s ON s.id = t.session_id
                  WHERE s.project IN ({ph}) AND t.consumer_type IS NOT NULL
                    AND t.message_id IS NOT NULL AND {in_win('t.at', lo, hi)}) g
            JOIN usage u ON u.message_id = g.message_id
            GROUP BY 1, 2""", projects):
        if (ty, c) in out:
            out[(ty, c)]["tokens"] = dict(zip(KINDS, (i, o, cc, cr)))
    return out


def usage_totals(conn, projects, lo, hi):
    ph = ",".join("?" * len(projects))
    i, o, cc, cr, nsess, ndays = conn.execute(f"""
        SELECT COALESCE(SUM(u.input_tokens),0), COALESCE(SUM(u.output_tokens),0),
               COALESCE(SUM(u.cache_creation_input_tokens),0),
               COALESCE(SUM(u.cache_read_input_tokens),0),
               COUNT(DISTINCT u.session_id), COUNT(DISTINCT {day_sql('u.at')})
        FROM usage u JOIN sessions s ON s.id = u.session_id
        WHERE s.project IN ({ph}) AND {in_win('u.at', lo, hi)}""", projects).fetchone()
    return {"tokens": dict(zip(KINDS, (i, o, cc, cr))), "sessions": nsess, "active_days": ndays}


def sunk(conn, projects):
    """A level, not a trend: sunk_cost has no history column."""
    ph = ",".join("?" * len(projects))
    rows = conn.execute(f"SELECT category, COALESCE(plugin,''), name, tokens FROM sunk_cost"
                        f" WHERE project IN ({ph}) OR project IS NULL", projects).fetchall()
    return {"total": sum(r[3] for r in rows), "items": len(rows),
            "by_category": dict(Counter({r[0]: 0 for r in rows}) + Counter())}


def config_changes(conn, projects, lo, hi):
    """change_events touching the sunk-cost surface in the window — the
    only history the sunk cost has (the silent-change backstop, ADR-0006)."""
    like = " OR ".join("path LIKE ?" for _ in projects)
    rows = conn.execute(f"""
        SELECT observed_at, source, path FROM change_events
        WHERE {in_win('observed_at', lo, hi)}
          AND (source != 'project-git' OR {like})
        ORDER BY observed_at""", [f"{p}/%" for p in projects]).fetchall()
    return [{"at": local_day(a), "source": s, "path": p} for a, s, p in rows]


def off_script(conn, projects, lo, hi, cache):
    """The how-view's off-script aggregate restricted to a day window,
    computed from how_data's trail (stage None, not a boundary)."""
    agg = Counter()
    firsts, sess = {}, defaultdict(set)
    for p in projects:
        if p not in cache:
            cache[p] = how_data(conn, p)
        d = cache[p]
        if d["declaration"]["state"] != "valid":
            continue
        for e in d["trail"]:
            day = local_day(e["at"])
            if (lo and day < lo) or day > hi or e["stage"] or is_boundary(e):
                continue
            k = (e["kind"], e["name"])
            agg[k] += 1
            firsts.setdefault(k, day)
            sess[k].add(e["session_id"])
    return {k: {"count": n, "first_seen": firsts[k], "sessions": sorted(sess[k])}
            for k, n in agg.items()}


def share(tokens):
    return sum(tokens.values())


def daily_work(conn, projects, lo, hi):
    """Work tokens (output + cache_creation) per active day — cache_read is
    the context re-read and dwarfs everything, so it is stated apart."""
    ph = ",".join("?" * len(projects))
    return [w for (w,) in conn.execute(f"""
        SELECT SUM(u.output_tokens + u.cache_creation_input_tokens)
        FROM usage u JOIN sessions s ON s.id = u.session_id
        WHERE s.project IN ({ph}) AND {in_win('u.at', lo, hi)}
        GROUP BY {day_sql('u.at')}""", projects)]


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else 0


def run(projects, end, n):
    apply_tz()
    conn = sqlite3.connect(f"file:{DEFAULT_DB}?mode=ro", uri=True)
    W = days(end, n)
    P = days(end - timedelta(days=n), n)
    wlo, whi, plo, phi = W[0], W[-1], P[0], P[-1]
    hhi = (date.fromisoformat(wlo) - timedelta(days=1)).isoformat()
    patterns = []
    report = {"projects": projects, "window": [wlo, whi], "preceding": [plo, phi],
              "history_to": hhi}

    # ---- signal 2 first: the window's size decides whether anything else reads
    tw, tp, th = (usage_totals(conn, projects, *w) for w in ((wlo, whi), (plo, phi), (None, hhi)))
    report["usage"] = {"W": tw, "P": tp, "H": th}
    if tw["sessions"] == 0:
        report["patterns"] = []
        report["nothing_to_report"] = "no sessions with usage in the window"
        return report
    cost_rows = []
    for name, base, lo, hi in (("preceding", tp, plo, phi), ("history", th, None, hhi)):
        if base["active_days"] < MIN_BASE_DAYS:
            report.setdefault("no_baseline", []).append(f"{name} ({base['active_days']} active days)")
            continue
        wd, bd = daily_work(conn, projects, wlo, whi), daily_work(conn, projects, lo, hi)
        row = {"baseline": name, "active_days": [tw["active_days"], base["active_days"]],
               "sessions": [tw["sessions"], base["sessions"]],
               "work_per_day_mean": [round(sum(wd) / len(wd)), round(sum(bd) / len(bd))],
               "work_per_day_median": [median(wd), median(bd)],
               "cache_read_per_day": [round(tw["tokens"]["cache_read"] / tw["active_days"]),
                                      round(base["tokens"]["cache_read"] / base["active_days"])]}
        row["lift_mean"] = round(row["work_per_day_mean"][0] / row["work_per_day_mean"][1] - 1, 2)
        row["lift_median"] = round(row["work_per_day_median"][0] / row["work_per_day_median"][1] - 1, 2)
        cost_rows.append(row)
    if any(abs(r["lift_median"]) >= COST_LIFT for r in cost_rows):
        patterns.append({"signal": "cost-trend", "rows": cost_rows,
                         "evidence": {"window_days": tw["active_days"]}})
    report["cost_rows"] = cost_rows
    report["sunk_cost"] = sunk(conn, projects)
    report["config_changes_in_W"] = config_changes(conn, projects, wlo, whi)

    # ---- signal 1: consumers
    cw, cp, ch = (consumers(conn, projects, *w) for w in ((wlo, whi), (plo, phi), (None, hhi)))
    tot_w = share(tw["tokens"]) or 1
    rows, cons_rows = [], []
    for k, v in sorted(cw.items(), key=lambda kv: -kv[1]["calls"]):
        known = v["calls"] - v["unknown"]
        es = v["err"] / known if known else None
        base = cp.get(k) or ch.get(k)
        bname = "preceding" if k in cp else ("history" if k in ch else None)
        bes = None
        if base:
            bk = base["calls"] - base["unknown"]
            bes = base["err"] / bk if bk else None
        row = {"consumer": "/".join(k), "calls": v["calls"], "unknown": v["unknown"],
               "err_share": None if es is None else round(es, 3),
               "sessions": len(v["sessions"]),
               "msg_tokens": share(v["tokens"]), "token_share": round(share(v["tokens"]) / tot_w, 3),
               "tokens_per_call": round(share(v["tokens"]) / v["calls"]),
               "baseline": bname, "baseline_err_share": None if bes is None else round(bes, 3),
               "baseline_calls": base["calls"] if base else 0}
        rows.append(row)
        if v["calls"] >= MIN_CALLS and ((es is not None and es >= ERR_FLOOR)
                                        or row["token_share"] >= COST_SHARE):
            cons_rows.append({**row, "why": "error-share" if es and es >= ERR_FLOOR else "cost-share",
                              "evidence": {"sessions": v["sessions"][:EVIDENCE],
                                           "tool_use_ids": v["err_tool_use_ids"],
                                           "message_ids": v["message_ids"]}})
    if cons_rows:
        patterns.append({"signal": "consumer", "rows": cons_rows})
    report["consumers"] = rows

    # ---- signal 3: declared/actual drift
    cache = {}
    ow, op, oh = (off_script(conn, projects, *w, cache) for w in ((wlo, whi), (plo, phi), (None, hhi)))
    report["declaration"] = {p: cache[p]["declaration"]["state"] for p in projects}
    drift, new_names, new_dirs = [], [], defaultdict(lambda: {"count": 0, "sessions": set(), "files": []})
    for k, v in sorted(ow.items(), key=lambda kv: -kv[1]["count"]):
        prev = op.get(k, {}).get("count", 0)
        ever = oh.get(k, {}).get("count", 0)
        new = ever == 0 and prev == 0
        drift.append({"name": f"{k[0]}:{k[1]}", "W": v["count"], "P": prev, "H": ever,
                      "new": new, "sessions": v["sessions"][:EVIDENCE]})
        if not new:
            continue
        if k[0] == "write":
            top = k[1].split("/")[0] + ("/" if "/" in k[1] else "")
            g = new_dirs[top]
            g["count"] += v["count"]; g["sessions"].update(v["sessions"]); g["files"].append(k[1])
        else:
            new_names.append({"name": f"{k[0]}:{k[1]}", "count": v["count"],
                              "first_seen": v["first_seen"], "sessions": v["sessions"][:EVIDENCE]})
    new_dirs = [{"path": t, "writes": g["count"], "files": len(g["files"]),
                 "sessions": sorted(g["sessions"])[:EVIDENCE]}
                for t, g in new_dirs.items() if g["count"] >= MIN_WRITES]
    trail_w = sum(1 for p in projects for e in cache[p]["trail"] if wlo <= local_day(e["at"]) <= whi)
    trail_p = sum(1 for p in projects for e in cache[p]["trail"] if plo <= local_day(e["at"]) <= phi)
    report["off_script"] = {"W_total": sum(v["count"] for v in ow.values()), "W_trail": trail_w,
                            "P_total": sum(v["count"] for v in op.values()), "P_trail": trail_p,
                            "rows": drift}
    if new_names or new_dirs:
        patterns.append({"signal": "declared-actual-drift",
                         "off_script_share": [round(report["off_script"]["W_total"] / trail_w, 3) if trail_w else None,
                                              round(report["off_script"]["P_total"] / trail_p, 3) if trail_p else None],
                         "new_names": new_names, "new_write_paths": new_dirs})
    report["patterns"] = patterns
    if not patterns:
        report["nothing_to_report"] = "window has activity; nothing above the floor"
    return report


def show(r):
    print(f"\n=== {','.join(r['projects'])}  W {r['window'][0]}..{r['window'][1]}"
          f"  P {r['preceding'][0]}..{r['preceding'][1]}  H ..{r['history_to']}")
    u = r["usage"]
    for k in ("W", "P", "H"):
        t = u[k]
        print(f"  {k}: sessions={t['sessions']:3d} active_days={t['active_days']:3d} "
              f"total={share(t['tokens']):>12,}  " +
              " ".join(f"{kk}={t['tokens'][kk]:,}" for kk in KINDS))
    if r.get("nothing_to_report"):
        print(f"  NOTHING TO REPORT: {r['nothing_to_report']}")
    if "consumers" not in r:
        return
    if r.get("no_baseline"):
        print(f"  no baseline: {r['no_baseline']}")
    print(f"  sunk cost (level, no history): {r['sunk_cost']['total']:,} tokens over {r['sunk_cost']['items']} items;"
          f" config changes in W: {len(r['config_changes_in_W'])}")
    print("  consumers (calls>=%d shown):" % MIN_CALLS)
    for c in r["consumers"]:
        if c["calls"] < MIN_CALLS:
            continue
        print(f"    {c['consumer']:<28} calls={c['calls']:4d} err={c['err_share']} unk={c['unknown']:3d} "
              f"sess={c['sessions']:2d} tok_share={c['token_share']:.3f} tok/call={c['tokens_per_call']:>7,} "
              f"base={c['baseline']} base_err={c['baseline_err_share']} base_calls={c['baseline_calls']}")
    for c in r.get("cost_rows", []):
        print(f"  cost vs {c['baseline']:<9} work/day mean {c['work_per_day_mean'][0]:>10,} vs {c['work_per_day_mean'][1]:>10,} ({c['lift_mean']:+.2f})"
              f"  median {c['work_per_day_median'][0]:>10,} vs {c['work_per_day_median'][1]:>10,} ({c['lift_median']:+.2f})"
              f"  days {c['active_days']} sessions {c['sessions']}")
    o = r['off_script']
    print(f"  declaration: {r['declaration']}  off-script W={o['W_total']}/{o['W_trail']} P={o['P_total']}/{o['P_trail']}")
    for d in r["off_script"]["rows"][:12]:
        print(f"    {d['name']:<34} W={d['W']:3d} P={d['P']:3d} H={d['H']:3d} {'NEW' if d['new'] else ''}")
    print(f"  PATTERNS: {len(r['patterns'])}")
    for p in r["patterns"]:
        print("    " + json.dumps(p, separators=(",", ":"))[:700])


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 14
    rep = run(args[0].split(","), date.fromisoformat(args[1]), n)
    print(json.dumps(rep, indent=1) if "--json" in sys.argv else "", end="")
    show(rep)
