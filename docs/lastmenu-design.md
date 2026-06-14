# Design — `_lastmenu.json` in-gate paraphrase detection (Story Mode cycle-2)

**Status:** DESIGN (not built). Authored 2026-06-14 (item 5 of chained pick).
**Motivation:** cycle-1 found the catch-rate (0.26) is a measurement artifact — the
`off_menu` bucket is polluted by *paraphrase-picks*: the user typed out an action the
menu DID offer (e.g. "Triage the 210 HIGH-urgency open threads" when slot-1 was a triage
item). These count as misses but are true catches. `_lastmenu.json` lets the gate tell
the two apart.

## The structural problem

`story-mode-gate.py` is a `UserPromptSubmit` hook. It sees ONLY the user's prompt. The
menu it must compare against lives in the PREVIOUS assistant turn's output, which this
hook never receives. So detection requires TWO cooperating hooks:

1. **Capture (new, Stop hook):** after each assistant turn, parse the emitted menu's 10
   items + their `⚠` safety markers and persist them to `_lastmenu.json`.
2. **Match (extend gate):** on an `off_menu` freetext prompt, fuzzy-match it against the
   10 stored item texts. On a strong match, reclassify the impression.

## The load-bearing split: MEASUREMENT vs ACTION

A fuzzy false-positive has two wildly different blast radii. The design MUST keep them
separate; conflating them is the trap the session-state note warned about.

| Use | False-positive cost | Threshold | Auto-act? |
|---|---|---|---|
| **MEASUREMENT** — reclassify `off_menu`→`paraphrase_pick` for the catch-rate metric | only mis-measures a number; self-correcting next cycle | lenient (≥0.55 token-Jaccard) | yes, silent |
| **ACTION** — route the prompt to item N's instruction | **wrong irreversible action** (push/post/delete) | n/a — NEVER | **NO** |

Rule: `_lastmenu.json` may **reclassify a metric** automatically. It may **never
auto-execute** a menu item from a fuzzy match. The most it does on the action axis is
emit a *soft surface*: "your prompt resembles item N (`<text>`) — treating as freetext;
reply `N` to run it as written." The LLM/user stays the executor. This makes a
false-positive cost = one extra sentence, never a wrong action.

Stronger guard: if the best-matched item carries the `⚠` marker (outward/irreversible),
suppress even the soft surface — an outward action must be picked by an explicit number,
never inferred from prose.

## `_lastmenu.json` schema

```json
{
  "t": 1781221250.0,
  "turn_id": "optional-uuid",
  "items": [
    {"n": 1, "text": "Recompute Story Mode true catch-rate post-gate-fix", "warn": false},
    {"n": 6, "text": "Draft one Odysseus issue batch for your review", "warn": true}
  ]
}
```

- Written by the Stop hook each turn; overwritten (only the LAST menu matters).
- `warn` = the item had a leading `⚠`. Drives the action-axis suppression above.
- Stale guard: if `now - t > 1800s` (30 min), treat as expired — a prompt that long
  after the menu is a fresh thread, not a paraphrase-pick. Skip matching.

## Matching function (lean, stdlib, deterministic)

```
sim(prompt, item) = |tokens(prompt) ∩ tokens(item.text)| / |tokens(prompt) ∪ tokens(item.text)|
  tokens = lowercased word-set, stopwords removed, len>=3
```

- token-set Jaccard, NOT edit-distance: order-invariant, robust to the user adding
  scope-words ("triage the HIGH ones" vs "Triage the open threads").
- best = argmax over the 10 items. Reclassify (measurement) iff best.sim >= 0.55.
- Soft-surface (action) iff best.sim >= 0.70 AND NOT item.warn AND not expired.
- Two thresholds on purpose: measurement is forgiving (only a count), the surface is
  strict (it nudges behavior).

## New impression `kind`

`paraphrase_pick` joins `pick` / `off_menu`. The metric then computes:

```
true_catch_rate = (pick + paraphrase_pick) / (pick + paraphrase_pick + genuine_miss)
```

where `genuine_miss` = off_menu that matched NOTHING (best.sim < 0.55). Conversational
turns ("tell me about x", "lol what does 10 mean") will naturally fall below 0.55 and
stay excluded — the existing cron-injection guard already drops `type:` turns. This
finally gives the denominator the cycle-1 note asked for.

## Why this is honest, not metric-gaming

Reclassifying a paraphrase-pick as a catch is only honest if the match is real. The 0.55
floor is deliberately ABOVE incidental word-overlap (a 4-word prompt sharing 2 generic
words with an item lands ~0.2–0.3). Set it by labelling the ~9 historical off_menu rows
once and picking the threshold that separates the one true paraphrase
("Triage the 210 HIGH...") from the conversational rows — then freeze it. Do NOT tune the
threshold to hit a target catch-rate; that would be measuring the ruler.

## Build order (when armed)

1. Stop hook `story-mode-lastmenu-capture.py`: regex the menu block
   (`^\s*(\d{1,2})[.)]\s*(⚠\s*)?(.+)$` under the EXACT title line), write `_lastmenu.json`.
2. Extend `story-mode-gate.py`: in the `off_menu` branch, load `_lastmenu.json`, run
   `sim`, set `kind=paraphrase_pick` on measurement-hit, append the soft-surface clause to
   `additionalContext` on action-hit.
3. Extend `story_mode_metrics.py`: count `paraphrase_pick`, emit `true_catch_rate`
   alongside the existing lower bound (keep BOTH — the lower bound stays as the
   never-overcount floor).
4. One regression: feed the 9 historical off_menu rows, assert exactly the known
   paraphrase reclassifies and the conversational rows do not.

## NOT building today

Keep it lean: this is the design only. Ship after a real Story-Mode session accumulates
more off-menu rows to calibrate the 0.55 floor on real labels — calibrating on one
positive example is overfitting. Wait for the labels before tuning the threshold.
