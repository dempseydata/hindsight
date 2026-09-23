#!/usr/bin/env python3
"""Hindsight menu bar status — a SwiftBar plugin (issue #37, ADR-0001 amendment).

SwiftBar runs the wrapper `install` writes into its plugin folder every 30 s
(the interval is in the wrapper's name) and turns stdout into the icon and
its menu. Hindsight ships only this script; SwiftBar is the host process, as
launchd is for the nightly job. Stdlib only.

Usage:
  menubar.py            print the menu (what SwiftBar calls)
  menubar.py install    write <SwiftBar plugin dir>/hindsight.30s.sh, a
                        wrapper that execs this file with this interpreter
  menubar.py uninstall  remove it
  menubar.py start      launchctl bootstrap the ingest plist (bootout first,
                        so a crash-looping job restarts cleanly)
  menubar.py stop       launchctl bootout it — the plist is KeepAlive, so a
                        killed process would be back in seconds
  menubar.py serve      start serve.py detached, output to
                        ~/Library/Logs/hindsight/serve.log — still on-demand
                        (ADR-0001): no plist, no KeepAlive, gone at logout
  menubar.py unserve    stop whatever listens on the serve port

Reads GET /health on the listener, GET / on the views server and the breakage
table read-only. Writes nothing but the wrapper at install and SwiftBar's
PluginDirectory preference if it has never chosen one.
"""
import os
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "local-data" / "hindsight.db"
PORT = 4318
SERVE_PORT = 8321
LABEL = "com.hindsight.ingest"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
DOMAIN = f"gui/{os.getuid()}"
SERVE_LOG = Path.home() / "Library" / "Logs" / "hindsight" / "serve.log"
WRAPPER_NAME = "hindsight.30s.sh"
WRAPPER = ('#!/bin/sh\n# written by menubar.py install — edit build/menubar.py, not this\n'
           'exec "{python}" "{script}" "$@"\n')
DEFAULT_PLUGIN_DIR = Path.home() / "Library" / "Application Support" / "SwiftBar" / "Plugins"


def http_up(port, path):
    """Any HTTP answer means the socket is served; a refused connection does not."""
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=2).close()
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def open_breakages(db=DB):
    """Open rows as (id, tier, condition, key, new_version); a str on failure.
    An unreadable table is shown, never read as clean."""
    if not Path(db).exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
        try:
            return conn.execute(
                "SELECT id, tier, condition, key, new_version FROM breakage"
                " WHERE acknowledged_at IS NULL ORDER BY id").fetchall()
        finally:
            conn.close()
    except sqlite3.Error as e:
        return str(e)


def render(up, rows, plist_installed=True, serve_up=False):
    """The SwiftBar menu for one tick. Icon: red pairs with blue, never green;
    grey when either process is down, red for a problem row regardless."""
    n = len(rows) if isinstance(rows, list) else 0
    if isinstance(rows, list) and any(r[1] == "problem" for r in rows):
        icon = f"🔴 {n}"
    elif not up or not serve_up:
        icon = "⚪"
    else:
        icon = f"🔵 {n}" if n else "🔵"
    me = f'bash="{sys.executable}" param1="{Path(__file__).resolve()}"'
    out = [icon, "---"]
    if up:
        out += [f"Listener running on :{PORT}",
                f"Stop listener | {me} param2=stop terminal=false refresh=true"]
    elif plist_installed:
        out += ["Listener stopped",
                f"Start listener | {me} param2=start terminal=false refresh=true"]
    else:
        out += ["Listener not installed | color=gray",
                "python3 build/listener.py install | font=Menlo size=11"]
    out.append("---")
    if serve_up:
        out += [f"Views server running on :{SERVE_PORT}",
                f"Open what view | href=http://127.0.0.1:{SERVE_PORT}/what",
                f"Stop views server | {me} param2=unserve terminal=false refresh=true"]
    else:
        out += ["Views server stopped",
                f"Start views server | {me} param2=serve terminal=false refresh=true"]
    out.append("---")
    if isinstance(rows, str):
        out.append(f"Breakage rows unreadable: {rows} | color=red")
    elif not rows:
        out.append("No open breakages")
    for bid, tier, cond, key, ver in (rows if isinstance(rows, list) else []):
        what = {1: f"thinned {key}", 2: f"new {key}"}.get(cond, "skipped-record spike")
        colour = "red" if tier == "problem" else "blue"
        out += [f"{tier}: {what} under {ver or '?'} | color={colour}",
                f"--Acknowledge #{bid} | bash=\"{sys.executable}\""
                f" param1=\"{REPO / 'build' / 'analyze.py'}\" param2=acknowledge-breakage"
                f" param3={bid} terminal=false refresh=true"]
    return "\n".join(out) + "\n"


def plugin_dir():
    r = subprocess.run(["defaults", "read", "com.ameba.SwiftBar", "PluginDirectory"],
                       capture_output=True, text=True)
    d = r.stdout.strip()
    if not d:
        # SwiftBar asks for a folder on first launch; set it so it never has to.
        d = str(DEFAULT_PLUGIN_DIR)
        subprocess.run(["defaults", "write", "com.ameba.SwiftBar", "PluginDirectory",
                        "-string", d], check=True)
    return Path(d)


def install():
    d = plugin_dir()
    d.mkdir(parents=True, exist_ok=True)
    p = d / WRAPPER_NAME
    p.unlink(missing_ok=True)   # never write through a stale symlink
    p.write_text(WRAPPER.format(python=sys.executable, script=Path(__file__).resolve()))
    p.chmod(0o755)
    print(f"wrote {p}: {sys.executable} {Path(__file__).resolve()}")
    if not Path("/Applications/SwiftBar.app").exists():
        print("SwiftBar not found: brew install --cask swiftbar")


def uninstall():
    p = plugin_dir() / WRAPPER_NAME
    p.unlink(missing_ok=True)
    print(f"removed {p}")


def start():
    subprocess.run(["launchctl", "bootout", f"{DOMAIN}/{LABEL}"], capture_output=True)
    subprocess.run(["launchctl", "bootstrap", DOMAIN, str(PLIST)], check=True)


def stop():
    subprocess.run(["launchctl", "bootout", f"{DOMAIN}/{LABEL}"], check=True)


def serve():
    SERVE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(SERVE_LOG, "ab") as log:
        subprocess.Popen([sys.executable, str(REPO / "build" / "serve.py")],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                         start_new_session=True)


def unserve():
    # Whatever holds the port — a terminal's serve.py or one started here.
    r = subprocess.run(["lsof", "-t", f"-iTCP:{SERVE_PORT}", "-sTCP:LISTEN"],
                       capture_output=True, text=True)
    for pid in r.stdout.split():
        os.kill(int(pid), 15)


def main(argv):
    cmd = argv[0] if argv else None
    if cmd in ("install", "uninstall", "start", "stop", "serve", "unserve"):
        return globals()[cmd]()
    if cmd:
        sys.exit(__doc__)
    sys.stdout.write(render(http_up(PORT, "/health"), open_breakages(), PLIST.exists(),
                            serve_up=http_up(SERVE_PORT, "/")))


if __name__ == "__main__":
    main(sys.argv[1:])
