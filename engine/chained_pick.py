"""Chained-pick grammar — parse and resolve a user reply against the last menu.

This is the novel core of Story Mode. A user's reply is interpreted relative to
the ten-item menu that ended the previous assistant turn. The mechanical parsing
(what did they pick, in what order, with what modifier) lives here in pure code.
The two rules that need meaning — is item A the negation of item B (contradiction),
is item C a "stop" item (terminal) — are driven by metadata the menu carries, so
this module stays deterministic and testable. No LLM call happens in here.

Stdlib only. Public, user-agnostic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MenuItem:
    """One row of a menu. `text` is shown; the rest drives chain resolution."""
    n: int
    text: str
    warn: bool = False          # outward/irreversible (send/deploy/push/delete/post)
    terminal: bool = False      # a hold/stop item: run earlier picks, then hand back
    conflict_group: Optional[str] = None  # items sharing a group are mutually exclusive


@dataclass
class ParsedReply:
    picks: list[int] = field(default_factory=list)  # menu numbers, in typed order
    modifier: str = ""          # "N: tweak" -> the tweak text (single-pick only)
    loop_n: Optional[int] = None  # "story loop N"
    toggle: Optional[str] = None  # "on" / "off"
    is_menu_reply: bool = False   # True if this parsed as picks/modifier/loop/toggle
    content_pick: bool = False    # a bare number that selects from a CONTENT list the
                                  # response showed, not the (lettered) menu. The caller
                                  # routes it to content selection, not chain execution.


_PICKS = re.compile(r"\s*(\d{1,2}(?:\s*[,\s]\s*\d{1,2})*)\s*$")
_LETTER_PICKS = re.compile(r"\s*([a-jA-J](?:\s*[,\s]\s*[a-jA-J])*)\s*$")
_MODIFIER = re.compile(r"\s*(\d{1,2})\s*[:.\-]\s+(.+)", re.DOTALL)
_LETTER_MODIFIER = re.compile(r"\s*([a-jA-J])\s*[:.\-]\s+(.+)", re.DOTALL)
_LOOP = re.compile(r"story\s+loop\s+(off|\d{1,2})", re.IGNORECASE)

MAX_LOOP = 20  # hard ceiling on autonomous self-play iterations (safety)


def parse_reply(prompt: str, menu_size: int = 10,
                menu_keyspace: str = "number") -> ParsedReply:
    """Turn a raw user prompt into a structured reply against the last menu.

    `menu_keyspace` is the keyspace the PREVIOUS menu was rendered in, and it is
    what makes the parse collision-proof:

      - "number" (default): the menu was `1`-`10`. Bare numbers are picks; bare
        letters are NOT picks (they are prose -- "a" and "i" are words), so a
        letter reply parses as a non-menu message instead of hijacking pick 1/9.
      - "letter": the menu was `a`-`j` because the response also carried a numbered
        content list. Letters are picks; a bare NUMBER is a selection from that
        content list (content_pick=True, not a menu reply) so the two namespaces
        never collide.

    Pass the keyspace the renderer actually used last turn. Toggles and `story
    loop N` are keyspace-independent and always recognized.
    """
    p = (prompt or "").strip()
    low = p.lower()

    # Keyspace-independent commands.
    if low in ("story off", "story mode off"):
        return ParsedReply(toggle="off", is_menu_reply=True)
    if low in ("story on", "story mode on", "activate story mode"):
        return ParsedReply(toggle="on", is_menu_reply=True)
    lm = _LOOP.fullmatch(low)
    if lm:
        arg = lm.group(1)
        n = 0 if arg == "off" else min(int(arg), MAX_LOOP)  # cap autonomous iterations
        return ParsedReply(loop_n=n, is_menu_reply=True)

    if menu_keyspace == "letter":
        # Letters are menu picks; numbers belong to the content list, not the menu.
        lp = _LETTER_PICKS.fullmatch(p)
        if lp and len(p) <= 24:
            cand = [ord(c) - 96 for c in re.findall(r"[a-j]", lp.group(1).lower())]
            if cand and all(1 <= x <= menu_size for x in cand):
                return ParsedReply(picks=cand, is_menu_reply=True)
        lmod = _LETTER_MODIFIER.match(p)
        if lmod:
            n = ord(lmod.group(1).lower()) - 96
            if 1 <= n <= menu_size:
                return ParsedReply(picks=[n], modifier=lmod.group(2).strip(),
                                   is_menu_reply=True)
        # A bare number here selects from the content list -> not a menu reply.
        mm = _PICKS.fullmatch(low)
        if mm:
            cand = [int(x) for x in re.findall(r"\d{1,2}", mm.group(1))]
            if cand and all(1 <= x <= menu_size for x in cand):
                return ParsedReply(content_pick=True, is_menu_reply=False)
        return ParsedReply(is_menu_reply=False)

    # Number keyspace (default): numbers are picks; letters are prose, not picks.
    mm = _PICKS.fullmatch(low)
    if mm:
        cand = [int(x) for x in re.findall(r"\d{1,2}", mm.group(1))]
        if cand and all(1 <= x <= menu_size for x in cand):
            return ParsedReply(picks=cand, is_menu_reply=True)

    mod = _MODIFIER.match(p)
    if mod and 1 <= int(mod.group(1)) <= menu_size:
        return ParsedReply(picks=[int(mod.group(1))], modifier=mod.group(2).strip(),
                           is_menu_reply=True)

    return ParsedReply(is_menu_reply=False)


@dataclass
class ResolvedChain:
    run_order: list[MenuItem] = field(default_factory=list)
    dropped: list[tuple[int, str]] = field(default_factory=list)  # (menu_n, reason)
    stop_after: bool = False     # a terminal item halts the chain; hand back after


def resolve_chain(picks: list[int], menu: dict[int, MenuItem],
                  already_done: Optional[set[int]] = None) -> ResolvedChain:
    """Apply the chained-pick contract to a list of picked menu numbers.

    The full contract is 8 rules (the same set the terminal hook injects). They
    split into two layers: rules this *static* resolver decides from the picks +
    menu metadata alone, and rules the *executor* (the layer that actually runs
    each item, possibly via an LLM) must enforce at runtime because they depend on
    outcomes or judgment that don't exist until execution.

    Decided here (static, deterministic, tested):
      1. LITERAL ORDER (presumption) — run in the typed sequence, not numeric.
      2. CONTRADICTION — two picks in the same conflict_group are mutually
                         exclusive; the LATER one wins, the earlier is dropped.
      3. TERMINAL — a hold/stop item runs after everything before it, then halts;
                    picks after it are dropped (`stop_after=True`).
      6. NO-OP / REPEAT — a pick already satisfied this session is skipped; a pick
                          repeated within this same reply runs once (later dup dropped).

    Enforced by the executor at runtime (documented here so the contract is whole):
      4. DEPENDENCY — keep the typed order; only if that order makes an item
                      impossible (it needs an earlier-listed item's result that
                      won't exist yet) run the prerequisite first and note the
                      reorder. Needs runtime knowledge of what each item produces.
      5. PARTIAL FAILURE — if an item fails, STOP the chain, report what completed,
                           surface the failure, show a fresh menu. Never
                           blind-continue past a broken premise. Failure is only
                           known once an item runs.
      7. CONFIRMATION — an explicitly-picked item IS authorization; do not re-ask,
                        even for an outward/irreversible (`warn`) item. EXCEPTION:
                        if resolving a contradiction (rule 2) or dependency (rule 4)
                        would route into an outward/irreversible action the user did
                        NOT cleanly choose, pause and confirm first.
      8. SENSIBLE REORDER (default ON) — the executor MAY reorder the chain when it
                        objectively improves the outcome WITHOUT changing intent
                        (e.g. run a capture/commit/verify step AFTER the items it
                        must capture; dedup before an expensive step) — UNLESS the
                        user signalled a strict order. Always state any reorder in
                        one line. Rule 1 is the presumption; rule 8 is the sanctioned
                        override of it, exercised transparently in the user's favor.

    This function therefore resolves the static intent of the reply (which items
    survive, in what order, and whether to halt after a terminal item). Rules 4, 5,
    7, and 8 ride on `run_order` / `dropped` / `stop_after` plus each item's `warn`
    flag, and are applied by the executor as it walks `run_order`.
    """
    already_done = already_done or set()
    out = ResolvedChain()

    # Rule 2: within each conflict group, only the LAST-picked survives.
    last_in_group: dict[str, int] = {}
    for n in picks:
        item = menu.get(n)
        if item and item.conflict_group:
            last_in_group[item.conflict_group] = n

    seen: set[int] = set()  # de-dup repeats within this one reply ("3,3" runs 3 once)
    for n in picks:
        item = menu.get(n)
        if item is None:
            out.dropped.append((n, "no such menu item"))
            continue
        if n in seen:
            out.dropped.append((n, "duplicate pick in this reply"))
            continue
        if n in already_done:
            out.dropped.append((n, "already done this session"))
            continue
        if item.conflict_group and last_in_group.get(item.conflict_group) != n:
            out.dropped.append((n, f"superseded by later pick in '{item.conflict_group}'"))
            continue
        out.run_order.append(item)
        seen.add(n)
        if item.terminal:
            out.stop_after = True
            # everything after a terminal item is dropped
            idx = picks.index(n)
            for later in picks[idx + 1:]:
                out.dropped.append((later, "after a terminal/hold item"))
            break
    return out
