---
name: ops
description: Install, uninstall, start, stop, serve or open hindsight's launchd jobs and views server.
argument-hint: install [--from <v1 db>] | uninstall | start | stop | serve | open
disable-model-invocation: true
---

# /hindsight:ops

Run this one command with the arguments exactly as given, then report its output verbatim. Do nothing else: no retries, no fixes, no edits to `~/.claude/settings.json`.

```bash
CLAUDE_PLUGIN_DATA="${CLAUDE_PLUGIN_DATA}" python3 "${CLAUDE_PLUGIN_ROOT}/cli/hindsight.py" $ARGUMENTS
```

With no arguments, the command prints its usage. Done when the command has run once and its output is shown.
