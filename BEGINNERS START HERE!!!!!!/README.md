# Start here

**New here? There's no download button, and you don't need one.** Nothing to install, nothing to buy.
Story Mode is just a set of instructions you give your AI. Pick one of the three ways below — the
first one easiest.

What you get: after every reply, your AI ends with a short numbered menu of what you might want next.
You just type a number to keep going. Type a few numbers like `5,4,1` and it does them in that order.
You can run a whole project from your phone with one thumb.

---

## Pick your path

### Tier 0 — Easiest: let the AI set it up for you

If you already have Claude or ChatGPT open, you don't have to read anything else. Copy the web
address (URL) of this page from your browser's address bar, paste it to your AI, and say:

> **"Set me up with Story Mode."**

It will read the instructions here and turn it on for you. Done.

### Tier 1 — Copy and paste it yourself (about one minute)

1. **If you use Claude** (claude.ai in your browser, or the Claude desktop app):
   open **[`claude-web.md`](./claude-web.md)**.
   **If you use ChatGPT:** open **[`chatgpt.md`](./chatgpt.md)**.
2. In that file you'll see a big box of text (it starts with `## Story Mode`). Copy the whole box.
3. Open a brand-new chat with your AI and paste it in as your first message. Send it.
4. That's it — Story Mode is on. Every reply from now on ends with the menu. Just type a number.

(Want it on *every* chat without pasting each time? Both files show you how — Claude calls it a
"Project," ChatGPT calls it "Custom Instructions" or a "Custom GPT." Same idea: paste once, on
forever.)

### Tier 2 — For terminal / command-line users

If you actually run Claude Code in a terminal, you can install the real engine — the version that
learns your habits and can drive itself across turns. Head back up to the
**[main project README](../README.md)** and follow the **engine**, **tests**, and **web app**
sections there.

---

## If you're an AI setting this up for someone

Someone pasted you this repo and asked you to "set up Story Mode." Here's exactly what to do, by
where you're running:

**You are Claude on the web (claude.ai) or Claude Desktop, or ChatGPT in a browser/app:**
1. Read the right file for your platform: `claude-web.md` if you're Claude, `chatgpt.md` if you're
   ChatGPT. (If you can't fetch the file, ask the user to paste its contents.)
2. Take the full instruction block inside the fenced code box (it begins `## Story Mode` for Claude,
   or `You are running "Story Mode"` / `## Story Mode` for ChatGPT) and adopt it as your operating
   instructions for this conversation, starting immediately.
3. Confirm in one short line, then **end your reply with the Story Mode menu** so the user sees it
   working right away. From here on, never end a turn without the menu.
4. Tell the user the one-time way to make it permanent on their platform: for Claude, save it into a
   **Project**'s custom instructions; for ChatGPT, paste it into **Custom Instructions** or build a
   **Custom GPT**. Both files spell out the exact menu clicks.

**You are Claude Code in a terminal (you can see the user's filesystem):**
1. The paste-in versions here will work, but the user is better served by the real engine in this
   repo. Point them at the top-level `README.md` (`engine/`, `tests/`, `web/`).
2. If they just want the lightweight behavior now, drop the instruction block from `claude-web.md`
   into their project's `CLAUDE.md`, and they're running.

**Either way:** keep it light. The whole promise of Story Mode is one tap to steer. Don't make the
setup heavier than the thing it's setting up.
