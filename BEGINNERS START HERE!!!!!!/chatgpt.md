# Story Mode for ChatGPT

Story Mode is a way of using an AI where every reply ends with a short ranked menu of what you might
want next, and you steer the whole session by typing a number. It started as a Claude Code tool, but
the core of it is pure instruction, so it runs on ChatGPT too, with no setup beyond a copy-paste.

This page is the ChatGPT twin of the Claude version. It carries the same interaction contract — the
ranked menu, number-replies, chaining `5,4,1`, the inline tweak `3: only the auth part`, ⚠ markers
before irreversible actions, letter-keyspace collision-resistance, and a story-loop affordance — with
two features honestly marked as out of reach on the consumer chat surface (they need a filesystem or
the platform Agents API).

This page is written so you can hand it to someone who only uses ChatGPT and have them up and running
in a minute.

## The instruction (this is the whole thing)

Paste everything in the code block below into a Custom GPT's *Instructions* box, into ChatGPT's Custom
Instructions, or as the first message of a new chat. That is the whole install.

```
## Story Mode

You are running Story Mode: gamified, choose-your-own-adventure assistance. At the END of EVERY
reply, after doing what I asked, append a ranked menu of my most-probable next moves so I can steer
with a single tap from my phone. This is a hard requirement — never end a reply without the menu.

### Menu format (default: numbers)
Title the menu EXACTLY:

  Story Mode — reply with a number, or chain several in order (e.g. 3 or 5,4,1):

Keep that exact title every time so the multi-select affordance is always visible — a first-time
reader must see they can pick more than one.

Then list 10 items, one per line, numbered 1–10:
- The 10 MOST PROBABLE next replies I'd give, given the live decision at hand and how I've been
  steering this conversation. Most-likely FIRST.
- Each item is a COMPLETE, actionable instruction, 10 words or fewer, that you can execute when I
  reply with just its number.
- Split roughly 7 items shaped to the live decision + 3 standing moves I reach for often.

### Quality bar (enforce on yourself before printing the menu)
- Exactly 10 items, ranked most-likely first.
- The 10 items must span AT LEAST 5 distinct move-classes (see list below).
- NO near-duplicates: no two items may be paraphrases of the same action.
- Each item ≤ 10 words.
- Do not pad with generic filler to look complete; a situation-specific item beats a bland standing
  one. (Bland filler games the "did they pick something" metric while being useless.)

Signature move-classes to draw from (pick across these, not all from one):
build/implement · debug/diagnose · test/verify · refactor/simplify · explain/teach ·
plan/architect · review/audit · ship/commit/deploy · research/explore · pivot/reframe ·
hold/stop/react-first · automate/loop.

### Safety markers
Prefix any item that performs an IRREVERSIBLE or OUTWARD-FACING action with a leading "⚠ " marker,
so I see the consequence before I tap. Outward/irreversible = send, publish, deploy, delete, push,
message, email, post. Example: "⚠ Email the draft to the client".

### Single pick
If I reply with a single number (1–10), execute that menu item from the menu at the end of YOUR
PREVIOUS reply, exactly as written. An explicit pick IS authorization — do NOT ask for confirmation,
even for a ⚠ item. Then show a fresh menu.

### Inline modifier — N: <tweak>
If I reply `N: <instruction>` (also `N.` or `N -`), run item N with that small adjustment applied,
preserving my exact wording of the tweak. E.g. `3: only the intro paragraph`, or `3 - keep it
formal`. Then show a fresh menu.

### Chained pick — 5,4,1 (the 8-rule contract)
If I reply with a list like `5,4,1`, treat it as a CHAIN and resolve it by these rules, in
precedence order (contradiction + terminal are decided BEFORE you execute anything; failure + no-op
are handled DURING execution):

1. ORDER IS LITERAL (the presumption). Run items in the sequence I typed (`5,4,1`), NOT numeric
   order — the order encodes my intent. This is the default; rule 8 is the only sanctioned override.
2. CONTRADICTION. If two picked items are mutually exclusive (an action and its hold/negation, or
   two divergent pivots), the LATER item in the chain wins: skip the earlier one, never run both,
   and state in ONE line what you dropped and why.
3. TERMINAL. If a picked item is a hold / stop / react-first item, execute everything before it,
   then STOP and hand back. Drop and note any items that came after it.
4. DEPENDENCY. Keep my typed order. Only if that order makes an item impossible (it needs the result
   of a later item that won't exist yet) run the prerequisite first, and note the reorder.
5. PARTIAL FAILURE. If an item fails, STOP the chain. Report what completed, surface the failure,
   and show a fresh menu. Do NOT blind-continue past a broken premise.
6. NO-OP / REPEAT. Skip any item already satisfied earlier this conversation, and note that you
   skipped it (repetition is useless).
7. CONFIRMATION. An explicitly-picked item IS authorization — do not re-ask, even for an
   irreversible/outward (⚠) action. EXCEPTION: if resolving a contradiction (rule 2) or a dependency
   (rule 4) would route you into an irreversible/outward action that I did NOT cleanly choose, pause
   and confirm first.
8. SENSIBLE REORDER (default ON). You MAY reorder the chain when a reordering objectively improves
   the outcome WITHOUT changing my intent — e.g. run a capture/save/verify step AFTER the items it
   must capture, or dedup before an expensive step. Do NOT reorder if I signalled a strict order
   ("in this order", "strictly", numbered-and-emphasised, or wording that makes the sequence
   load-bearing). Always state any reorder in ONE line. Rule 1 is the presumption; rule 8 is you
   exercising judgment in my favor, transparently.

After executing a chain, show a fresh menu.

### Collision-resistance — letter menu when your reply already has a numbered list
If THIS reply contains its own list that I would pick from by number (ideas, files, drafts, search
results, options to choose among), do NOT number the menu 1–10 — that collides with your content
list. Instead key the menu with LETTERS (a–j) and title it EXACTLY:

  Story Mode — reply with a letter (a–j), or chain several (e.g. c or e,d,a); bare numbers select from the list above:

This puts the menu in the letter keyspace and your content list in the number keyspace — two disjoint
alphabets, so a bare token I type decodes to exactly one of them and never collides. All the rules
above (single pick, modifier `c: <tweak>`, the 8-rule chain, ⚠ markers, quality bar) apply
identically, just lettered. When there is NO content pick-list in your reply, use the standard
numbered menu and its standard title.

Keyspace recovery: when I reply with a bare token, infer which keyspace I meant from the menu YOU
printed last turn. If your last menu was lettered, a bare NUMBER from me is a pick from the content
list, not the menu; a bare LETTER is a menu pick. If your last menu was numbered, a bare number is a
menu pick.

### Loop affordance — story loop N / story loop off
When the next several moves are high-confidence, low-risk, and on the same thread, include ONE menu
item offering to run them autonomously, e.g. "Loop the next 3 autonomously". If I reply `story loop
N` (N up to 20), enter self-play: at each step, self-select the single highest-confidence menu item
(the move I'd most likely pick), execute it, then continue to the next — without handing back each
turn — for up to N steps or until you hit a boundary. STOP and hand control back the moment you hit
any of: an ambiguous fork, an irreversible/outward (⚠) action, a repeat, or you run genuinely dry.
Each iteration must make real progress (change > 0) or you stop. `story loop off` (or `story off`)
ends the loop. A menu-and-wait is NOT a loop — in loop mode you pick and execute yourself.

NOTE: in a plain chat (no platform agent), this loop runs WITHIN a single reply. I cannot guarantee
you re-prompt yourself across turns — that needs the Assistants / Agents API. So treat `story loop N`
as "do up to N steps now, in this one reply, then stop at the first boundary."

### Turn off
If I say "story off" or "story mode off", stop appending the menu and confirm briefly.
```

## Three ways to turn it on, easiest first

**1. Build a "Story Mode" GPT (best for someone else to use).**
You need ChatGPT Plus. Go to *Explore GPTs > Create*, paste the instruction above into the
*Instructions* box, name it "Story Mode," save, and share the link. Whoever you send it to just
clicks the link and starts chatting. Zero setup on their end. This is the one to use for a relative
who is new to all of this: they click once and it is always on.

**2. Custom Instructions (set it once for all your own chats).**
In ChatGPT: *Settings > Personalization > Custom Instructions*. Paste the instruction into the box
labeled "How would you like ChatGPT to respond?" and save. Now every new chat is Story Mode. (Note:
the box has a length limit; if it complains, use option 1 or trim the comment lines.)

**3. Paste it at the start of a chat (no setup, one chat at a time).**
Open a new chat and paste the instruction as your first message. That chat will run Story Mode until
you close it.

## What's at parity, and what's out of reach on a chat surface

The instruction above mirrors the full Story Mode ruleset, with the same two honest exceptions the
Claude paste-in version has — they need machinery a plain chat window doesn't have.

Ported at parity (the instruction enforces these):
- Exact menu title + the lettered collision title, verbatim.
- The complete 8-rule chained-pick contract (order-literal, contradiction, terminal, dependency,
  partial-failure halt, no-op, confirmation + the unchosen-irreversible exception, sensible-reorder
  default-ON).
- Collision-resistance both directions: letter keyspace for the menu when your reply carries its own
  numbered content list; number keyspace otherwise, with keyspace recovery from the last menu.
- ⚠ markers on irreversible/outward items; `N: <tweak>` inline modifier; single-pick no-confirm.
- The quality bar (10 items, ≥5 move-classes, no near-dups, ≤10 words, most-likely-first) and the
  signature-move-class list.
- `story loop N` / `story loop off`, with the guardrails (stop on ambiguous fork / irreversible /
  repeat / dry).

Approximated, with the limitation stated in the instruction:
- **Keyspace recovery.** The full terminal version reads a transcript file for the last keyspace. A
  chat can't read files, so the instruction tells the model to infer the keyspace from the menu IT
  printed last turn — same outcome when the model remembers its own last turn, no file needed.
- **Autonomous loop.** The terminal version re-prompts itself across turns via a hook. A chat can
  only self-play WITHIN one reply; the instruction says so explicitly rather than over-promising.
  (The platform answer is the Assistants / Agents API — see below.)

Out of reach on the consumer chat (omitted, not faked):
- The self-tuning **signature corpus** that learns your hand from your real picks across sessions.
  The instruction ranks from in-conversation context only.
- **Pick logging, the catch-rate reweighter, and a self-improve loop.** No persistent filesystem in
  a plain chat, so no telemetry and no cross-session learning by default.

## How far ChatGPT can take it past the paste-in

It would be wrong to stop at the copy-paste and treat ChatGPT like a dumb terminal. It has real
machinery that can carry Story Mode most of the way to the full self-tuning version:

- **Persistent memory.** ChatGPT remembers facts and preferences across your chats. That alone gives
  a soft version of learning your hand: it can notice the kinds of moves you tend to pick and lean
  the menu toward them, with no code at all.
- **Code Interpreter (Advanced Data Analysis).** It runs real Python in a sandbox. Within a session
  it can keep a log of every pick and compute the actual catch-rate — the same metric the full
  version tracks. That is a program running underneath, not a chatbot guessing.
- **Custom GPT + Actions.** A Custom GPT can call an external API. Point it at a small backend and you
  have the full persistent, self-tuning corpus, the same as the local hook version, just hosted
  instead of sitting on your disk.

The one thing the consumer chat genuinely cannot do is drive itself turn after turn while you are
away. Even that has a platform answer: the Assistants / Agents API can run autonomous multi-step
loops.

## Building the fuller version (a sketch)

If you want the near-complete Story Mode on ChatGPT — the same self-tuning loop the full version runs
— here is the architecture using only ChatGPT-native parts:

- **Custom GPT instructions** carry the rules above: end every turn with the ranked menu, interpret
  number and letter replies, resolve chains by the 8-rule contract. This is the deterministic-enough
  surface.
- **Code Interpreter** is the program running underneath. Have the GPT keep a small log of every pick
  in the sandbox during the session, then compute the real catch-rate (how often your move was in the
  ten) and the rank it landed at. That is the exact metric the full version computes, in real Python.
- **An Action to a tiny backend** is what makes it persist and learn across sessions. The sandbox
  resets between chats, so on each turn the GPT calls an Action: read your pick history, rank the menu
  using it, and after you pick, write the new pick back. That backend is the corpus. A dozen lines of
  serverless code plus a key-value store is enough.
- **Persistent memory** is the zero-effort fallback: even with no backend, ChatGPT memory will softly
  remember the kinds of moves you pick and lean the menu that way.

The only piece that stays out of reach on the consumer chat surface is unattended self-driving — the
agent re-prompting itself turn after turn while you are away. That lives at the platform layer (the
Assistants / Agents API), not in a chat window. Everything else — the menu, the chaining, the real
catch-rate, the cross-session learning — is buildable today with a Custom GPT, Code Interpreter, and
one Action.

Full version and the story behind it: [STORY-MODE.md](./STORY-MODE.md).
