# #86 Run-it section: honest setup docs + hard-wired list

state: closed · labels: ready-for-agent · opened: 2026-09-01 · closed: 2026-09-01

## Parent

#56

## What to build

The README's third section, written against what the clean-environment ticket proved rather than what we believe. macOS + launchd stated as assumptions; the plists, hook registration (its absolute install path called out), OTEL env vars, and backfill from existing transcript history; the privacy posture stated plainly (the DB holds transcript-derived text, stays in the gitignored local data directory, nothing leaves the machine); and a plain 'hard-wired to this Mac' list. Document, don't automate: no installer, no Linux — deferred explicitly until a real second user appears.

## Acceptance criteria

- [ ] Run-it section follows the verified step list from #84 verbatim — no undocumented step, no documented step that wasn't exercised
- [ ] Hard-wired list enumerates every machine-specific assumption a reader must change
- [ ] Privacy posture stated in the section, not just in ADRs
- [ ] Deferred scope (installer, Linux) stated as deferred, with the reason

## Blocked by

- #84
- #85


---

**comment · 2026-09-01**

All four acceptance criteria met, landed in 8074632:

- **Verified step list, verbatim**: the three steps transcribe #84's proven list — clone (no build step), analyze (incl. no-transcripts exit 0, live-session guard, limit-exhaustion pause, missing-claude pause explicitly credited as the path #84 exercised), serve (verbatim refusal message, listener-only-DB clause). The nightly is stated as the one piece verified by code reading only.
- **Hard-wired list**: hook snippet's absolute clone path (build/hook.py:21-25) first, then ~/Documents/Claude workspace layout, ~/.claude home, the haiku model pin, ports 4318/8321, and the install-time absolutes both plists bake (python path; shell PATH in the nightly). A code sweep found no further machine-specific assumption.
- **Privacy posture in the section**: transcript-derived text in gitignored local-data/, read-only server on 127.0.0.1, and the one outbound path stated honestly — extracts go to the model through the operator's own claude CLI, the same trust boundary that produced them.
- **Deferred scope**: no installer, no uvx, no Linux/systemd — documented-not-automated, with the one-user reason and reversal condition (#56).

Two-axis review (standards + spec sub-agents): zero hard violations; four wording refinements found and applied before commit. Full test suite green (147).

