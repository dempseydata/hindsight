# Hindsight v2 — ideation framing

**Date:** 2026-11-13
**Method:** A retrospective over v1's record ([why.md](../why.md), the ADRs, the exported tickets) and its operation since shipping, set against one proposed change of direction.
**Verdict:** Not yet a premise. These are the inputs to v2's six forcing questions, which have not yet been run. One assumption must be tested before any design (see *Open risks*).

## Why a v2 is on the table

v1 answers *where*, *what* and *how* from local history. It works. Collection was checked end to end on 2026-11-13 and was current to the day. But operating it has shown where its cost sits, and a new presentation option has appeared that v1 was not designed for: a page inside the Claude desktop app that reads a local MCP server.

v2 is built **in this repository and folder**, not a fresh one. The utility's evolution is part of what it records: ADR-0018 holds that a project is its folder and that history stays with it. A fresh folder would split v1's trail from v2's, and that is the opposite of the point.

## The evidence gap, stated first

v1's bar was *acted-upon insights, not interest* ([why.md](../why.md)). Whether v1 has produced any acted-upon insight since September cannot be measured: hindsight records no use of itself, and its only access log covers the build period. The one action the record shows came from the so-what dry run (ADR-0026), not from a shipped view. An observability tool that does not observe its own use is v2's first lesson, and question 1 of the forcing questions has to be answered from memory until that is fixed.

## Lessons from v1

### Data model

1. **Ingest records, not sessions.** Most reversals came from treating a session as one file analysed once:
   - resumed sessions went unrecorded once marked done, 26M tokens on the day it was found (ADR-0013);
   - subagent transcripts were never seen (ADR-0019);
   - growth required a per-session wipe and rescan;
   - giving a session a single start `date` later made "synced through" lag a week behind collection.

   v2 ingests each transcript record as a row keyed by its own id, append-only and idempotent. Growth is new rows; a session's dates derive from its records.
2. **Capture before retention prunes.** Transcripts aged past Claude Code's retention while queued behind a model rate limit (ADR-0015). Copy or extract on quiet, separately from any model work, from the first build. v1 reached this as "greedy extraction"; v2 starts there.
3. **Stamp identity at the source.** Transcript directory names encode folders lossily. Project identity needed a hook, inode tracking and a repair command (ADR-0018). v2's hook records folder identity for every session from the first commit.
4. **Derive time at read, in local time.** ADR-0014 stands. UTC buckets misdated 11.5% of usage rows.
5. **Keep the honesty rules.** Unknown is never zero; pruned is reported as pruned; coverage windows are stated. These held.

### Operations

6. **Fewer moving parts, and health as data.** v1 runs five: an OTLP listener, a launchd nightly, a hook, a menu-bar plugin and a foreground server. Its quietest failure was the log directory being deleted underneath a running listener, which left its errors invisible for two days. v2 records its own health in the database (last event received, last run, last error, freshness per source) and puts that row in front of the operator. "Is collection working?" should be answered by looking, not by an investigation.
7. **Drift is core, not an add-on.** The transcript format is internal and changed nine times in three months. The drift guard (ADR-0020) and a field contract are written before the first reader.

### Model use

8. **Mechanical by default; a model only where an eval earns it.** The why-view was dropped (ADR-0006). The so-what synthesis failed a criterion fixed before its run, and the mechanical rows it was compared against rated *act* once in eighteen (ADR-0026). Model-quoted evidence failed verbatim verification (ADR-0002). Only the what-pass audit survived, behind a standing eval. v2 starts with no model calls and earns each one back.
9. **The one *act* pointed at errors by consumer.** That surface was recorded in ADR-0026 and never built. It is v2's strongest evidence-backed candidate view.

### Scope and presentation

10. **Kill a view before charting it.** The blind *would I act on this?* rating that ended so-what took an afternoon; the eight tickets before it took weeks. Run it on rendered sentences over real data before any map.
11. **Chrome cost more than it returned for one user.** v1 had a direction-setting pass (ADR-0007), a second theme (ADR-0017) and a full restyle (ADR-0029). The restyle cut the ledger rows above the fold from 11 to 3. A presentation layer someone else maintains is worth a great deal here.

## The proposed direction: an MCP server, with a desktop page over it

A Claude desktop Artifact page can reach data three ways. Only one keeps hindsight's data on the machine:

| Route | Data path | Verdict |
| --- | --- | --- |
| The page's own database (`db`) | Aggregates are pushed to claude.ai and stored there | Rejected. It breaks the local-only posture, and nothing local can write to it without a Claude session in between. |
| Project files (`files`) | Read from a cloud-side Claude Code project | Rejected for the same reason. |
| A local MCP server (`mcp`, `host:` server) | A read-only stdio server over the SQLite store, called live by the page on the operator's device | **Proposed.** |

The same server makes hindsight queryable from any Claude conversation. A dashboard answers a fixed set of questions; a conversation over the same queries does not. That may be the larger gain of the two.

What it replaces: the foreground server, the menu-bar *open* path and the token-contract inlining. What it does not touch: collection. The listener, the nightly and the hook are unchanged by a change of presentation.

What it costs:

- The page works only in the Claude desktop app with the server configured. That fits a one-user tool, but there is no browser fallback unless one is kept.
- Design control passes to the host, which makes ADR-0007, ADR-0017, ADR-0029 and the token contract moot.
- An on-demand narrative through the page's `sample` capability would replace the nightly's model calls but spend the viewer's usage each time it renders.

## Collection that survives source changes

v1's collection was robust to failure but brittle to change. Each format change or retention window cost data until a fix landed. Measured on 2026-11-13: 338 transcripts (435 MB) remain on disk against 486 sessions known to the database, so retention has already taken about 150 originals. v2's collection rests on five rules, in order of what each buys:

1. **Capture raw, parse later.** Every transcript record is stored verbatim, compressed with stdlib `zlib` (an estimated 40–60 MB for today's corpus), before any parsing. Derived tables are a pure, versioned function of that copy. A parser fix re-derives from hindsight's own copy rather than rescanning a disk retention keeps shrinking. A format change becomes a reparse, not a loss.
2. **Capture on the event, not the night.** Claude Code hooks carry `transcript_path`. A `Stop`/`SessionEnd` hook triggers capture within seconds of a session going quiet, which ends the retention race (ADR-0015) for good. The nightly is left with analysis only.
3. **Prefer documented sources.** OTel and hooks are documented interfaces; the transcript format is internal and changed nine times in three months. Tokens, tool decisions and errors come from OTel where it carries them. The transcript is read for what only it holds: the conversation the audit reads.
4. **Cross-check the sources against each other.** Daily token totals from OTel and from the transcripts are reconciled, and divergence beyond a threshold fixed in advance raises a breakage. This detects shape drift without knowing which field moved, and sits beside the field-level guard (ADR-0020), which says which one did.
5. **Health is data.** Last event, last capture, last run and last error per source are rows in the database, shown on every view and checked at session start (lesson 6).

## Shipping shape: a Claude Code plugin

The operator's answer to the shipping question is **leaning plugin**. A plugin carries hooks (registered through `${CLAUDE_PLUGIN_ROOT}`, which replaces the hand-edited hook paths in user settings), the MCP server, skills and a `bin/` directory as one installable unit. Path wiring is v1's most fragile configuration: renaming the working folder on 2026-11-13 touched two launchd plists, the menu-bar wrapper and three hook entries.

What it costs:

- **Installed plugins run from a versioned cache**, so the code's path changes on every update. The database cannot live under the plugin root, and launchd jobs cannot bake a cache path. Both need a stable location outside the cache. Whether Claude Code provides a persistent per-plugin data directory is unverified.
- **A plugin cannot install launchd jobs.** The listener and nightly keep a one-off install step. A `SessionStart` hook checks their health and warns when they are down or stale.
- **The house plugin layout applies:** repo root as plugin root, deterministic code in `cli/`, `claude plugin validate` gating commits, evals in `evals/`.

## Open risks

1. **Load-bearing and untested: that MCP results passing through a page served from claude.ai are not retained or logged off the machine.** The capability documentation says a page stores nothing it does not write. What transits or is logged has not been verified. This repository is public and the data is private, so this is tested before any design: one throwaway page, one read-only tool, and an inspection of what leaves the device.
2. **Refactor or rewrite.** Lessons 1–3 are a new ingest core and the MCP route is a new presentation layer. Both may land on v1's database through a schema bump and new modules. A rewrite is justified only if record-level ingest cannot migrate into the existing schema. Test that before choosing.
3. **The plugin's stable location.** If the cache-path question in *Shipping shape* has no clean answer, the database and launchd jobs need a location the plugin does not own, and the plugin case weakens. It is settled before the restructure, and the restructure is the first v2 ticket.
4. **Demand.** See *The evidence gap*. If v1 has changed little in how the operator works since September, the cheapest v2 is the MCP server alone, queried from conversation, with no dashboard.

## Next

This brief is the input to a `wayfinder` charting session. Run the six forcing questions against it, then open risks 1 and 3 become the map's first decision tickets, ahead of any build.
