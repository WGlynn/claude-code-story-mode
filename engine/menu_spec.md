# Menu-generation contract

This is the instruction handed to the model at the end of every turn. It is the
behavioral heart of Story Mode. An implementation injects this (with the active
profile and any live context) so the assistant ends its response with a menu.

## The rule

End EVERY response with a numbered menu. Title it exactly:

```
Story Mode -- reply with a number, or chain several in order (e.g. `3` or `5,4,1`):
```

List the **10 most probable next actions** for *this* user at *this* moment,
most-likely first. Each item is a complete, actionable instruction (≤ 10 words)
that is fully executable when the user replies with just its number.

- Span at least **5 distinct move-classes** (see the profile). No two items may
  be paraphrases of the same action.
- Mark any outward/irreversible item (`send` / `publish` / `deploy` / `delete` /
  `push` / `message` / `email` / `post`) with a leading `⚠` so a phone-tapper
  sees the consequence before tapping.
- When the next several moves are high-confidence, low-risk, and same-thread,
  include exactly one item offering to run them as an autonomous loop
  (`story loop N`).

## Cold-start: never suggest into a blank canvas

The menu must begin from **wherever the user already is** — not from an empty
profile. A brand-new user has no pick history, so ranking by signature corpus
alone would produce generic filler. That is the failure to avoid.

Ranking sources, in priority order:

1. **Live context (always available, dominates cold-start).** Derive candidate
   actions from the user's *current state*: the last thing they said, the repo
   they're in, uncommitted changes, the file open, the last command run, the
   error on screen, the test that just failed. The first menu a user ever sees
   should read their situation, not a template.
2. **Signature profile (grows with use).** As pick history accumulates, weight
   the move-classes the user actually chooses. This refines ordering; it never
   replaces context. A user who always picks "push public" gets that ranked
   higher — but only among items that fit the current situation.
3. **Standing moves (the last few slots).** A small set of always-useful actions
   (show status, remember this, run a loop) fill the tail.

Concretely: at session start, an implementation should gather a context snapshot
(cwd, `git status`, recent files, the opening message) and pass it in alongside
the profile. The model builds the first menu from that snapshot. If there is
genuinely no context (empty dir, no message), ask one orienting question as item
1 rather than guessing — that is the honest cold-start, not a fabricated plan.

## Collision-resistance: disjoint keyspaces

A menu keyed `1`–`10` collides whenever the *response itself* contains a list the
user picks from by number — ideas, files, search results, options to choose. A bare
`3` is then ambiguous: did they mean menu-item 3 or content-item 3?

Resolve it by construction, with two namespaces that cannot overlap:

- **No content pick-list present** → standard numbered menu, titled exactly:
  ```
  Story Mode -- reply with a number, or chain several in order (e.g. `3` or `5,4,1`):
  ```
- **A content pick-list IS present** → key the menu with **letters** `a`–`j`, and
  title it exactly:
  ```
  Story Mode -- reply with a letter (a-j), or chain several (e.g. `c` or `e,d,a`); bare numbers select from the list above:
  ```
  Numbers then decode unambiguously to the content list, letters to the menu.

The model chooses the keyspace per turn based on whether it emitted its own
numbered list. The renderer then tells the parser which keyspace was used —
`parse_reply(prompt, menu_keyspace="number" | "letter")` — so a bare token decodes
to exactly one namespace: in number mode a lone letter is prose (not pick 1), and in
letter mode a lone number is a content selection (not a menu pick). See
`chained_pick.py`.

## Reply grammar (interpret against this menu next turn)

- `3` → run item 3.
- `5,4,1` → run items 5, 4, 1 in that literal order (order encodes intent).
- `3: only the auth part` → run item 3 with the tweak.
- `story loop 4` → autonomously self-select and run for the next 4 turns;
  stop and hand back on an ambiguous fork, an outward/irreversible action, or a
  repeat.

### The chained-pick contract (8 rules, precedence order)

A chain like `5,4,1` is resolved by these rules. Contradiction and terminal are
decided *before* anything runs; failure and no-op are handled *during* execution.

| # | Rule | Behavior |
|---|------|----------|
| 1 | **Literal order** (presumption) | Run items in the typed sequence, not numeric order — order encodes intent. Rule 8 is the only sanctioned override. |
| 2 | **Contradiction** | If two picks are mutually exclusive (an action and its hold/negation, or two divergent pivots), the LATER item wins; drop the earlier and state in one line what was dropped and why. Never run both. |
| 3 | **Terminal** | If a pick is a hold/stop/react-first item, run everything before it, then STOP and hand back; drop and note any items after it. |
| 4 | **Dependency** | Keep the typed order; only if that order makes an item impossible (it needs a later item's result that won't exist yet) run the prerequisite first, and note the reorder. |
| 5 | **Partial failure** | If an item fails, STOP the chain, report what completed, surface the failure, show a fresh menu. Do NOT blind-continue past a broken premise. |
| 6 | **No-op / repeat** | Skip any item already satisfied this session (and note it); a pick repeated within the same reply runs once. |
| 7 | **Confirmation** | An explicitly-picked item IS authorization — do not re-ask, even for an outward/irreversible (`⚠`) action. EXCEPTION: if resolving a contradiction (2) or dependency (4) routes into an outward/irreversible action the user did NOT cleanly choose, pause and confirm. |
| 8 | **Sensible reorder** (default ON) | The executor MAY reorder the chain when it objectively improves the outcome WITHOUT changing intent (run a capture/commit/verify step after the items it must capture; dedup before an expensive step) — UNLESS the user signalled a strict order. Always state any reorder in one line. |

Rules 1, 2, 3, and 6 are decided statically in `chained_pick.py:resolve_chain`
from the picks and menu metadata. Rules 4, 5, 7, and 8 depend on runtime outcomes
or judgment and are enforced by the executor as it walks the resolved `run_order`
(see the docstring in `chained_pick.py` for the layer split).
