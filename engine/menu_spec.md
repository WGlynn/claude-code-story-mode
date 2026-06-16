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
numbered list. The resolver accepts either namespace (see `chained_pick.py`).

## Reply grammar (interpret against this menu next turn)

- `3` → run item 3.
- `5,4,1` → run items 5, 4, 1 in that literal order (order encodes intent).
- `3: only the auth part` → run item 3 with the tweak.
- `story loop 4` → autonomously self-select and run for the next 4 turns;
  stop and hand back on an ambiguous fork, an outward/irreversible action, or a
  repeat.

See `chained_pick.py` for the full resolution contract (literal order;
later-wins on contradiction; terminal item halts; skip already-done).
