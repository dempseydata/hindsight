# ADR-0043: The MCP server is the one exception to zero pip deps

**Date:** 2026-11-24 · **Status:** accepted · **Amends:** ADR-0003 (dependencies) · **Decides:** the stack half of issue #125 (map #118, dashboards v2)

## Context

ADR-0003 made zero pip packages the default for the pipeline and the listener, and required an ADR for any exception. It gave two reasons. A launchd-managed listener has no third-party package to break silently on a Python upgrade. And the install stays clone-and-run.

Issue #125 adds a read-only MCP server: four tools over the store, run over stdio. Without a package, that means hand-writing MCP's JSON-RPC over stdio, including the handshake and protocol-version negotiation. The official Python `mcp` SDK already does that, and it follows the protocol as it changes.

ADR-0003's reasons do not carry over to the server. Claude Code starts it once per session, not launchd. If it breaks, it breaks visibly in the conversation that called it, not silently overnight. And the plugin route (ADR-0036) already replaced clone-and-run.

## Decision

1. **The MCP server may depend on the official Python `mcp` SDK.** Nothing else in hindsight may. The listener, the analysis pipeline, the nightly, the dashboard (`serve.py`) and the CLI stay stdlib-only under ADR-0003.
2. **The dependency is pinned inline and isolated by uv.** `cli/mcp_server.py` declares `mcp==<exact version>` in a PEP 723 inline-script header. The plugin's `.mcp.json` runs it with `uv run --script ${CLAUDE_PLUGIN_ROOT}/cli/mcp_server.py`. uv builds a cached environment of its own on first launch. Nothing is installed into the system Python.
3. **The server imports hindsight's stdlib modules and is never imported by them.** It reuses the data functions in `serve.py` and `how.py`. The dependency stops at the server's own file.

## Alternatives rejected

- **Hand-written JSON-RPC, keeping zero deps everywhere.** It is about a hundred lines today. But the protocol is still revising its handshake and capabilities, and every revision would be hindsight's to follow. Owning a protocol implementation for one user's four tools costs more than one pinned package.
- **Retire the zero-deps default project-wide.** Nothing else wants a package. The listener's silent-break risk on a Python upgrade is still real.
- **`pip install mcp` into the operator's Python.** Homebrew's Python refuses system-wide pip (PEP 668). A venv beside the plugin would need an install step and would break on the next Python upgrade: ADR-0003's trap again.

## Consequences

- **uv becomes a prerequisite**, but only for the MCP server. Without uv, the server fails to start and every other part of hindsight runs unchanged. The README's requirements line says this when the server ships. Until then, its "stdlib only, so no pip and no venv" line stays true.
- **The first launch on a machine needs the network**, so that uv can fetch the pinned SDK. Later launches use uv's cache.
- **Raising the pin is a deliberate change**, made with a smoke test of the four tools. It is not automatic.
- **The descriptions in `CLAUDE.md` and the README ("stdlib-only Python") gain the exception** when the server ships, in the same change.
- ADR-0003's status line reads "accepted; dependencies amended by ADR-0043".
