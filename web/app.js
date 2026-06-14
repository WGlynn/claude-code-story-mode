// Story Mode — client loop + chain builder.
// Renders each assistant turn, parses the trailing menu into tappable cards, and
// sends the user's reply (a number, a chain like "5,4,1", or free text) for the
// next turn. The FIRST message is treated as cold-start context so the opening
// menu reads the user's real situation, not a blank canvas.
//
// Interaction: tap a card body = run it now. Tap the card's "+" = queue it into a
// chain; the chain bar shows the ordered queue and RUN fires them all at once
// ("fire a batch, walk away"). Typing "5,4,1" works too.

const log = document.getElementById("log");
const box = document.getElementById("box");
const chainbar = document.getElementById("chainbar");
const chainq = document.getElementById("chainq");
const runchain = document.getElementById("runchain");

const messages = []; // conversation sent to the backend
let coldStart = "";
let started = false;
const chain = []; // ordered [{ n, text, card }]

const MENU_TITLE = "Story Mode -- reply with a number";

function add(role, text) {
  const div = document.createElement("div");
  div.className = "turn " + role;
  div.textContent = text;
  log.appendChild(div);
  return div;
}

// Split an assistant turn into prose + parsed menu items {n, text, warn}.
function parseMenu(text) {
  const idx = text.indexOf(MENU_TITLE);
  if (idx === -1) return { prose: text, items: [] };
  const prose = text.slice(0, idx).trimEnd();
  const items = [];
  for (const line of text.slice(idx).split("\n")) {
    const m = line.match(/^\s*(\d{1,2})\.\s*(⚠\s*)?(.+?)\s*$/);
    if (m) items.push({ n: +m[1], warn: !!m[2], text: m[3] });
  }
  return { prose, items };
}

function renderChain() {
  chainq.innerHTML = "";
  chain.forEach((c, i) => {
    if (i) {
      const arr = document.createElement("span");
      arr.className = "arr";
      arr.textContent = "→";
      chainq.appendChild(arr);
    }
    const q = document.createElement("span");
    q.className = "q";
    q.textContent = c.n;
    q.title = "remove from chain";
    q.onclick = () => removeFromChain(c.n);
    chainq.appendChild(q);
  });
  chainbar.classList.toggle("on", chain.length > 0);
}

function addToChain(n, text, card) {
  if (chain.some((c) => c.n === n && c.card === card)) return;
  chain.push({ n, text, card });
  card?.classList.add("queued");
  renderChain();
}

function removeFromChain(n) {
  const i = chain.findIndex((c) => c.n === n);
  if (i === -1) return;
  chain[i].card?.classList.remove("queued");
  chain.splice(i, 1);
  renderChain();
}

function clearChain() {
  for (const c of chain) c.card?.classList.remove("queued");
  chain.length = 0;
  renderChain();
}

function renderAssistant(text) {
  const { prose, items } = parseMenu(text);
  if (prose) add("assistant", prose);
  if (!items.length) return;
  const menu = document.createElement("div");
  menu.className = "menu";
  const title = document.createElement("div");
  title.className = "menu-title";
  title.textContent = "pick a path";
  menu.appendChild(title);

  items.forEach((it, i) => {
    const card = document.createElement("div");
    card.className = "card" + (it.warn ? " warn" : "");
    card.style.animationDelay = `${i * 35}ms`;

    const body = document.createElement("button");
    body.className = "body";
    body.setAttribute("aria-label", `run option ${it.n}: ${it.text}`);
    body.onclick = () => send(String(it.n));
    const key = document.createElement("span");
    key.className = "key";
    key.textContent = String(it.n);
    const label = document.createElement("span");
    label.className = "label";
    label.textContent = (it.warn ? "⚠ " : "") + it.text;
    body.append(key, label);

    const addBtn = document.createElement("button");
    addBtn.className = "add";
    addBtn.textContent = "+";
    addBtn.title = "queue into a chain";
    addBtn.setAttribute("aria-label", `add option ${it.n} to the chain`);
    addBtn.onclick = () => addToChain(it.n, it.text, card);

    card.append(body, addBtn);
    menu.appendChild(card);
  });
  log.appendChild(menu);
}

async function send(reply) {
  clearChain();
  document.getElementById("hero")?.remove();
  add("user", reply);
  if (!started) {
    coldStart = reply; // first message = the starting point
    started = true;
  }
  messages.push({ role: "user", content: reply });
  const pending = add("assistant pending", "");
  try {
    const r = await fetch("/api/turn", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ messages, coldStart }),
    });
    const data = await r.json();
    pending.remove();
    if (data.error) return add("assistant", "error: " + data.error);
    messages.push({ role: "assistant", content: data.text });
    renderAssistant(data.text);
  } catch (e) {
    pending.remove();
    add("assistant", "network error: " + e.message);
  }
  document.getElementById("composer").scrollIntoView({ block: "end" });
}

runchain.onclick = () => {
  if (!chain.length) return;
  const reply = chain.map((c) => c.n).join(",");
  send(reply);
};

box.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && box.value.trim()) {
    const v = box.value.trim();
    box.value = "";
    send(v);
  }
});
