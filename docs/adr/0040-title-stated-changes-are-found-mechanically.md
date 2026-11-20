# ADR-0040: Title-stated changes are found mechanically, and the card must carry the strong ones

**Date:** 2026-11-20 · **Status:** proposed · **Amends:** ADR-0035 (§2, §4, §6) · **Decides:** issue #96 (map #59, v2 audit core)

## Context

ADR-0035 §4 leaves a project with no ADRs to take its Superseded lines from titles that state the change in their own words, and §2 leaves all of that judgement to the narrative. The `status-v2` eval shows Haiku does not do this reliably, and prompt rules have not fixed it.

- **The failure.** Across the five clean, serial Haiku sweeps (`v2-p7` ×3, `v2-p9`, `v2-p10`), `thisisme@live` failed 5 of 15 calls. Every miss was a change stated only in a run title. In `v2-p10` r1 the model copied "Paused schema ticket, inverted to content-first ordering" word for word into Standing and Now, and wrote no Superseded line.
- **Prompt rules have not moved it.** The prompt already names the closed verb list and gives an example almost the same as the missed title. `v2-p8` added a title-pass rule and over-fired. `v2-p10` added an instruction to search every part of every title, and the target got worse: 3 misses in 3 rounds, against 1 for `v2-p9`.
- **The verb list is already mechanical.** It is a closed list of words, applied to the parts of a title. A plain match over the five frozen cases (split on `;` and `,`) finds:
  - **strong verbs** (drop, kill, retire, remove, replace, invert): 5 unique matches, all of them genuine changes;
  - **"close"**: 9 unique matches, only 1 of them a genuine change ("close OpenSpec"). Four name a ticket, map or issue. The others close research, a palette decision or a restyle.

## Decision

1. **`cli/how.py` derives title changes from the run ledger.** It splits each title into parts on `;` and `,`, and matches the closed verb list as whole words in any tense. Each match is a **title change**: its run's dates, the part verbatim, and its kind.
   - **strong**: drop, kill, retire, remove, replace, invert.
   - **close**: close, unless the same part names a ticket, map, issue, phase or `#N`. Such a part is finished work and is not a title change.
2. **The narrative's input gains `changes` beside `runs` and `adrs`.** They are derived from `runs` at call time, by the same function in the live pass and in `eval/run_v2.py`. The frozen cases stay as they are.
3. **Every strong change gets a Superseded line.** A close change gets one only when a thing was abandoned. That judgement stays with the model, under `status-v1`'s existing rule. The prompt replaces its "read every title for these verbs" instruction with "read `changes`".
4. **The write-time gate gains M7, Listed:** every strong change shares at least two content words with some Superseded line. It is ground-truth-free, because it reads only the input. So it joins `contract_v2` and binds the eval and the live pass alike. A card that drops a strong change is refused, and the next run retries.
5. **The eval floors gain M7 before the next prompt is written.** No case, anchor or existing floor moves. Earlier runs are re-scored under M7 for the record only.

This amends ADR-0035 §2: a title-stated change is now found by code, not by the narrative. Supersession by ADRs is still judged by the narrative. A run is still never marked. It also amends §4: the "Otherwise the list is empty" rule now applies to close changes the model judges as finished, and to projects with no changes at all. And it amends §6: the gate grows by M7.

## Alternatives rejected

- **More prompt rules.** Three attempts (the existing rule, `v2-p8`, `v2-p10`) have not moved the miss rate, and two made it worse.
- **Code writes the Superseded lines.** A line needs both sides of the change. A title such as "killed model-only approach" names the old thing, but not always what replaced it. "close" still needs judgement.
- **Pass close matches without the ticket filter.** Eight close matches for `hindsight@live` alone, seven of them finished work. That is the over-firing `v2-p8` showed.
- **Escalate to Sonnet.** Clean runs put Sonnet behind Haiku (10/15 against 14/15 on the same prompt), and it fails the explainer ADR-0010 fact more often.
- **Loosen the bar.** The operator kept 15/15 (2026-11-20). M2 fired in clean runs, so a split bar would not have accepted any prompt so far.

## Consequences

- The model input grows by one short list. For the frozen cases, that is at most 3 strong and 5 close changes per project.
- Superseded can grow by up to the number of strong changes. `hindsight@live` would carry its 2 ADR facts plus 3 strong changes: 5 lines, within the cap of 6.
- A strong verb used for something that is not a change becomes a mandatory Superseded line. None occurs in the frozen data. If one appears live, the fix is in the verb list, not in the prompt.
- Two failures are left untouched:
  - the explainer case naming the wrong half of ADR-0010's title (2 of 15 Haiku calls);
  - the 300 s `CALL_TIMEOUT`, hit once with a single call in flight.
- CONTEXT.md: **Superseded** changes ("judged by the narrative" covers ADR-drawn lines only), and **Title change** is added. Both wait until this ADR is accepted.
