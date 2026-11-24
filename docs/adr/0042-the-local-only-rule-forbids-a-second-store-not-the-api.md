# ADR-0042: The local-only rule forbids a second store, not the API

**Date:** 2026-11-24 · **Status:** accepted · **Decides:** issue #123 (map #118, dashboards v2)

## Context

The README said hindsight's derived data "never leaves" the machine. That was never literally true. Every analysis run sends transcript extracts of up to ~180 KB to the Anthropic API through `claude -p`: the what-pass, its merge call and the how-view's status narrative (ADR-0002, ADR-0003, ADR-0012). In practice the rule hindsight has kept is narrower: no copy outside the machine that hindsight writes or controls, and nothing leaving except inside a Claude session.

Map #118 adds a read-only MCP server so the store can be queried from a conversation. Its results go to the API and are kept there under Anthropic's retention terms. They are also kept in the account's conversation history when the client is the desktop app's chat. Under the literal rule the server cannot exist. Under the rule hindsight has actually kept, it can.

The `v2-framing.md` routing table already applied the narrower rule. It rejected an Artifact page's `db` because hindsight would push aggregates into a store on claude.ai with no session in between. It did not reject the API as such.

## Decision

1. **The local-only rule.** Hindsight's store, and every copy it writes or controls, stays on the machine. Data reaches Anthropic only inside a Claude session the operator runs: hindsight's own `claude -p` passes, or a conversation the operator starts. It is then kept on the same terms as the sessions it came from.
2. **An operator-initiated MCP query is within the rule.** It uses the same channel as the what-pass, driven by a person instead of a job.
3. **What an MCP tool may return:**
   - **Aggregates:** tokens, counts and rates.
   - **Identifiers:** session ids, project names and skill names.
   - **Summary text:** audit entries and status narratives.
   - **Not verbatim `error_text`** (ADR-0027). It is raw tool output: the likeliest carrier of instructions injected into the querying agent, and of a secret that appeared in a failed command. A tool may return error counts and error classes instead.
4. **Current project by default.** A tool answers for the project the querying session sits in. All-projects results need an explicit argument. This keeps a private project's names and text out of a session in another repo, including this public one, unless they are asked for.
5. **Any local client.** The server is stdio and registered by the plugin. Claude Code and the desktop app's chat may both use it. Conversation history in the operator's own account is the same terms as the source sessions, not a store hindsight controls.
6. **The self-observation loop is accepted.** A query result lands in the querying session's transcript, which hindsight then ingests and sends through the what-pass. Querying hindsight is something that session did. Self-exclusion (ADR-0003) stays limited to hindsight's own `claude -p` runs.

## Alternatives rejected

- **The literal rule: no derived data ever leaves.** It is already false because of the what-pass. Holding to it would rule out the MCP server and keep a public claim hindsight does not meet.
- **Aggregates only.** It removes the injection and leakage risks, but it also removes the what-view's content, which is the main thing a conversation would ask about. The risks come from verbatim tool output and from cross-project scope, and items 3 and 4 address those directly.
- **All projects by default, as the dashboard does.** A dashboard is read by the operator. An MCP result is read by an agent that can write commits and issue bodies in whichever repo it sits in.

## Consequences

- The README's privacy line is corrected in the same change. It is a public claim, and it overstated what hindsight does.
- `CONTEXT.md` gains **Local-only rule**.
- Issue #125 (what the server exposes) inherits items 3 and 4 as constraints. It decides only which queries become tools, and in what shape.
- The pre-commit denylist still guards commits. Nothing guards an issue body a querying agent writes. The current-project default is the only defence there.
