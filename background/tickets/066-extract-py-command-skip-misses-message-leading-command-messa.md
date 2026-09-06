# #66 extract.py command-skip misses message-leading command messages

state: closed · labels: bug, needs-triage · opened: 2026-08-27 · closed: 2026-08-29

Found by ticket #61's review. `build/extract.py` line 57 skips command boilerplate with `text.startswith("<command-name>")` — but real command messages also occur with `<command-message>` leading (the shape #61's parse handles via the starts-with-`<command-` rule). Those messages pass the skip and leak command boilerplate into what-pass extracts. Pre-existing, cosmetic (the what-pass tolerates noise), and extract.py is the frozen ADR-0002 seam — deliberately not touched by #61. If fixed, note that cached extracts were built with the old filter.


---

**comment · 2026-08-29**

Triaged as `bug` + `needs-triage` rather than `ready-for-agent`: the defect is fully specified, but the decision it needs is a maintainer's, not an agent's — whether to touch `extract.py` at all. It is the frozen ADR-0002 seam, the leak is cosmetic (the what-pass tolerates the noise), and fixing it means every cached extract was built with the old filter. Fix, invalidate the cache, and re-run; fix and let the caches age out; or wontfix. That call unblocks it.


---

**comment · 2026-08-29**

Fixed in 6f86c55. Decision taken: fix + re-run.

**The filter.** One line — `startswith("<command-")` in place of `startswith("<command-name>")`, the same rule #61's parse uses. The regression test caught `<command-args>` leaking too, not just `<command-message>`.

**Measured before deciding**, since the seam is frozen:
- 60 of 93 live extracts carried a leak; 78 of 92 pieces sat at index `[1]`, the opening line
- the payload was always the entry-point skill name — `wayfinder` ×59, `implement` ×12
- six sampled entries were unaffected ("Verify ingest schemas against real payloads", "Greybox the what-view prototype") — the what-pass tolerated it, exactly as this ticket predicted
- the sidecar map's *contents* are never read; `analyze.py:765` and `import_backfill.py:47` only test that the file exists. The why-pass that would have consumed index→uuid was cut in ADR-0006, so renumbering pieces costs nothing — which removed the main cache worry raised here

**Invalidated for the re-audit:** 177 files (extracts + cached what-pass outputs) across 65 sessions with live transcripts, now `pending`. Audit rows deliberately left in place — the what-view derives "pending" from a *missing audit row*, not from `sessions.status`, so entries stay visible until their replacement lands instead of blanking in the interim.

**Not re-runnable:** nine backfill-imported sessions keep the leak, their transcripts being gone — nothing to re-extract from. The `eval/` and `dogfood-week2/` extract dirs are artifacts rather than pipeline inputs and were left alone.

The re-audit itself lands on the next analysis run: 65 what-pass calls, haiku, one-off. A db backup sits at `local-data/hindsight.db.bak-66` until it completes.

