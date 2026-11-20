# ADR-0035: The status card is a current-state summary, with supersession judged from ADR headers

**Date:** 2026-11-16 · **Status:** accepted; §2, §4 and §6 amended by ADR-0040 · **Amends:** ADR-0012 · **Decides:** issue #64 (map #59, v2 audit core)

## Context

ADR-0012's status narrative is an aggregate. `status-v1` lists everything ever built under **Built** and repeats a reversed item under **Reversed**. The v2 charting session settled that the how-view should read as a current state instead: later decisions overwrite earlier ones, and the history stays reachable.

A throwaway prototype (branch `prototype/064-current-state`, never merged) ran on hindsight's and explainer's real ledgers on 2026-11-15. It produced three cards per project, and each prototype prompt ran twice:

- **A**, the stored `status-v1` card;
- **B**, a current-state prompt over the run ledger alone;
- **C**, the same prompt with the project's ADR headers as a second input.

What it showed:

- **The titles rarely say what was superseded.** Only 4 of hindsight's 49 ledger titles use reversal words. Neither of its two largest reversals appears in any title: the so-what view dropped (ADR-0026) and hook self-instrumentation retired (ADR-0005 → ADR-0033). Card A lists the so-what view under Built and never mentions the drop.
- **B missed both and invented a link.** In one run it wrote "model-only pattern detection → ADR-0023", which neither the titles nor the decisions state.
- **C found both in each run**, and on explainer it found the npm-link install replaced by the plugin layout (ADR-0011).
- **C is limited by ADR status lines.** It reported "v1 ships two views", because ADR-0006 is not marked as amended by ADR-0010.
- **Only 2 of the 5 declaring projects have ADRs.**

## Decision

1. **The card is a current-state summary:** three groups, **Standing**, **Superseded** and **Now**, in a new prompt version `status-v2`.
   - Anything later overwritten leaves Standing and appears only under Superseded. Each Superseded line takes the form *what it was (date) → what replaced or dropped it (date)*.
   - Now is unchanged.
2. **Supersession is judged in the narrative and never marked on the runs.** Two runs of the same stage are different work, not one replacing the other. The run ledger stays purely mechanical.
3. **The narrative gets the project's ADR headers as a second input, next to the run ledger.** The headers are read mechanically: number, date, title, status line and touches/amends. The ADR header supplies the evidence; the model judges what it means. The date comes from the header, or else from the commit that added the file.
4. **A project with no ADRs** gets Superseded only from a title that states the change in its own words, keeping `status-v1`'s rule. Otherwise the list is empty and never inferred.
5. **History stays reachable through the run ledger, kept complete and never rewritten below the card.** A Superseded line carries both dates, so it traces to the runs on either side. There is no separate history store and no collapsing of old runs.
6. **A line may trace to a ledger run (by its dates) or an ADR (by its number and date).** The write-time gate changes to match:
   - a Superseded line carries two dates, each found in the ledger or the decisions input;
   - a line drawn from an ADR names its number;
   - Standing stays at 3–8 lines.
7. **An ADR that supersedes or amends another updates the earlier one's status line** ("superseded by ADR-N" / "amended by ADR-N"). This is trialled in this repo's process copy and promoted to the house master if it holds. Fixing hindsight's existing unmarked ADRs is part of the build scope.
8. **The `status-v2` eval set and threshold are decided before the prompt is written** (the ADR-0012 discipline). It needs supersession answers checked against real data, including one project with no ADRs whose Superseded must stay empty.

## Alternatives rejected

- **Marking supersession on the runs.** There is no mechanical rule for it: a later Build run does not replace an earlier one.
- **Narrative over titles only (B).** It missed every real supersession on hindsight and invented one.
- **A separate store for superseded history, or collapsing old runs.** That is a second copy of the audit trail that can drift from the first. The ledger already is the trail.
- **Keeping the aggregate card.** It presents dropped work as standing.

## Consequences

- The narrative's input grows by one header per ADR: 34 for hindsight today. Its key now includes the ADR headers, so editing an ADR's status line regenerates the card.
- C's Standing describes the decisions now in force, not just the work done. It is only as accurate as the ADR status lines (decision 7).
- The wording varied a lot between prototype runs, though the supersessions it found did not. The eval measures this; it is not settled here.
- CONTEXT.md: **Status narrative** and **Run ledger** change; **Superseded** is added.
