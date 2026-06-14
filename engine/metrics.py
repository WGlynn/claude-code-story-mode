"""Catch-rate metrics — is the menu actually anticipating the user?

Every Story-Mode turn is one menu impression. Classifying it pick-vs-off-menu
gives the denominator a catch-rate needs. The headline number is a LOWER BOUND:
the off-menu bucket mixes three classes an analysis must split —

  - paraphrase-catch : the menu HAD the action, the user typed it out anyway
                       (a true catch undercounted as a miss)
  - conversational   : banter / meta / a question no menu could anticipate
                       (exclude from the denominator entirely)
  - genuine miss     : the user wanted something absent from all 10 items
                       (the only real miss; mine these to improve menu-gen)

Feed it a list of impression dicts: {"kind": "pick"|"off_menu", "picked": [int]}.
Stdlib only.
"""
from __future__ import annotations


def summarize(impressions: list[dict]) -> dict:
    n = len(impressions)
    n_pick = sum(1 for r in impressions if r.get("kind") == "pick")
    n_off = sum(1 for r in impressions if r.get("kind") == "off_menu")

    # recall@10 lower bound: of all menus shown, how many did a number answer?
    recall_lb = round(n_pick / n, 4) if n else 0.0

    # precision@3: of picks, how many landed in the top 3 slots (menu ranked well)?
    top3 = 0
    picked_total = 0
    pos_dist: dict[int, int] = {}
    for r in impressions:
        for p in r.get("picked", []) or []:
            picked_total += 1
            pos_dist[p] = pos_dist.get(p, 0) + 1
            if p <= 3:
                top3 += 1
    precision_at_3 = round(top3 / picked_total, 4) if picked_total else 0.0

    return {
        "impressions_total": n,
        "impressions_pick": n_pick,
        "impressions_offmenu": n_off,
        "catch_rate_recall_at_10_lower_bound": recall_lb,
        "precision_at_3": precision_at_3,
        "pick_position_distribution": dict(sorted(pos_dist.items())),
        "note": (
            "recall is a LOWER BOUND: off_menu still contains paraphrase-catches "
            "(true catches) and conversational turns (not menu failures). Split "
            "them with last-menu paraphrase detection (see docs/lastmenu-design.md) "
            "to recover the true rate."
        ),
    }


if __name__ == "__main__":
    import json
    import sys

    rows = [json.loads(l) for l in sys.stdin if l.strip()]
    print(json.dumps(summarize(rows), indent=2))
