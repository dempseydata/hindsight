# #4 Decide the silent-change backstop

state: closed · labels: wayfinder:grilling · opened: 2026-08-01 · closed: 2026-08-01

## Question

Which mechanical sources detect setup changes that were never discussed in a session (the model's blind spot, proven by the unreported vendored v1.22.0 update): git history of `.claude` trees? settings.json snapshots/mtimes? plugin cache versions? skills-lock files? And how are diffs stored so the why-view can show "changed, no stated rationale" entries honestly?

Part of #1



---

**comment · 2026-08-01**

## Resolution

**Sources (three, exactly):**

1. **Project `.claude/` trees + CLAUDE.md via each project's own git history** — commits only; uncommitted edits are an accepted, bounded gap (retrospective review + prompt-commit habits). Backfill is real history: change events reach months back with true timestamps.
2. **Global `~/.claude` config surface via analysis-time snapshots** — text-config subset only: `settings.json`, `settings.local.json`, `CLAUDE.md`, `mcp.json`, `hooks/`, `agents/`, `commands/`, `skills/`. `~/.claude` is not a git repo, so snapshots are the only history possible there. First run records a silent baseline — no synthetic "added" events.
3. **`installed_plugins.json` diffed structurally** — `(plugin, old_version → new_version, lastUpdated, gitCommitSha)`. Directly catches the auto-update class that proved the blind spot (the unreported vendored v1.22.0 update). Baseline seeds one honest fact per plugin from the file's own `installedAt`/`lastUpdated` timestamps.

**Rejected sources:** mtime-watching (detects *that* something changed, not *what* — cannot produce an honest diff) and skills-lock files (verified: they don't exist on this machine).

**Capture:** at analysis runs only — the batch-on-launch run and the manual refresh. The listener stays ingest-only; ADR-0001 is not reopened. A detected change is windowed "between run N−1 and run N", with file mtimes narrowing the timestamp inside the window.

**Storage:** in the existing SQLite store — content-addressed blobs `(hash, content)` deduped by hash, plus one change-event table `(path, old_hash, new_hash, window-or-commit, mtime, kind: added/modified/deleted)` shared by git-sourced and snapshot-sourced events. Diffs are computed at render from the two blobs, never stored, so the view can always show full before/after context. Plugin changes are structural records, not text diffs. Shadow-git over `~/.claude` rejected: a second storage system with commit-time semantics instead of observation windows.

**Attribution ("changed, no stated rationale"):** deterministic linking, no model in the loop. A change event links to a why-finding only when the finding's `change` text or resolved evidence spans **name the changed artifact** (normalised path/basename/skill/plugin-name match) within the change window ± one adjacent session. No link ⇒ the entry reads **"changed, no stated rationale"** and states its observation window. Failure direction is deliberate: a missed link under-claims (forgivable, visible); a model-inferred link would over-claim and poison trust in every entry. ADR-0002's extraction contract is untouched — linking is purely downstream of it. Findings that discuss a change without naming the artifact won't link in v1; a smarter linking pass is addable later without schema change.

**Noise:** filtering is a render-time concern, never capture-time — a capture exclusion is a permanent blind spot of exactly the kind this ticket exists to close. The display policy for high-frequency churn (`settings.local.json` permission-allowlist appends) is delegated to the why-view greybox, where real data decides it.



---

**comment · 2026-08-01**

Resolved — see resolution comment above. Decision indexed on the map.

