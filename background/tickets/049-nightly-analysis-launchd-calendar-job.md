# #49 Nightly analysis launchd calendar job

state: closed · labels: wayfinder:task · opened: 2026-08-25 · closed: 2026-08-25

Part of #40

## Question

Install the nightly analysis run: a launchd calendar job (`StartCalendarInterval`) invoking the same analysis CLI command run by hand — a scheduled *invocation* of the on-demand app, not a background *process* (ADR-0008; ADR-0001 amendment 2026-08-24). No nightly existed before; only the ingest listener is scheduled today. Deliverable: the plist plus install/uninstall notes. ADR-0003 already designed analysis for unattended runs (limit pause/resume, self-exclusion).


---

**comment · 2026-08-25**

## Resolution

Delivered as `install`/`uninstall` subcommands on `build/analyze.py` (commit b15ccff), mirroring the listener's established idiom — the plist is generated at install time rather than checked in, so paths are never stale and the machine-specific file stays out of the repo.

**What the plist is:** `com.hindsight.nightly`, a `StartCalendarInterval` job at 03:00 invoking `analyze.py` with the same interpreter and zero arguments — identical to the hand-run command, a scheduled *invocation* of the on-demand app per the ADR-0001 amendment (no `KeepAlive`, no `RunAtLoad`). Logs append to `local-data/analyze.log`. One judgement call worth recording: **the installing shell's `PATH` is baked into the plist** — launchd's default PATH cannot resolve `claude` (the model runner is invoked by bare name) nor the CLI-kind classification probes, so the job inherits the environment it was installed from. Re-run `install` after moving `claude` (idempotent: bootout-then-bootstrap).

**Install/uninstall notes:**
- `python3 build/analyze.py install` — writes `~/Library/LaunchAgents/com.hindsight.nightly.plist` and bootstraps it into `gui/$UID`
- `python3 build/analyze.py uninstall` — bootout + remove the plist
- Asleep at 03:00 → launchd runs the job on wake; powered off → that night is skipped and the next run picks the sessions up (ADR-0003 designed analysis for exactly this: idempotent, limit pause/resume, self-exclusion)

**Operator action required (one command):** the session sandbox blocked `launchctl bootstrap`, so the job is coded and tested but **not yet registered**. Run:

```
python3 build/analyze.py install
```

then verify with `launchctl print gui/$(id -u)/com.hindsight.nightly`.

Tests: new plist-shape test (valid plist, calendar trigger, no daemon keys, PATH baked); full `test_analyze` suite green (44).

