# Story Mode

Story Mode is how you operate an autonomous agent without becoming a passenger.

Most "autonomous AI" puts you in one of two bad seats: you either babysit every step, or you
hand over the wheel and watch. Story Mode is a third option. The agent does the work, and at the
end of every turn it hands you a short numbered menu of the most likely next moves. You reply with
a number, or chain several at once like `5,4,1` to run them in order. The session branches forward
like a pick-your-own-adventure novel, except the branches are real work and you are the one
choosing the path. That multi-pick is the whole trick: one reply can queue a sequence of moves, so
you are not clicking through a wizard, you are directing.

## It is the original game AI, on an LLM

The first things ever called game AI were branch trees. Zork, the dungeon dialogue, choose your
own adventure. You typed a choice, the world responded, you chose again. Story Mode is that exact
loop with two changes. The branches are generated live by a language model instead of written in
advance, and the choices do real work instead of advancing a plot. The dungeon master went from a
lookup table to a mind, and the dungeon became your actual project. That is gamified vibe coding:
the loose, intuition-led way of building with an AI, turned into a game you navigate one keystroke
at a time.

## How it works

At the end of each turn the agent appends a menu titled **Story Mode** — ten options, ranked by
probability, each a complete instruction short enough to execute when you reply with just its
number. No re-typing. The menu is built from two things: the user's own signature-response
patterns (how this person actually decides) and the live decision on the table (what the next move
genuinely could be). Seven items are shaped to the specific situation; three are standing moves
the person reaches for again and again.

Reply `3` and option three happens. Reply `5,4,1` and they happen in order. The interface
collapses the cost of directing an autonomous agent down to a keystroke, which means you can stay
in control across a long run without it feeling like work.

## Why it is more than a menu

A menu that guesses well is a menu that knows you. Story Mode keeps a record of which option you
actually picked each time, and a background loop measures its own hit rate — how often your real
choice was in the top few it offered — and reweights the ranking toward your patterns. The menu
gets better at being you the more you use it.

That is the real point. The branch you pick is the decision the agent would otherwise have made
alone. Story Mode keeps the human as the author of the story rather than a reader of it. The agent
renders each branch in full; you decide which branch becomes real. Autonomy stops being "the agent
acts for you" and becomes "the agent proposes, you author, at the speed of a single number."

## The shape of it

- Every turn ends in a fork.
- Every fork is ten labeled paths, ranked, executable by number.
- The session is the branch you walked.
- The menu learns your hand over time.

It reads like a game because it is one, in the good sense: the kind where the choices are yours and
they matter, and the world is rendered for you the moment you choose. Build with an agent long
enough and you stop wanting any other interface.

## Runs anywhere

The above is the full version: a set of local hooks, so it runs where Claude Code can reach your
filesystem (terminal, desktop app, IDE). For the web app, where hooks can't run, there's a hookless
drop-in that keeps the menu and the number-replies, just without the learning loop:
[STORY-MODE-LITE.md](STORY-MODE-LITE.md).
