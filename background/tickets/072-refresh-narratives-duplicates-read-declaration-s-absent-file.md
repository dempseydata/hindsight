# #72 refresh_narratives duplicates read_declaration's absent-file check (ADR-0011 single read location)

state: closed · labels: bug · opened: 2026-08-29 · closed: 2026-08-29

Surfaced by code-review during #70, pre-existing.

## ~~run_ledger crashes on an undated grain~~ — fixed in 671c305 (#74)

`run_ledger` did `r["events"][0]["at"][:10]` / `[-1]["at"][:10]` on a nullable `at`. Fixed at the shared spot as this ticket asked: `run_ledger` now skips an event with no timestamp when banding, so an undated grain can never reach a run edge. A run's start/end is a day and `None` has none; the event stays in the trail, the aggregates and the off-script list — only the band skips it.

It came back into view during #74 because `local_day(None)` returns `""` where `[:10]` raised, turning the crash into a silently empty run boundary that got hashed into the ledger and passed to `eval/score.py`'s `md()`. Quieter, and worse.

## What remains

`analyze.refresh_narratives` re-implements the absent-declaration `is_file()` check that `how.read_declaration` already performs. The following `state != "valid"` test already covers it, so the pre-check is a duplicate that can drift from ADR-0011's single read location.

Small, and in the same function as #77 — worth doing together.



---

**comment · 2026-08-29**

Primary half fixed in 671c305 while landing #74 — the guard went into `run_ledger`, the shared spot this ticket named. Title and body trimmed to the `refresh_narratives` duplicate, which is untouched and sits in the same function as #77.


---

**comment · 2026-08-29**

Fixed in 6cd31d7, alongside #77 as this ticket suggested.

The `is_file()` duplicate is gone. One deviation from the literal ask, worth recording: removing the pre-check entirely — leaning on the `state != "valid"` test after `how_data` — would have made every **non-declaring** project pay `how_data`'s full per-project event scan on every analysis run, which the short-circuit existed to avoid. So the short-circuit stays, but now asks `how.read_declaration` directly:

```python
if how.read_declaration(Path(projects_dir) / project)[0] != "valid":
    continue
```

That satisfies what ADR-0011 actually requires — one place where the declaration-reading *logic* lives — without paying the scan. It costs a second `read_declaration` call for declaring projects (one small file read), which is the cheaper side of the trade and cannot drift, both calls going through the same function.

