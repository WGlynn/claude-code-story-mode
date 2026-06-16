"""Tests for engine/chained_pick.py.

Covers parse_reply and resolve_chain according to the chained-pick contract
documented in engine/menu_spec.md and implemented in engine/chained_pick.py.

No external dependencies — stdlib + pytest only.
"""
import sys
import os

# Allow `python -m pytest` from repo root without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from engine.chained_pick import (
    MenuItem,
    ParsedReply,
    ResolvedChain,
    parse_reply,
    resolve_chain,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_menu(*items: MenuItem) -> dict[int, MenuItem]:
    """Build a menu dict from a sequence of MenuItems."""
    return {item.n: item for item in items}


def simple_menu() -> dict[int, MenuItem]:
    """A plain 10-item menu with no special flags — good for basic tests."""
    return make_menu(*[MenuItem(n=i, text=f"Action {i}") for i in range(1, 11)])


# ---------------------------------------------------------------------------
# parse_reply — single-number picks
# ---------------------------------------------------------------------------

class TestParseReplySingleNumber:
    def test_single_digit(self):
        r = parse_reply("3")
        assert r.is_menu_reply is True
        assert r.picks == [3]
        assert r.modifier == ""
        assert r.toggle is None
        assert r.loop_n is None

    def test_single_digit_max_default(self):
        r = parse_reply("10")
        assert r.is_menu_reply is True
        assert r.picks == [10]

    def test_single_digit_one(self):
        r = parse_reply("1")
        assert r.is_menu_reply is True
        assert r.picks == [1]

    def test_out_of_range_zero(self):
        r = parse_reply("0")
        assert r.is_menu_reply is False

    def test_out_of_range_above_max(self):
        # Default menu_size is 10; 11 is out of range.
        r = parse_reply("11")
        assert r.is_menu_reply is False

    def test_custom_menu_size(self):
        # With a 5-item menu, 6 is out of range.
        r = parse_reply("6", menu_size=5)
        assert r.is_menu_reply is False

    def test_custom_menu_size_in_range(self):
        r = parse_reply("5", menu_size=5)
        assert r.is_menu_reply is True
        assert r.picks == [5]


# ---------------------------------------------------------------------------
# parse_reply — chained picks (numbers)
# ---------------------------------------------------------------------------

class TestParseReplyChainedNumbers:
    def test_chain_comma_separated(self):
        r = parse_reply("5,4,1")
        assert r.is_menu_reply is True
        assert r.picks == [5, 4, 1]

    def test_chain_order_preserved(self):
        # The literal typed order must be kept — not sorted.
        r = parse_reply("9,2,7")
        assert r.picks == [9, 2, 7]

    def test_chain_space_separated(self):
        r = parse_reply("3 1 2")
        assert r.is_menu_reply is True
        assert r.picks == [3, 1, 2]

    def test_chain_with_spaces_around_commas(self):
        r = parse_reply("5 , 4 , 1")
        assert r.is_menu_reply is True
        assert r.picks == [5, 4, 1]

    def test_chain_out_of_range_member(self):
        # 11 is out of range; the whole reply becomes non-menu.
        r = parse_reply("5,11,1")
        assert r.is_menu_reply is False


# ---------------------------------------------------------------------------
# parse_reply — letter keyspace (a-j)
# ---------------------------------------------------------------------------

class TestParseReplyLetterKeyspace:
    def test_single_letter_c_maps_to_3(self):
        r = parse_reply("c")
        assert r.is_menu_reply is True
        assert r.picks == [3]

    def test_letter_chain_maps_correctly(self):
        # e=5, d=4, a=1
        r = parse_reply("e,d,a")
        assert r.is_menu_reply is True
        assert r.picks == [5, 4, 1]

    def test_letter_a_maps_to_1(self):
        r = parse_reply("a")
        assert r.is_menu_reply is True
        assert r.picks == [1]

    def test_letter_j_maps_to_10(self):
        r = parse_reply("j")
        assert r.is_menu_reply is True
        assert r.picks == [10]

    def test_uppercase_letter_accepted(self):
        r = parse_reply("C")
        assert r.is_menu_reply is True
        assert r.picks == [3]

    def test_out_of_range_letter_k(self):
        # 'k' is the 11th letter, outside the a-j keyspace.
        r = parse_reply("k")
        assert r.is_menu_reply is False

    def test_letter_z_not_menu(self):
        r = parse_reply("z")
        assert r.is_menu_reply is False

    def test_prose_starting_with_letter_not_a_pick(self):
        # Long prose beginning with a letter must not be misread as a pick.
        r = parse_reply("can you explain how the auth flow works?")
        assert r.is_menu_reply is False

    def test_prose_single_word_starting_c_not_a_pick(self):
        # "cancel" starts with 'c' but is way longer than 24 chars limit — actually
        # it's short. The guard is len(p) <= 24, but multi-char word won't match
        # the letter-only regex _LETTER_PICKS which requires only [a-jA-J] chars.
        r = parse_reply("cancel")
        assert r.is_menu_reply is False


# ---------------------------------------------------------------------------
# parse_reply — modifier syntax  "N: tweak"
# ---------------------------------------------------------------------------

class TestParseReplyModifier:
    def test_modifier_basic(self):
        r = parse_reply("3: only the auth part")
        assert r.is_menu_reply is True
        assert r.picks == [3]
        assert r.modifier == "only the auth part"

    def test_modifier_stripped(self):
        r = parse_reply("7:   trim whitespace   ")
        assert r.is_menu_reply is True
        assert r.picks == [7]
        assert r.modifier == "trim whitespace"

    def test_modifier_dot_separator(self):
        r = parse_reply("2. just the tests")
        assert r.is_menu_reply is True
        assert r.picks == [2]
        assert r.modifier == "just the tests"

    def test_modifier_dash_separator(self):
        r = parse_reply("4- skip the intro")
        assert r.is_menu_reply is True
        assert r.picks == [4]
        assert r.modifier == "skip the intro"

    def test_modifier_out_of_range_not_menu(self):
        r = parse_reply("11: do something")
        assert r.is_menu_reply is False


# ---------------------------------------------------------------------------
# parse_reply — story loop
# ---------------------------------------------------------------------------

class TestParseReplyStoryLoop:
    def test_story_loop_n(self):
        r = parse_reply("story loop 4")
        assert r.is_menu_reply is True
        assert r.loop_n == 4
        assert r.picks == []
        assert r.toggle is None

    def test_story_loop_off(self):
        r = parse_reply("story loop off")
        assert r.is_menu_reply is True
        assert r.loop_n == 0

    def test_story_loop_case_insensitive(self):
        r = parse_reply("STORY LOOP 3")
        assert r.is_menu_reply is True
        assert r.loop_n == 3

    def test_story_loop_two_digit(self):
        r = parse_reply("story loop 10")
        assert r.is_menu_reply is True
        assert r.loop_n == 10


# ---------------------------------------------------------------------------
# parse_reply — story on / off toggles
# ---------------------------------------------------------------------------

class TestParseReplyToggles:
    def test_story_off(self):
        r = parse_reply("story off")
        assert r.is_menu_reply is True
        assert r.toggle == "off"
        assert r.picks == []
        assert r.loop_n is None

    def test_story_mode_off(self):
        r = parse_reply("story mode off")
        assert r.is_menu_reply is True
        assert r.toggle == "off"

    def test_story_on(self):
        r = parse_reply("story on")
        assert r.is_menu_reply is True
        assert r.toggle == "on"

    def test_story_mode_on(self):
        r = parse_reply("story mode on")
        assert r.is_menu_reply is True
        assert r.toggle == "on"

    def test_activate_story_mode(self):
        r = parse_reply("activate story mode")
        assert r.is_menu_reply is True
        assert r.toggle == "on"

    def test_toggle_case_insensitive(self):
        r = parse_reply("Story Off")
        assert r.is_menu_reply is True
        assert r.toggle == "off"


# ---------------------------------------------------------------------------
# parse_reply — non-menu replies (prose)
# ---------------------------------------------------------------------------

class TestParseReplyNonMenu:
    def test_plain_prose(self):
        r = parse_reply("What do you think about using Redis here?")
        assert r.is_menu_reply is False

    def test_empty_string(self):
        r = parse_reply("")
        assert r.is_menu_reply is False

    def test_none_like_empty(self):
        r = parse_reply(None)  # type: ignore[arg-type]
        assert r.is_menu_reply is False

    def test_number_at_start_of_sentence(self):
        # "3 things I want..." — the trailing text prevents menu-match.
        r = parse_reply("3 things I want to cover:")
        assert r.is_menu_reply is False

    def test_large_number_in_prose(self):
        r = parse_reply("100")
        assert r.is_menu_reply is False


# ---------------------------------------------------------------------------
# resolve_chain — basic ordering
# ---------------------------------------------------------------------------

class TestResolveChainLiteralOrder:
    def test_single_pick_runs(self):
        menu = simple_menu()
        rc = resolve_chain([3], menu)
        assert [i.n for i in rc.run_order] == [3]
        assert rc.dropped == []
        assert rc.stop_after is False

    def test_chain_literal_order_preserved(self):
        menu = simple_menu()
        rc = resolve_chain([5, 4, 1], menu)
        assert [i.n for i in rc.run_order] == [5, 4, 1]

    def test_chain_order_not_sorted(self):
        menu = simple_menu()
        rc = resolve_chain([9, 2, 7], menu)
        assert [i.n for i in rc.run_order] == [9, 2, 7]


# ---------------------------------------------------------------------------
# resolve_chain — CONTRADICTION (conflict_group)
# ---------------------------------------------------------------------------

class TestResolveChainContradiction:
    def _conflict_menu(self):
        return make_menu(
            MenuItem(n=1, text="Enable dark mode", conflict_group="theme"),
            MenuItem(n=2, text="Enable light mode", conflict_group="theme"),
            MenuItem(n=3, text="Save file"),
        )

    def test_later_pick_wins(self):
        menu = self._conflict_menu()
        # 1 then 2: item 2 is later, so item 2 wins; item 1 is dropped.
        rc = resolve_chain([1, 2, 3], menu)
        assert [i.n for i in rc.run_order] == [2, 3]
        dropped_ns = [n for n, _ in rc.dropped]
        assert 1 in dropped_ns

    def test_earlier_pick_dropped_with_reason(self):
        menu = self._conflict_menu()
        rc = resolve_chain([1, 2], menu)
        dropped_ns = [n for n, _ in rc.dropped]
        reasons = [reason for _, reason in rc.dropped]
        assert 1 in dropped_ns
        assert any("superseded" in r.lower() or "theme" in r.lower() for r in reasons)

    def test_reversed_order_opposite_winner(self):
        menu = self._conflict_menu()
        # 2 then 1: item 1 is later, so item 1 wins.
        rc = resolve_chain([2, 1], menu)
        assert [i.n for i in rc.run_order] == [1]
        dropped_ns = [n for n, _ in rc.dropped]
        assert 2 in dropped_ns

    def test_no_conflict_when_same_item_not_conflicting(self):
        menu = make_menu(
            MenuItem(n=1, text="Action A"),
            MenuItem(n=2, text="Action B"),
        )
        rc = resolve_chain([1, 2], menu)
        assert [i.n for i in rc.run_order] == [1, 2]
        assert rc.dropped == []


# ---------------------------------------------------------------------------
# resolve_chain — TERMINAL
# ---------------------------------------------------------------------------

class TestResolveChainTerminal:
    def _terminal_menu(self):
        return make_menu(
            MenuItem(n=1, text="Run tests"),
            MenuItem(n=2, text="Pause and review", terminal=True),
            MenuItem(n=3, text="Deploy to prod"),
        )

    def test_terminal_runs_then_halts(self):
        menu = self._terminal_menu()
        rc = resolve_chain([1, 2, 3], menu)
        # Items before terminal run; terminal itself runs; item after is dropped.
        assert [i.n for i in rc.run_order] == [1, 2]
        assert rc.stop_after is True

    def test_picks_after_terminal_dropped(self):
        menu = self._terminal_menu()
        rc = resolve_chain([1, 2, 3], menu)
        dropped_ns = [n for n, _ in rc.dropped]
        assert 3 in dropped_ns
        reasons = [r for _, r in rc.dropped]
        assert any("terminal" in r.lower() or "hold" in r.lower() for r in reasons)

    def test_terminal_first_only_item(self):
        menu = self._terminal_menu()
        rc = resolve_chain([2], menu)
        assert [i.n for i in rc.run_order] == [2]
        assert rc.stop_after is True
        assert rc.dropped == []

    def test_stop_after_false_without_terminal(self):
        menu = simple_menu()
        rc = resolve_chain([1, 2, 3], menu)
        assert rc.stop_after is False


# ---------------------------------------------------------------------------
# resolve_chain — NO-OP / already done
# ---------------------------------------------------------------------------

class TestResolveChainNoOp:
    def test_already_done_skipped(self):
        menu = simple_menu()
        rc = resolve_chain([1, 2, 3], menu, already_done={2})
        assert [i.n for i in rc.run_order] == [1, 3]
        dropped_ns = [n for n, _ in rc.dropped]
        assert 2 in dropped_ns

    def test_already_done_drop_reason(self):
        menu = simple_menu()
        rc = resolve_chain([1, 2], menu, already_done={2})
        reasons = [r for _, r in rc.dropped]
        assert any("already done" in r.lower() for r in reasons)

    def test_already_done_empty_set(self):
        menu = simple_menu()
        rc = resolve_chain([1, 2], menu, already_done=set())
        assert [i.n for i in rc.run_order] == [1, 2]

    def test_already_done_none_default(self):
        menu = simple_menu()
        rc = resolve_chain([1, 2], menu, already_done=None)
        assert [i.n for i in rc.run_order] == [1, 2]


# ---------------------------------------------------------------------------
# resolve_chain — unknown / missing menu items
# ---------------------------------------------------------------------------

class TestResolveChainUnknownItem:
    def test_unknown_number_dropped(self):
        menu = simple_menu()
        # Pick 99 is not in the menu.
        rc = resolve_chain([1, 99, 3], menu)
        assert [i.n for i in rc.run_order] == [1, 3]
        dropped_ns = [n for n, _ in rc.dropped]
        assert 99 in dropped_ns

    def test_unknown_item_drop_reason(self):
        menu = simple_menu()
        rc = resolve_chain([99], menu)
        assert rc.dropped[0][0] == 99
        assert "no such menu item" in rc.dropped[0][1].lower()

    def test_all_unknown_gives_empty_run_order(self):
        menu = simple_menu()
        rc = resolve_chain([50, 99], menu)
        assert rc.run_order == []
        assert len(rc.dropped) == 2


# ---------------------------------------------------------------------------
# resolve_chain — empty picks
# ---------------------------------------------------------------------------

class TestResolveChainEdgeCases:
    def test_empty_picks(self):
        menu = simple_menu()
        rc = resolve_chain([], menu)
        assert rc.run_order == []
        assert rc.dropped == []
        assert rc.stop_after is False

    def test_single_item_menu_pick(self):
        menu = make_menu(MenuItem(n=1, text="Only action"))
        rc = resolve_chain([1], menu)
        assert [i.n for i in rc.run_order] == [1]


# ---------------------------------------------------------------------------
# Integration: parse_reply -> resolve_chain round-trip
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_chain_string_to_resolved_order(self):
        menu = simple_menu()
        r = parse_reply("5,4,1")
        assert r.is_menu_reply is True
        rc = resolve_chain(r.picks, menu)
        assert [i.n for i in rc.run_order] == [5, 4, 1]

    def test_letter_chain_to_resolved_order(self):
        menu = simple_menu()
        r = parse_reply("e,d,a")  # e=5, d=4, a=1
        assert r.is_menu_reply is True
        rc = resolve_chain(r.picks, menu)
        assert [i.n for i in rc.run_order] == [5, 4, 1]

    def test_modifier_preserved_through_resolution(self):
        menu = simple_menu()
        r = parse_reply("3: only the auth part")
        assert r.modifier == "only the auth part"
        rc = resolve_chain(r.picks, menu)
        assert [i.n for i in rc.run_order] == [3]

    def test_contradiction_resolved_in_chain_string(self):
        menu = make_menu(
            MenuItem(n=1, text="Light theme", conflict_group="theme"),
            MenuItem(n=2, text="Dark theme", conflict_group="theme"),
            MenuItem(n=5, text="Save"),
        )
        r = parse_reply("1,2,5")
        rc = resolve_chain(r.picks, menu)
        # 2 is later in the "theme" group, so 1 is dropped.
        assert [i.n for i in rc.run_order] == [2, 5]
