"""Throwaway: is there a mechanical "recurring dead end" (issue #22)?

python3 prototype/dead_end.py            # score D1/D2/D3, write the candidate sheet
python3 prototype/dead_end.py show <session-prefix> [<thing>]   # tail of a session for judging

Read-only over local-data/hindsight.db and the raw transcripts that still
exist (command text is not stored; see the kill criterion on #22).
Code dies on this branch; the answer is on #22.
"""
import json
import os
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
from analyze import DEFAULT_DB  # noqa: E402

PROJECTS = ("hindsight-old", "career-ops", "hindsight-new", "content", "thisisme")
WRITES = {"Write", "Edit", "NotebookEdit", "MultiEdit", "Artifact"}
OUTCOME_CLI = {"git", "gh"}
READ_BUILTINS = {"Read", "Grep", "Glob", "ToolSearch", "TodoWrite", "AskUserQuestion",
                 "WebSearch", "WebFetch", "ListAgents", "TaskOutput", "TaskStop", "Bash",
                 "ScheduleWakeup", "ReportFindings", "SendMessage", "Monitor", "ListMcpResourcesTool",
                 "ReadMcpResourceTool", "EnterPlanMode", "ExitPlanMode", "SendUserFile"}
PLANNING = re.compile(r"wayfinder|grilling|grill-with-docs|grill-me|to-tickets|to-spec")
COMMIT_RE = re.compile(r"\bgit\s+(-\S+\s+)*commit\b")
GH_WRITE_RE = re.compile(r"\bgh\s+(issue|pr)\s+(create|comment|close|edit|reopen|merge)\b|\bgh\s+api\s+(--method\s+(POST|PATCH|PUT)|-X\s*(POST|PATCH|PUT))")
BASH_WRITE_RE = re.compile(r"(?<![<>])>(?!>?\s*/dev/null)|<<|\btee\b|\bsed\s+-i|\bcp\b|\bmv\b|\bmkdir\b|\btouch\b|\bpython3?\s+\S+\.py")
SHEET = Path("local-data/analysis/prototype/dead-end-candidates.tsv")
EXTRACTS = Path("local-data/analysis/extracts")


def thing_of(name, ctype, consumer):
    """The 'thing' a call belongs to, or None when it is not a thing worth
    dead-ending on (reads, writes, the outcome programs, shell builtins)."""
    if name in WRITES or name in READ_BUILTINS:
        return None
    if ctype == "skill":
        return "skill:" + consumer
    if ctype == "mcp":
        return "mcp:" + consumer
    if ctype == "cli":
        return None if consumer in OUTCOME_CLI else "cli:" + consumer
    if name == "Agent":
        return "builtin:Agent"
    return None


def load(conn):
    """session -> ordered event list; each event: at, name, ctype, consumer, err, tool_use_id."""
    sess = {}
    for sid, project, path in conn.execute(
            "SELECT s.id, s.project, s.transcript_path FROM sessions s "
            "WHERE s.project IN (%s) AND EXISTS (SELECT 1 FROM usage u WHERE u.session_id=s.id)"
            % ",".join("?" * len(PROJECTS)), PROJECTS):
        sess[sid] = {"project": project, "path": path, "events": [], "grains": []}
    for sid, at, name, ct, c, err, tu in conn.execute(
            "SELECT session_id, at, name, COALESCE(consumer_type,''), COALESCE(consumer,''), is_error, tool_use_id "
            "FROM tool_events ORDER BY at"):
        if sid in sess:
            sess[sid]["events"].append({"at": at or "", "name": name, "ctype": ct, "consumer": c,
                                        "err": err, "tu": tu, "thing": thing_of(name, ct, c)})
    for sid, cmd, at in conn.execute("SELECT session_id, command, at FROM command_grains ORDER BY at"):
        if sid in sess:
            sess[sid]["grains"].append({"at": at or "", "cmd": cmd})
    return sess


def raw_bash(path):
    """tool_use_id -> command for every Bash call in a raw transcript."""
    out = {}
    if not os.path.exists(path):
        return None
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            m = r.get("message") or {}
            if not isinstance(m.get("content"), list):
                continue
            for b in m["content"]:
                if b.get("type") == "tool_use" and b.get("name") == "Bash":
                    out[b.get("id")] = (b.get("input") or {}).get("command") or ""
    return out


def outcomes(s, raw):
    """Sorted list of (at, kind) outcome events for a session.
    stored kinds: write, git, gh.  raw kinds add: commit, ghwrite, bashwrite."""
    out = []
    for e in s["events"]:
        if e["name"] in WRITES:
            out.append((e["at"], "write"))
        elif e["consumer"] in OUTCOME_CLI:
            out.append((e["at"], e["consumer"]))
        if raw is not None and e["name"] == "Bash":
            cmd = raw.get(e["tu"], "")
            if COMMIT_RE.search(cmd):
                out.append((e["at"], "commit"))
            if GH_WRITE_RE.search(cmd):
                out.append((e["at"], "ghwrite"))
            if BASH_WRITE_RE.search(cmd):
                out.append((e["at"], "bashwrite"))
    return sorted(out)


def d1(sess, raws):
    """Orphaned invocation: a thing's last call followed by no outcome."""
    rows = []
    for sid, s in sess.items():
        doing = [e for e in s["events"] if e["thing"] or e["name"] in WRITES or e["name"] == "Bash"]
        if not doing:
            continue  # pure Q&A, excluded
        raw = raws.get(sid)
        outs = outcomes(s, raw)
        stored_outs = [(a, k) for a, k in outs if k in ("write", "git", "gh")]
        raw_outs = [(a, k) for a, k in outs if k in ("write", "commit", "ghwrite", "bashwrite")]
        last = {}
        for e in s["events"]:
            if e["thing"]:
                last[e["thing"]] = e["at"]
        for g in s["grains"]:
            if not re.match(r"/(clear|compact|model)$", g["cmd"]):
                last["cmd:" + g["cmd"]] = max(last.get("cmd:" + g["cmd"], ""), g["at"])
        for thing, at in last.items():
            stored_flag = not any(a > at for a, _ in stored_outs)
            raw_flag = (not any(a > at for a, _ in raw_outs)) if raw is not None else None
            if stored_flag or raw_flag:
                rows.append({"def": "D1", "project": s["project"], "session": sid, "thing": thing,
                             "at": at, "stored": int(stored_flag), "raw": raw_flag})
    return rows


def d2(sess):
    """Error burst then switch: >=3 consecutive errors on one consumer, never returns, another follows."""
    rows = []
    for sid, s in sess.items():
        ev = s["events"]
        i = 0
        while i < len(ev):
            key = (ev[i]["ctype"], ev[i]["consumer"])
            j = i
            while j < len(ev) and (ev[j]["ctype"], ev[j]["consumer"]) == key and ev[j]["err"] == 1:
                j += 1
            if j - i >= 3:
                rest = ev[j:]
                returns = any((e["ctype"], e["consumer"]) == key for e in rest)
                switched = any((e["ctype"], e["consumer"]) != key for e in rest)
                if not returns and switched:
                    rows.append({"def": "D2", "project": s["project"], "session": sid,
                                 "thing": ":".join(key), "at": ev[i]["at"], "burst": j - i,
                                 "stored": 1, "raw": None})
                i = j
            else:
                i += 1
    return rows


def d3(sess, raws):
    """Planning invocation with no ticket write and no write."""
    rows = []
    for sid, s in sess.items():
        plan = [g["cmd"] for g in s["grains"] if PLANNING.search(g["cmd"])] + \
               [e["consumer"] for e in s["events"] if e["ctype"] == "skill" and PLANNING.search(e["consumer"])]
        if not plan:
            continue
        outs = outcomes(s, raws.get(sid))
        kinds = {k for _, k in outs}
        stored_flag = not (kinds & {"write", "gh"})
        raw_flag = (not (kinds & {"write", "ghwrite", "bashwrite"})) if raws.get(sid) is not None else None
        if stored_flag or raw_flag:
            rows.append({"def": "D3", "project": s["project"], "session": sid, "thing": "plan:" + plan[0],
                         "at": "", "stored": int(stored_flag), "raw": raw_flag})
    return rows


def recurrence(rows, flavour):
    c = Counter()
    for r in rows:
        if r[flavour] or r[flavour] is None and flavour == "raw" and False:
            c[(r["project"], r["thing"])] += 1
    return c


def report(rows, label, flavour):
    hits = [r for r in rows if r[flavour]]
    rec = Counter((r["project"], r["thing"]) for r in hits)
    n_sessions = len({r["session"] for r in hits})
    print(f"\n== {label} [{flavour}]: {len(hits)} instances in {n_sessions} sessions; "
          f"{sum(1 for v in rec.values() if v >= 3)} (project, thing) at >=3 sessions")
    for (p, t), n in rec.most_common(12):
        print(f"   {n:3d}  {p:14s} {t}")


def show(sess, sid_prefix, thing=None, tail=25):
    sid = next(s for s in sess if s.startswith(sid_prefix))
    s = sess[sid]
    print(f"# {sid} {s['project']}  events={len(s['events'])} grains={[g['cmd'] for g in s['grains']]}")
    raw = raw_bash(s["path"])
    seq = []
    for e in s["events"]:
        lab = e["thing"] or e["name"]
        if e["name"] == "Bash" and raw:
            lab += " " + (raw.get(e["tu"], "")[:70].replace("\n", " "))
        seq.append((e["at"], ("!" if e["err"] else " ") + lab))
    for g in s["grains"]:
        seq.append((g["at"], "CMD " + g["cmd"]))
    seq.sort()
    # collapse runs of identical labels
    out, prev, n = [], None, 0
    for at, lab in seq:
        key = lab.split(" ")[0]
        if key == prev:
            n += 1
            continue
        if prev:
            out[-1] = out[-1] + (f" x{n}" if n > 1 else "")
        out.append(f"{at[11:19]} {lab}")
        prev, n = key, 1
    if prev:
        out[-1] = out[-1] + (f" x{n}" if n > 1 else "")
    start = 0
    if thing:
        idx = [i for i, l in enumerate(out) if thing in l]
        start = max(0, (idx[-1] if idx else 0) - 6)
    for l in out[start:start + tail + 6]:
        print("  ", l)
    print(f"   ... {len(out)} steps total")
    # assistant/user text after the thing's last call, from the raw transcript
    if os.path.exists(s["path"]):
        last_at = ""
        if thing:
            for e in s["events"]:
                if (e["thing"] or "") == thing:
                    last_at = e["at"]
            for g in s["grains"]:
                if "cmd:" + g["cmd"] == thing or thing.startswith("plan:"):
                    last_at = max(last_at, g["at"])
        texts = []
        with open(s["path"]) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if (r.get("timestamp") or "") < last_at or r.get("type") not in ("user", "assistant"):
                    continue
                m = r.get("message") or {}
                c = m.get("content")
                if isinstance(c, str):
                    t = c
                else:
                    t = " ".join(b.get("text", "") for b in (c or []) if isinstance(b, dict) and b.get("type") == "text")
                t = re.sub(r"\s+", " ", t).strip()
                if t and not t.startswith("<"):
                    texts.append((r["type"][0].upper(), t[:220]))
        print(f"   -- text after {last_at[11:19] or 'start'} ({len(texts)} turns):")
        for role, t in texts[:14]:
            print(f"   {role}: {t}")
        if len(texts) > 14:
            print(f"   ... and {len(texts) - 14} more; last: {texts[-1][0]}: {texts[-1][1]}")


def main():
    conn = sqlite3.connect(DEFAULT_DB)
    sess = load(conn)
    if sys.argv[1:2] == ["show"]:
        show(sess, sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        return
    raws = {sid: raw_bash(s["path"]) for sid, s in sess.items()}
    raws = {k: v for k, v in raws.items() if v is not None}
    print(f"sessions={len(sess)} raw-present={len(raws)} "
          f"doing={sum(1 for s in sess.values() if any(e['thing'] or e['name'] in WRITES or e['name']=='Bash' for e in s['events']))}")
    r1, r2, r3 = d1(sess, raws), d2(sess), d3(sess, raws)
    report(r1, "D1 orphaned invocation", "stored")
    report(r1, "D1 orphaned invocation", "raw")
    report(r2, "D2 error burst then switch", "stored")
    report(r3, "D3 planning, no ticket write", "stored")
    report(r3, "D3 planning, no ticket write", "raw")
    with open(SHEET, "w") as f:
        f.write("def\tproject\tsession\tthing\tat\tstored\traw\tlabel\tnote\n")
        for r in r1 + r2 + r3:
            f.write("\t".join(str(r.get(k, "")) for k in ("def", "project", "session", "thing", "at", "stored", "raw")) + "\t\t\n")
    print(f"\nsheet: {SHEET} ({len(r1)+len(r2)+len(r3)} rows)")
    random.seed(22)
    flagged = {r["session"] for r in r1 + r2 + r3 if r["stored"] or r["raw"]}
    unflagged = sorted(set(sess) - flagged)
    print(f"unflagged sessions: {len(unflagged)}; recall sample of 10: "
          + " ".join(x[:8] for x in random.sample(unflagged, min(10, len(unflagged)))))


if __name__ == "__main__" and sys.argv[1:2] != ["probe"]:
    main()


def probe(sess):
    """The one revision (D1-v2): a *deliverable-level* reading — a written path
    later moved to a discard folder, or written in one session and never
    touched again by any later session of the project. Counts only."""
    conn = sqlite3.connect(DEFAULT_DB)
    moves = Counter()
    for sid, s in sess.items():
        raw = raw_bash(s["path"])
        for cmd in (raw or {}).values():
            if re.search(r"\b(mv|git\s+mv)\b.*\b(discard|scrapped|archive|graveyard)", cmd, re.I):
                moves[s["project"]] += 1
    print("\n== probe: moves into a discard-like folder (raw Bash), per project:", dict(moves))
    for p in PROJECTS:
        rows = conn.execute("""
            SELECT t.file_path, COUNT(DISTINCT t.session_id) sess, MAX(s.date) last
            FROM tool_events t JOIN sessions s ON s.id=t.session_id
            WHERE s.project=? AND t.name IN ('Write','Edit') AND t.file_path IS NOT NULL
              AND t.file_path NOT LIKE '/private/tmp/%' AND t.file_path NOT LIKE '/tmp/%'
            GROUP BY 1""", (p,)).fetchall()
        once = [r for r in rows if r[1] == 1]
        print(f"   {p:14s} written paths={len(rows):4d}  touched in one session only={len(once):4d} ({len(once)/max(1,len(rows)):.0%})")


if __name__ == "__main__" and sys.argv[1:2] == ["probe"]:
    probe(load(sqlite3.connect(DEFAULT_DB)))
