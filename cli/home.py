"""Hindsight home (ADR-0036): everything that outlives a plugin update.

`~/.hindsight/`, or `HINDSIGHT_HOME`. It holds the database, the logs and
`current`, the symlink to the live plugin root that launchd runs through.
Nothing deletes it. Read at call time; the --db defaults in analyze, listener
and serve read it once, at import.
"""
import os
import re
import sys
from pathlib import Path

INGEST, NIGHTLY = "com.hindsight.ingest", "com.hindsight.nightly"  # launchd labels


def loopback_host(host):
    """DNS-rebinding guard for the two loopback servers: True when the Host
    header names loopback. A page that rebinds its own domain to 127.0.0.1
    still sends its own domain here. No header passes: browsers always send one."""
    if not host:
        return True
    host = host.strip().lower()
    if re.fullmatch(r".*:\d+", host):
        host = host.rsplit(":", 1)[0]
    return host in ("127.0.0.1", "localhost", "[::1]")


def private(db_path):
    """Owner-only modes on the store, whatever the umask: 0600 on the db and its
    WAL sidecars, 0700 on its directory when that is Hindsight home. A --db
    elsewhere leaves its directory alone: that one is the operator's choice."""
    db_path = Path(db_path)
    for suffix in ("", "-wal", "-shm"):
        p = Path(f"{db_path}{suffix}")
        if p.exists():
            p.chmod(0o600)
    if db_path.parent.resolve() == home().resolve():
        db_path.parent.chmod(0o700)


def domain():
    return f"gui/{os.getuid()}"


def home():
    return Path(os.environ.get("HINDSIGHT_HOME") or Path.home() / ".hindsight")


def log_to(name):
    """Point this process's stdout and stderr at <home>/logs/<name>, creating
    the directory first. launchd jobs log through here rather than through a
    plist's StandardOutPath, so a deleted log directory comes back at the next
    start instead of failing the spawn or swallowing errors (ADR-0036)."""
    d = home() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    home().chmod(0o700)
    fd = os.open(d / name, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    sys.stdout.flush()
    sys.stderr.flush()
    os.dup2(fd, 1)
    os.dup2(fd, 2)
    os.close(fd)
