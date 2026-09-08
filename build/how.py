"""The how-view data pipeline (ticket #63) — everything below rendering.

Per ADR-0010: the process trail is a mechanical date-ordered merge of
command grains, skill invocations and file writes for one workspace
project, with audit titles supplying the prose. Per ADR-0011: the process
declaration is a strict hand-parsed YAML subset at line 1 of the project's
`.claude/my-process.md`, three states (absent / invalid / valid), whole
declaration rejected on any fault. The checker is deliberately dumb —
presence, first/last-seen per stage, off-script list — no order rules, no
verdicts.

Output of how_data() (the greybox ticket consumes it directly):
  declaration: {state, error, stages}   error = "line N: reason" when invalid
  trail:       [{at, session_id, kind, name, stage}]  date order;
               kind command|skill|write; stage None when unbucketed
  summary:     [{name, count, first_seen, last_seen}] per declared stage,
               in stated order; count 0 = "nothing observed"
  off_script:  [{kind, name, count, first_seen, last_seen}] first-seen order
  boundaries:  {name: count}  unbucketed session boundaries set aside from
               off-script (ticket #70) — stated in the off-script total,
               never silently dropped
  sessions:    {session_id: {date, title}}  title = audit title or None
  runs:        [{stage, start, end, titles}]  the run ledger (ticket #64):
               phase runs in date order, empty unless the declaration is
               valid — the sole input to the status narrative (ADR-0012).
               start/end are local days (ADR-0014); trail `at` stays UTC
  run_detail:  [{sessions, events, names, minor}]  parallel to runs — what
               the view shows per run beyond the ledger (ticket #65);
               kept apart so the ledger's content hash stays the narrative's
               key
"""
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from analyze import (DEFAULT_PROJECTS_DIR, MODEL, SKILL, STATUS_VERSION,
                     audit_title, local_day)
from extract import FILE_TOOLS

# commands and skills are one name pool seen through two capture paths
# (ADR-0011): /implement typed is a grain, Skill(implement) is a tool event,
# and either is evidence of the stage that declares the name in either list
NAME_KEYS = ("commands", "skills")
MARKER_KEYS = NAME_KEYS + ("paths",)
MIN_RUN = 3  # a shorter band of one stage folds into the run before it (#64)
# ticket #70: session boundaries — Claude Code's own /clear and /model, and
# wayfinder as the house pipeline's session front door — open sessions, they
# don't mark process steps. Applied only to events no stage claimed, so a
# declaration that lists wayfinder under a stage still wins.
SESSION_BOUNDARIES = ("clear", "model", "wayfinder")


class DeclarationInvalid(Exception):
    pass


def match_name(marker, stored):
    """ADR-0011: bare marker = whole tail segment after the last colon;
    qualified marker = exact. Case-sensitive, no globs."""
    if ":" in marker:
        return marker == stored
    return marker == stored or stored.endswith(":" + marker)


def is_boundary(e):
    return e["kind"] == "command" and any(
        match_name(b, e["name"].lstrip("/")) for b in SESSION_BOUNDARIES)


def match_path(marker, rel):
    """Trailing slash = any write under that subtree; otherwise exact."""
    return rel.startswith(marker) if marker.endswith("/") else rel == marker


def _list(value, n):
    """Inline `[a, b]` list of bare scalars — the only list form allowed."""
    if not (value.startswith("[") and value.endswith("]")):
        raise DeclarationInvalid(f"line {n}: expected an inline list like [a, b]")
    inner = value[1:-1].strip()
    items = [i.strip() for i in inner.split(",")] if inner else []
    if any(not i or i[0] in "\"'[{" for i in items):
        raise DeclarationInvalid(f"line {n}: list items must be bare names")
    return items


def _parse(lines):
    """lines: (1-based number, text) of the fenced body. Grammar: `stages:`
    then `  - name: X` items, each with optional `    <marker>: [..]`.
    Ambiguity is rejected here: a name marker that would match another
    stage's marker (by match_name, so `grilling` vs `x:grilling` collide)
    or a path marker repeated across stages — the same marker in one
    stage's commands and skills is not ambiguous."""
    stages, cur, seen_names, seen_paths = [], None, [], {}
    for n, raw in lines:
        if not raw.strip():
            continue
        indent, line = len(raw) - len(raw.lstrip(" ")), raw.strip()
        if indent == 0:
            if line != "stages:":
                raise DeclarationInvalid(
                    f"line {n}: only a top-level `stages:` key is allowed")
            if stages or cur:
                raise DeclarationInvalid(f"line {n}: `stages:` declared twice")
            continue
        if line.startswith("- "):
            if cur:
                stages.append(cur)
            key, _, value = line[2:].partition(":")
            if key.strip() != "name" or not value.strip():
                raise DeclarationInvalid(
                    f"line {n}: a stage must start with `- name: <name>`")
            if value.strip() in (s["name"] for s in stages):
                raise DeclarationInvalid(
                    f"line {n}: duplicate stage name `{value.strip()}`")
            cur = {"name": value.strip()}
            continue
        if cur is None:
            raise DeclarationInvalid(
                f"line {n}: expected `stages:` then `- name:` items")
        key, sep, value = line.partition(":")
        key = key.strip()
        if not sep or key not in MARKER_KEYS:
            raise DeclarationInvalid(
                f"line {n}: unknown key `{key}` (allowed: {', '.join(MARKER_KEYS)})")
        if key in cur:
            raise DeclarationInvalid(f"line {n}: `{key}` given twice in `{cur['name']}`")
        cur[key] = _list(value.strip(), n)
        for m in cur[key]:
            if key == "paths":
                other = seen_paths.get(m)
                if other and other != cur["name"]:
                    raise DeclarationInvalid(
                        f"line {n}: path `{m}` declared in both `{other}` and `{cur['name']}`")
                seen_paths[m] = cur["name"]
            else:
                for prior, stage in seen_names:
                    if stage != cur["name"] and (match_name(m, prior) or match_name(prior, m)):
                        raise DeclarationInvalid(
                            f"line {n}: `{m}` in `{cur['name']}` collides with"
                            f" `{prior}` in `{stage}`")
                seen_names.append((m, cur["name"]))
    if cur:
        stages.append(cur)
    if not stages:
        raise DeclarationInvalid("line 1: no `stages:` list declared")
    for s in stages:
        for k in MARKER_KEYS:
            s.setdefault(k, [])
    return stages


def parse_declaration(text):
    """-> (state, stages, error). Absent = no `---` at line 1 (a fence
    elsewhere is prose). Invalid = fence present but body fails the subset;
    stages is then [] — no partial salvage."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return "absent", [], None
    try:
        close = next(i for i, l in enumerate(lines[1:], 1) if l.strip() == "---")
    except StopIteration:
        return "invalid", [], "line 1: unclosed frontmatter fence"
    try:
        return "valid", _parse(list(enumerate(lines[1:close], 2))), None
    except DeclarationInvalid as e:
        return "invalid", [], str(e)


def read_declaration(root):
    """The one location ADR-0011 reads. A missing file is absent; a file
    that exists but can't be read is invalid — nothing hides."""
    path = Path(root) / ".claude" / "my-process.md"
    try:
        text = path.read_text()
    except FileNotFoundError:
        return "absent", [], None
    except OSError as e:
        return "invalid", [], f"line 0: cannot read {path.name}: {e.strerror}"
    return parse_declaration(text)


def stage_for(stages, kind, name):
    """Stage name owning this event, or None (off-script). Grain names carry
    their leading slash verbatim (#62) — stripped here. Nested path
    subtrees: longest matching prefix wins (ADR-0011 amendment)."""
    if kind == "write":
        best = max(((len(m), s["name"]) for s in stages for m in s["paths"]
                    if match_path(m, name)), default=None)
        return best[1] if best else None
    stored = name.lstrip("/") if kind == "command" else name
    for s in stages:
        if any(match_name(m, stored) for k in NAME_KEYS for m in s[k]):
            return s["name"]
    return None


def _events(conn, project, root):
    """The raw trail: grains, skill calls and first-touch writes under the
    project root, date-ordered.
    ponytail: project scoping is a path-prefix match on projects_dir/<name>,
    the same ceiling adr_count carries — a project whose name is a mangled
    transcript dirname outside the workspace contributes no writes."""
    prefix = str(root) + "/"
    marks = ", ".join("?" * len(FILE_TOOLS))
    # writes: one event per (session, file) — the first touch; a file edited
    # forty times in a session is one step on the trail, not forty
    rows = [{"at": at, "session_id": sid, "kind": kind,
             "name": name[len(prefix):] if kind == "write" else name}
            for kind, sid, at, name in conn.execute(f"""
        SELECT 'command', g.session_id, g.at, g.command FROM command_grains g
          JOIN sessions s ON s.id = g.session_id WHERE s.project = ?
        UNION ALL
        SELECT 'skill', t.session_id, t.at, t.consumer FROM tool_events t
          JOIN sessions s ON s.id = t.session_id
          WHERE s.project = ? AND t.consumer_type = '{SKILL}'
        UNION ALL
        SELECT 'write', t.session_id, MIN(t.at), t.file_path FROM tool_events t
          JOIN sessions s ON s.id = t.session_id
          WHERE s.project = ? AND t.name IN ({marks})
            AND substr(t.file_path, 1, ?) = ?
          GROUP BY t.session_id, t.file_path""",
                (project, project, project, *sorted(FILE_TOOLS), len(prefix), prefix))]
    rows.sort(key=lambda r: (r["at"] or "", r["kind"], r["name"]))
    return rows


def _agg(rows, key):
    out = {}
    for r in rows:
        a = out.setdefault(key(r), {"count": 0, "first_seen": r["at"], "last_seen": r["at"]})
        a["count"] += 1
        a["last_seen"] = r["at"]
    return out


def used_names(events):
    """Distinct command/skill names in first-seen order, slash stripped."""
    return list(dict.fromkeys(e["name"].lstrip("/") for e in events if e["kind"] != "write"))


def run_ledger(trail, sessions, detail=False):
    """Phase runs over the bucketed trail (ticket #64, CONTEXT "Phase run"):
    consecutive same-stage events form a run; a band shorter than MIN_RUN
    folds into the preceding run (the first band always opens one). A
    session straddling runs is titled only in the run holding most of its
    events (ties to the newest). Dates are day-granular; a run's titles
    are its majority sessions' audit titles, in order of first appearance.
    detail=True returns (ledger, run_detail) — see the module docstring."""
    bands, cur = [], None
    for e in trail:
        # no stage, no band; no timestamp, no date — a run's start/end is a
        # day, and an undated event cannot supply one. It stays in the trail,
        # the aggregates and the off-script list; only the band skips it.
        if not e["stage"] or not e["at"]:
            continue
        if cur and cur[0] == e["stage"]:
            cur[1].append(e)
        else:
            cur = (e["stage"], [e]); bands.append(cur)
    runs = []
    for stage, es in bands:
        if runs and (len(es) < MIN_RUN or runs[-1]["stage"] == stage):
            runs[-1]["events"].extend(es)
        else:
            runs.append({"stage": stage, "events": list(es)})
    majority = {}  # session -> (count, run index); >= so a later run wins ties
    for i, r in enumerate(runs):
        per = {}
        for e in r["events"]:
            per[e["session_id"]] = per.get(e["session_id"], 0) + 1
        for sid, n in per.items():
            if n >= majority.get(sid, (0, -1))[0]:
                majority[sid] = (n, i)
    out = []
    for i, r in enumerate(runs):
        sids = list(dict.fromkeys(e["session_id"] for e in r["events"]))
        titles = [sessions[sid]["title"] for sid in sids
                  if majority[sid][1] == i and sid in sessions and sessions[sid]["title"]]
        out.append({"stage": r["stage"], "start": local_day(r["events"][0]["at"]),
                    "end": local_day(r["events"][-1]["at"]), "titles": titles})
    if not detail:
        return out
    extra = []  # sessions counted where titled (majority), events in full
    for i, r in enumerate(runs):
        extra.append({
            "sessions": sum(v[1] == i for v in majority.values()),
            "events": len(r["events"]),
            "names": used_names(r["events"]),
            "minor": dict(Counter(e["stage"] for e in r["events"] if e["stage"] != r["stage"]))})
    return out, extra


def ledger(d):
    """The run ledger as the narrative pass sees it (ADR-0012) — the exact
    object hashed into `status_narrative.ledger_hash`, so the view can tell
    a stale row from a current one."""
    return {"project": d["project"], "as_of": d["runs"][-1]["end"],
            "stages": [s["name"] for s in d["declaration"]["stages"]],
            "runs": d["runs"]}


def ledger_hash(d):
    """Over the ledger's content, never the project's name: a rename re-keys
    the stored row (ADR-0018) and the narrative must survive it without a
    model call, so the name — part of the prompt, not of the runs — stays
    out of the staleness key."""
    content = {k: v for k, v in ledger(d).items() if k != "project"}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def narrative(conn, project, d):
    """The status-narrative read (ticket #81), beside ledger_hash so the
    writer gate (analyze.refresh_narratives) and this reader share the same
    regeneration key triple: stale when (ledger_hash, prompt_version, model)
    no longer matches what the next run would write (ADR-0012 amendment).
    None when nothing is stored; never stale without runs to compare to."""
    row = conn.execute(
        "SELECT narrative, ledger_hash, generated_at, model, prompt_version"
        " FROM status_narrative WHERE project = ?", (project,)).fetchone()
    if row is None:
        return None
    facts, h, at, model, pv = row
    stale = bool(d["runs"]) and (h, pv, model) != (
        ledger_hash(d), STATUS_VERSION, MODEL)
    return {"facts": json.loads(facts), "written_day": local_day(at),
            "model": model, "stale": stale}


def how_data(conn, project, projects_dir=DEFAULT_PROJECTS_DIR):
    """The how-view blob for one project — see the module docstring for
    the shape. Declaration state drives the checker: without a valid
    declaration every event is unbucketed and summary/off_script are empty
    (the raw ungrouped trail, ADR-0010's degradation)."""
    root = Path(projects_dir) / project
    state, stages, error = read_declaration(root)
    trail = _events(conn, project, root)
    for e in trail:
        e["stage"] = stage_for(stages, e["kind"], e["name"]) if stages else None
    by_stage = _agg([e for e in trail if e["stage"]], lambda e: e["stage"])
    loose = [e for e in trail if not e["stage"]]
    off = _agg([e for e in loose if not is_boundary(e)], lambda e: (e["kind"], e["name"]))
    bounds = Counter(e["name"] for e in loose if is_boundary(e))
    sessions = {}
    for sid, date, md in conn.execute(
            "SELECT s.id, s.date, a.markdown FROM sessions s"
            " LEFT JOIN audit a ON a.session_id = s.id AND a.skip = 0"
            " WHERE s.project = ?", (project,)):
        sessions[sid] = {"date": date, "title": audit_title(md)}
    runs, detail = (run_ledger(trail, sessions, detail=True)
                    if state == "valid" else ([], []))
    return {
        "project": project,
        "declaration": {"state": state, "error": error, "stages": stages},
        "trail": trail,
        "summary": [{"name": s["name"], **by_stage.get(
            s["name"], {"count": 0, "first_seen": None, "last_seen": None})}
            for s in stages],
        "off_script": [{"kind": k, "name": n, **a} for (k, n), a in off.items()]
                      if stages else [],
        "boundaries": dict(bounds) if stages else {},
        "sessions": sessions,
        "runs": runs,
        "run_detail": detail,
    }


if __name__ == "__main__":  # real-data smoke: python3 how.py [project]
    import json
    import sys

    from analyze import DEFAULT_DB
    conn = sqlite3.connect(f"file:{DEFAULT_DB}?mode=ro", uri=True)
    d = how_data(conn, sys.argv[1] if len(sys.argv) > 1 else "hindsight")
    print(json.dumps({k: v for k, v in d.items() if k not in ("trail", "sessions")}, indent=1))
    print(len(d["trail"]), "trail events")
