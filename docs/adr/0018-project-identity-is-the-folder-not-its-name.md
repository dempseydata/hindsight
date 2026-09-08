# ADR-0018: A project is its folder, not its name — identity by inode, renames observed, history stays with the folder

**Date:** 2026-09-08 · **Status:** accepted · **Decides:** the folder-rename question raised 2026-09-08 (tickets cut by `to-tickets` follow)

## Context

On 2026-09-07 the working folder `hindsight` was renamed `hindsight-old`, a born-public successor `hindsight-new` was created, and for twenty minutes in between `hindsight-new` itself carried the name `hindsight`. Project identity was the transcript directory name, fixed once at sync, so: the 114 sessions and 445 trail events under `hindsight` were orphaned from any live declaration (folder gone → declaration *absent* → raw trail, chip hidden under ADR-0009); `hindsight-old` showed one session; and seven sessions opened during the twenty-minute window sat under `hindsight` although they ran in `hindsight-new`. Nothing was lost — the join was wrong. The glossary had no term for *project* at all; the how-view was "per workspace folder", and by that definition a rename ends one project and starts another.

The operator's principle, put to a grilling: **insights stay with the folder they belong to; nothing is forced from an old folder onto a new one.** `hindsight-new` is a fork for a reason and owns its own trail from 6 September.

## Decision

1. **A project is the folder itself, identified by its inode.** Its name is an attribute. A rename keeps the project; a copy, clone or cross-volume move is a new folder and so a new project — the boundary the principle asks for, not a gap.
2. **Renames are observed, never declared.** The self-instrumentation hook (ADR-0005) stamps every session with its folder's inode at SessionStart — one `stat`, live, exact, including a rename-and-back inside a day. The analysis run's presence observation (ADR-0009) records name→inode per run and keeps the history of names each inode has carried; that history gives an inode its current display name and its former names. No `formerly:` key in the process declaration, no curated file in the workspace.
3. **One name per project in the database, canonicalised at analysis time.** Rows are re-keyed to the folder's current name when the run sees the inode under a new name; every project-scoped query stays untouched. The how-view accepts every former root when matching write paths and shows "formerly …" in its header; chips and ledger carry current names only.
4. **Attribution has three sources and no fourth:** hook (live), operator (an `attribute` command stamping an inode onto legacy rows, with an optional time bound), or name (no identity recorded — the session keeps its synced name, the coverage-window rule). Name reuse is resolved by identity; a name-only session in a reused name is a stated ceiling. Never a presence-flip heuristic, never name resemblance.
5. **The present state is repaired by the operator command, twice:** `hindsight` → `hindsight-old` for sessions before 2026-09-07 13:51Z, `hindsight` → `hindsight-new` for the seven after.

## Considered options

- **History follows the product lineage** (`hindsight-new` inherits the 114 sessions as the consolidated successor). Rejected by the operator: the fork was deliberate and owns its own how-view; forcing an old folder's history onto a new one is precisely the thing the principle forbids.
- **Declared rename** — a `formerly:` key in the process declaration. Retroactive and simple, but an ADR-0011 schema change, unavailable to a project without a declaration, and the exact instrument for forcing history across folders.
- **Run-cadence inode detection alone** — compare name→inode maps run to run. Cheap, but provably blind to the case that actually happened: both renames fell between two nightly runs and the maps were identical on both nights. Kept as the presence observation; not sufficient as the trap.
- **Directory ctime as the rename instant.** A directory's ctime also moves when entries are added or removed, so it is an upper bound at best in an active folder — usable to corroborate a one-off, not as a mechanism.
- **Resolve at read time** — rows keep their synced name and every project-scoped query joins through a rename table. A dozen sites across the server, the how pipeline and the narrative writer, each a place to forget the join.
- **Presence-flip heuristic** — folder vanished, similar name appeared. ADR-0009 already found this misfires on archive-by-rename.

## Consequences

- ADR-0009 is amended: presence is no longer rewritten whole each run; it keeps the (inode, name, first seen, last seen) history the how-view's former roots and "formerly" line read from. Hiding is unchanged in meaning — a project is hidden when its folder is absent under every name it has carried.
- Presence reads the workspace root both ways: name → folder for every name a session references, and inode → name over the root's top-level folders for every identity a session carries. The second is what lets a rename be re-keyed the run after it happens, before any session opens under the new name; without it a live folder sat hidden under its old name until one did. A nested project folder is found only the first way — a stated ceiling.
- The hook payload, the listener's stored attributes and the sessions table each gain the folder identity; the hook's failure mode stays silent and bounded. Sessions predating the change carry no identity until the operator stamps them.
- Re-keying substrate rows on rename is not the history re-shaping ADR-0009 forbids: a rename is not a deletion, and by (1) the rows always belonged to that folder.
