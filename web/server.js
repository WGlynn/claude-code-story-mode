// Story Mode — standalone web backend.
// Reimplements the loop without Claude Code hooks: it injects the menu-generation
// contract + the active profile + the user's cold-start context into the system
// prompt, calls the Claude API, and returns the assistant turn (which ends with a
// menu). The client renders the menu and sends back the user's number(s).
//
// Model is env-configurable. For production model choice + params, consult the
// claude-api reference rather than hardcoding.
import express from "express";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Anthropic from "@anthropic-ai/sdk";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");
const MODEL = process.env.STORY_MODEL || "claude-sonnet-4-6";
const PORT = process.env.PORT || 3000;

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const menuSpec = fs.readFileSync(path.join(ROOT, "engine", "menu_spec.md"), "utf8");
const profile = JSON.parse(
  fs.readFileSync(path.join(ROOT, "profiles", "demo.json"), "utf8")
);

function systemPrompt(coldStartContext) {
  // The contract + the profile + (on the first turn) the user's starting point.
  // Cold-start context dominates ranking so the first menu reads the user's real
  // situation instead of suggesting into a blank canvas.
  return [
    "You are an AI coding assistant running in Story Mode.",
    menuSpec,
    "\n## Active profile\n```json\n" + JSON.stringify(profile, null, 2) + "\n```",
    coldStartContext
      ? "\n## User's starting point (cold-start context — let this dominate the FIRST menu)\n" +
        coldStartContext
      : "",
  ].join("\n");
}

const app = express();
app.use(express.json());
app.use(express.static(ROOT));

// One turn of the loop. Body: { messages: [{role, content}], coldStart?: string }
app.post("/api/turn", async (req, res) => {
  try {
    const { messages = [], coldStart = "" } = req.body || {};
    const resp = await client.messages.create({
      model: MODEL,
      max_tokens: 2048,
      system: systemPrompt(coldStart),
      messages,
    });
    const text = resp.content.map((b) => (b.type === "text" ? b.text : "")).join("");
    res.json({ text });
  } catch (e) {
    res.status(500).json({ error: String(e?.message || e) });
  }
});

app.listen(PORT, () =>
  console.log(`Story Mode on http://localhost:${PORT}  (model: ${MODEL})`)
);
