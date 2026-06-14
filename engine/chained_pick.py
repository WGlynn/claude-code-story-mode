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


_PICKS = re.compile(r"\s*(\d{1,2}(?:\s*[,\s]\s*\d{1,2})*)\s*$")
_MODIFIER = re.compile(r"\s*(\d{1,2})\s*[:.\-]\s+(.+)", re.DOTALL)
_LOOP = re.compile(r"story\s+loop\s+(off|\d{1,2})", re.IGNORECASE)


def parse_reply(prompt: str, menu_size: int = 10) -> ParsedReply:
    """Turn a raw user prompt into a structured reply against a menu of menu_size."""
    p = (prompt or "").strip()
    low = p.lower()

    if low in ("story off", "story mode off"):
        return ParsedReply(toggle="off", is_menu_reply=True)
    if low in ("story on", "story mode on", "activate story mode"):
        return ParsedReply(toggle="on", is_menu_reply=True)

    lm = _LOOP.fullmatch(low)
    if lm:
        arg = lm.group(1)
        return ParsedReply(loop_n=(0 if arg == "off" else int(arg)), is_menu_reply=True)

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

    Rules (order matters):
      1. LITERAL order  — run in the typed sequence, not numeric.
      2. CONTRADICTION  — two picks in the same conflict_group are mutually
                          exclusive; the LATER one wins, the earlier is dropped.
      3. TERMINAL       — a hold/stop item runs after everything before it, then
                          halts; picks after it are dropped.
      4. NO-OP/REPEAT   — a pick already satisfied this session is skipped.
    (Dependency reordering and partial-failure halting are runtime concerns the
    executor handles; this resolves the static intent of the reply.)
    """
    already_done = already_done or set()
    out = ResolvedChain()

    # Rule 2: within each conflict group, only the LAST-picked survives.
    last_in_group: dict[str, int] = {}
    for n in picks:
        item = menu.get(n)
        if item and item.conflict_group:
            last_in_group[item.conflict_group] = n

    for n in picks:
        item = menu.get(n)
        if item is None:
            out.dropped.append((n, "no such menu item"))
            continue
        if n in already_done:
            out.dropped.append((n, "already done this session"))
            continue
        if item.conflict_group and last_in_group.get(item.conflict_group) != n:
            out.dropped.append((n, f"superseded by later pick in '{item.conflict_group}'"))
            continue
        out.run_order.append(item)
        if item.terminal:
            out.stop_after = True
            # everything after a terminal item is dropped
            idx = picks.index(n)
            for later in picks[idx + 1:]:
                out.dropped.append((later, "after a terminal/hold item"))
            break
    return out
