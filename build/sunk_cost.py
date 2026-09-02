"""The sunk-cost scan (ticket #24) — what a session pays at start before
the first prompt: the CLAUDE.md chain with @-imports expanded, skill and
command descriptions, MCP config, itemised per project with plugins as a
grouping level and the plugin registry keyed by install path so a skill
behind duplicate install records counts once. Full replace per run.

A leaf module: stdlib only, nothing from analyze — the import direction is
analyze -> sunk_cost only (ticket #82; analyze's backstop imports
plugin_entries and PLUGINS_FILE from here).
"""
import json
import re
from pathlib import Path

# The structurally-diffed plugin registry file under ~/.claude.
PLUGINS_FILE = "plugins/installed_plugins.json"


def plugin_entries(content):
    """installed_plugins.json -> {plugin name: entries}, comparable values.
    Unparseable content degrades to None (no structural diff possible)."""
    try:
        plugins = json.loads(content).get("plugins", {})
        return plugins if isinstance(plugins, dict) else None
    except (json.JSONDecodeError, AttributeError):
        return None


def est_tokens(path):
    """size/4 token estimate (ccwhere's method). These guide the where-view's
    composition drill only — the measured median carries authority."""
    try:
        return Path(path).stat().st_size // 4
    except OSError:
        return 0


# The instruction files loading in full at each level of the chain.
MD_CHAIN = ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md")
# A memory import: an @path line inside an instruction file. Claude Code
# recurses these to depth 5; a decorator in a fenced code block matches too
# but resolves to no file and drops out harmlessly.
IMPORT_RE = re.compile(r"^@(\S+)", re.M)
_NAME_RE = re.compile(r"^name:\s*(.+)$", re.M)
_DESC_RE = re.compile(r"^description:\s*(.+?)(?=\n\w|\n---)", re.S | re.M)


def instruction_files(f, depth=5):
    """f plus everything it @-imports, transitively to the real loader's
    depth cap, existing files only, deduped. Without this the chain misses
    most of its own weight — this repo's CLAUDE.md is 1.6K importing a 19K
    process file."""
    out, seen, stack = [], set(), [(Path(f), depth)]
    while stack:
        f, d = stack.pop()
        f = f.expanduser()
        if str(f) in seen or not f.is_file():
            continue
        seen.add(str(f))
        out.append(f)
        if d:
            try:
                text = f.read_text(errors="ignore")
            except OSError:
                continue
            stack.extend((f.parent / Path(m).expanduser(), d - 1)
                         for m in IMPORT_RE.findall(text))
    return out


def _head(path):
    """First 3000 bytes (bounded read — skill bodies run to hundreds of KB),
    or None on an unreadable file."""
    try:
        with Path(path).open(errors="ignore") as f:
            return f.read(3000)
    except OSError:
        return None


def _desc_tokens(head):
    """Description-size/4 (+40 name-and-framing overhead) — what the skill
    roster in the system prompt actually carries per entry."""
    m = _DESC_RE.search(head)
    return ((len(m.group(1)) if m else 0) + 40) // 4


def skill_items(root):
    """("skill", name, path, tokens) for every SKILL.md under root, sized by
    the frontmatter description — the part every session pays at start; the
    body loads on use. Name falls back to the skill's directory name."""
    items = []
    if not Path(root).is_dir():
        return items
    for sm in sorted(Path(root).rglob("SKILL.md")):
        head = _head(sm)
        if head is None:
            continue
        name = _NAME_RE.search(head)
        items.append(("skill", name.group(1).strip() if name else sm.parent.name,
                      str(sm), _desc_tokens(head)))
    return items


def command_items(root):
    """("command", name, path, tokens) for command .md files — they load
    like skills and are invoked like skills (ccwhere's probe finding)."""
    items = []
    if not Path(root).is_dir():
        return items
    for md in sorted(Path(root).rglob("*.md")):
        head = _head(md)
        if head is not None:
            items.append(("command", md.stem, str(md), _desc_tokens(head)))
    return items


def plugin_registry(claude_dir):
    """{plugin key: [install paths]} from installed_plugins.json. Billing
    dedupes by install path (ticket #24) — the fix for ccwhere's per-record
    scan, which double-counted skills behind duplicate install records."""
    pf = Path(claude_dir) / PLUGINS_FILE
    if not pf.exists():
        return {}
    keys = {}
    for key, recs in (plugin_entries(pf.read_text()) or {}).items():
        for rec in (recs if isinstance(recs, list) else []):
            p = rec.get("installPath") if isinstance(rec, dict) else None
            if p:
                keys.setdefault(key, []).append(p)
    return keys


def _enabled_plugins(path):
    """The enabledPlugins map from one settings file. None only when the
    file is absent or carries no map — the legacy installed = loaded signal.
    A file present but unparseable (typo, torn read) returns {} instead: an
    empty map undercounts for one full-replace cycle and self-heals, where
    None would flip every installed plugin to user scope and zero every
    project's rows in the same run."""
    try:
        content = Path(path).read_text()
    except OSError:
        return None
    try:
        m = json.loads(content).get("enabledPlugins")
        return m if isinstance(m, dict) else None
    except (ValueError, AttributeError):
        return {}


def enabled_map(d):
    """Merged enabledPlugins across settings.json + settings.local.json in
    one directory — the same resolution at user and project scope. None when
    neither file carries a map (distinct from an empty map)."""
    maps = [_enabled_plugins(Path(d) / nm)
            for nm in ("settings.json", "settings.local.json")]
    if all(m is None for m in maps):
        return None
    merged = {}
    for m in maps:
        merged.update(m or {})
    return merged


def _claude_json(claude_dir):
    """(parsed ~/.claude.json sibling of the claude dir, its path) — where
    user-scope and per-project mcpServers actually live. {} if unreadable."""
    p = Path(claude_dir).parent / (Path(claude_dir).name + ".json")
    try:
        return json.loads(p.read_text()), p
    except (OSError, ValueError):
        return {}, p


def scan_sunk_cost(conn, claude_dir, projects_dir):
    """The session-start sunk-cost scan (ticket #24): itemise what a session
    pays before the first prompt — the CLAUDE.md chain (@-imports expanded),
    skill and command descriptions, MCP config — with plugins as a grouping
    level (the `plugin` column). project-NULL rows are user scope, paid by
    every project's sessions; a project's full bill is WHERE project=? OR
    project IS NULL. Full replace every run, so rescanning is idempotent.
    ponytail: MCP rows are config-JSON size, not the wire schemas servers
    serve — cross-check against OTEL's MCP attribution if the proxy ever
    misleads. project keys are workspace dir basenames; a session run from a
    subdirectory carries a suffixed name (hindsight-ideation-...) — prefix-
    match at query time if that join ever matters."""
    claude_dir, rows = Path(claude_dir), []
    scanned = {}  # install path -> items, each path scanned at most once

    def plugin_items(p):
        if p not in scanned:
            d = Path(p)
            sk = d / "skills"
            # ponytail: counts what's on disk under skills/ + commands/; a
            # plugin shipping unloaded skills (deprecated/, mirrors) still
            # overcounts — read the plugin manifest if that gap ever matters.
            scanned[p] = (skill_items(sk if sk.is_dir() else d)
                          + command_items(d / "commands"))
        return scanned[p]

    def add_items(project, plugin, items):
        rows.extend((project, cat, plugin, n, p, t) for cat, n, p, t in items)

    def add_md_chain(project, d):
        emitted = set()  # AGENTS.md both in the chain and @-imported: once
        for name in MD_CHAIN:
            for f in instruction_files(d / name):
                if str(f) not in emitted:
                    emitted.add(str(f))
                    rows.append((project, "claude-md", None, f.name, str(f),
                                 est_tokens(f)))

    def add_mcp(project, name, path, tokens):
        rows.append((project, "mcp", None, name, str(path), tokens))

    def add_plugins(project, plugin_keys, seen):
        for k in plugin_keys:
            for p in keys.get(k, []):
                if p not in seen:
                    seen.add(p)
                    add_items(project, k, plugin_items(p))

    keys = plugin_registry(claude_dir)
    user_map = enabled_map(claude_dir)
    # No map anywhere at user scope is an older config where installed =
    # loaded — count all rather than report a false zero (ccwhere's rule).
    user_keys = list(keys) if user_map is None else [k for k in keys if user_map.get(k)]
    cj, cj_path = _claude_json(claude_dir)

    add_md_chain(None, claude_dir)
    add_md_chain(None, Path(projects_dir))  # workspace level
    servers = cj.get("mcpServers")
    if isinstance(servers, dict) and servers:
        add_mcp(None, cj_path.name, cj_path, len(json.dumps(servers)) // 4)
    add_items(None, None, skill_items(claude_dir / "skills")
              + command_items(claude_dir / "commands"))
    user_seen = set()  # an install path billed once per scope chain
    add_plugins(None, user_keys, user_seen)

    if Path(projects_dir).is_dir():
        for proj in sorted(Path(projects_dir).iterdir()):
            if not proj.is_dir():
                continue
            add_md_chain(proj.name, proj)
            if (proj / ".mcp.json").is_file():
                add_mcp(proj.name, ".mcp.json", proj / ".mcp.json",
                        est_tokens(proj / ".mcp.json"))
            servers = ((cj.get("projects") or {}).get(str(proj)) or {}).get("mcpServers")
            if isinstance(servers, dict) and servers:
                add_mcp(proj.name, cj_path.name, cj_path,
                        len(json.dumps(servers)) // 4)
            add_items(proj.name, None, skill_items(proj / ".claude" / "skills")
                      + command_items(proj / ".claude" / "commands"))
            pmap = enabled_map(proj / ".claude") or {}
            # seen starts from the user scope: a path already in the user
            # floor is not billed again to the project (the ccwhere fix,
            # held across scopes) — but two projects each pay their own.
            add_plugins(proj.name,
                        [k for k, v in pmap.items()
                         if v and k in keys and k not in user_keys],
                        set(user_seen))

    conn.execute("DELETE FROM sunk_cost")
    conn.executemany("INSERT INTO sunk_cost (project, category, plugin, name,"
                     " path, tokens) VALUES (?, ?, ?, ?, ?, ?)", rows)
    conn.commit()
