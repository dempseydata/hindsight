#!/usr/bin/env python3
"""`/hindsight:ops` — install, control and serve (ADR-0036). Stdlib only.

Usage: hindsight.py install [--from <v1 db>]   write both launchd jobs against
                                                <home>/current; --from moves a v1
                                                database into Hindsight home, once
       hindsight.py uninstall                  remove both jobs and current; the
                                                database stays
       hindsight.py start | stop               the ingest listener
       hindsight.py serve                      the views server, detached
       hindsight.py open                       the what view, serving first if needed

The plists run the interpreter this ran under against <home>/current/cli/...,
so launchd never runs code from the versioned plugin cache. Never edits
~/.claude/settings.json; it prints what to remove there.
"""
import json
import os
import plistlib
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from home import INGEST, NIGHTLY, domain, home

ROOT = Path(__file__).resolve().parent.parent   # the plugin root
NIGHTLY_HOUR = 3
SERVE_PORT = 8321


def plist_path(label):
    return Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"


def launchctl(*args, check=False):
    return subprocess.run(["launchctl", *args], capture_output=not check, check=check)


def bootout(label):
    launchctl("bootout", f"{domain()}/{label}")


def bootstrap(label):
    launchctl("bootstrap", domain(), str(plist_path(label)), check=True)


def plists():
    h = home()
    script = h / "current" / "cli"
    # Baked at install: launchd's default PATH lacks `claude`, and the jobs
    # must see the same zone, home, raw limit and cache directory as the installing
    # shell (an unbaked HINDSIGHT_RAW_DAYS would compact at the default 90 days).
    env = {k: os.environ[k] for k in ("HINDSIGHT_HOME", "HINDSIGHT_TZ", "HINDSIGHT_RAW_DAYS",
                                      "CLAUDE_PLUGIN_DATA")
           if os.environ.get(k)}
    return {
        INGEST: {"Label": INGEST,
                 "ProgramArguments": [sys.executable, str(script / "listener.py"), "--log"],
                 "EnvironmentVariables": {k: v for k, v in env.items() if k == "HINDSIGHT_HOME"},  # the db path
                 "RunAtLoad": True, "KeepAlive": True},
        NIGHTLY: {"Label": NIGHTLY,
                  "ProgramArguments": [sys.executable, str(script / "analyze.py"), "--log"],
                  "EnvironmentVariables": {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), **env},
                  "StartCalendarInterval": {"Hour": NIGHTLY_HOUR, "Minute": 0}},
    }


def v1_hook_entries():
    """(event, command) for every settings.json hook still pointing at v1's
    build/hook.py. Read-only; an unreadable file has none to report."""
    try:
        hooks = json.loads((Path.home() / ".claude" / "settings.json").read_text()).get("hooks", {})
    except (OSError, ValueError, AttributeError):
        return []
    return [(event, h.get("command", ""))
            for event, groups in hooks.items() for g in groups for h in g.get("hooks", [])
            if "/build/hook.py" in h.get("command", "")]


def install(from_path=None):
    h = home()
    db = h / "hindsight.db"
    if from_path:
        src = Path(from_path).expanduser()
        if db.exists():
            print(f"refused: a database is already at {db}; nothing moved")
            return 1
        if not src.is_file():
            print(f"refused: no database at {src}")
            return 1
        for label in (INGEST, NIGHTLY):   # nothing may hold the database while it moves
            bootout(label)
        h.mkdir(parents=True, exist_ok=True)
        for suffix in ("", "-wal", "-shm"):   # WAL mode: the sidecars carry committed rows
            if Path(f"{src}{suffix}").exists():
                shutil.move(f"{src}{suffix}", f"{db}{suffix}")
        print(f"moved {src} to {db}")
    logs = h / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    h.chmod(0o700)   # the store is transcripts: owner-only, whatever the umask
    v1_logs = Path.home() / "Library" / "Logs" / "hindsight"
    for f in sorted(v1_logs.glob("*.log")):   # v1's log history moves once, never over a newer log
        if not (logs / f.name).exists():
            shutil.move(str(f), logs / f.name)
    current = h / "current"
    if current.is_symlink() or current.exists():
        current.unlink()
    current.symlink_to(ROOT)
    for label, body in plists().items():
        p = plist_path(label)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(plistlib.dumps(body))
        bootout(label)
        bootstrap(label)
    print(f"installed {INGEST} (listener on :4318) and {NIGHTLY} (daily at "
          f"{NIGHTLY_HOUR:02d}:00), running {sys.executable} against {current} -> {ROOT}")
    entries = v1_hook_entries()
    if entries:
        print("Remove these v1 hook entries from ~/.claude/settings.json by hand;"
              " the plugin registers its own:")
        for event, cmd in entries:
            print(f"  {event}: {cmd}")
    print("If SwiftBar runs hindsight.30s.sh, delete it: the menu bar is retired.")
    if not os.environ.get("CLAUDE_PLUGIN_DATA"):
        print("warning: CLAUDE_PLUGIN_DATA is unset, so the nightly caches extracts under"
              f" {current}/local-data, which a plugin update sweeps. Install through /hindsight:ops.")
    return 0


def uninstall():
    for label in (INGEST, NIGHTLY):
        bootout(label)
        plist_path(label).unlink(missing_ok=True)
    current = home() / "current"
    if current.is_symlink():
        current.unlink()
    print(f"removed {INGEST}, {NIGHTLY} and {current}. The database is kept;"
          f" to delete it and the logs: rm -rf {home()}")
    return 0


def start():
    if not plist_path(INGEST).exists():
        print("not installed — run `/hindsight:ops install`")
        return 1
    bootout(INGEST)   # so a crash-looping job restarts cleanly
    bootstrap(INGEST)
    print(f"started {INGEST}")
    return 0


def stop():
    bootout(INGEST)   # KeepAlive: a killed process would be back in seconds
    print(f"stopped {INGEST}")
    return 0


def http_up(port, path):
    """Any HTTP answer means the socket is served; a refused connection does not."""
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=2).close()
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def serve_log():
    return home() / "logs" / "serve.log"


def serve():
    """serve.py detached — still on-demand (ADR-0001): no plist, gone at logout.
    None when a server already answers on the port."""
    if http_up(SERVE_PORT, "/"):
        print(f"views server already running on http://127.0.0.1:{SERVE_PORT}/what")
        return None
    log = serve_log()
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "ab") as f:
        p = subprocess.Popen([sys.executable, str(ROOT / "cli" / "serve.py"),
                              "--port", str(SERVE_PORT)],
                             stdin=subprocess.DEVNULL, stdout=f, stderr=f,
                             start_new_session=True)
    print(f"views server starting on http://127.0.0.1:{SERVE_PORT}/what, log {log}")
    return p


def open_view():
    url = f"http://127.0.0.1:{SERVE_PORT}/what"
    if not http_up(SERVE_PORT, "/"):
        p = serve()
        for _ in range(40):   # shortcut: a fixed 10 s start budget, raise it if a cold start ever needs more
            if http_up(SERVE_PORT, "/"):
                break
            if p.poll() is not None:
                print(f"the views server exited; see {serve_log()}")
                return 1
            time.sleep(0.25)
    subprocess.run(["open", url])
    return 0


def main(argv):
    cmd, rest = (argv[0], argv[1:]) if argv else (None, [])
    if cmd == "install" and rest[:1] == ["--from"] and len(rest) == 2:
        return install(rest[1])
    if cmd in ("install", "uninstall", "start", "stop") and not rest:
        return globals()[cmd]()
    if cmd == "serve" and not rest:
        serve()
        return 0
    if cmd == "open" and not rest:
        return open_view()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
