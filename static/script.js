const chatBox = document.getElementById("chat-box");
const userInput = document.getElementById("user-input");
const aiMode = document.getElementById("ai-mode");
const replyLang = document.getElementById("reply-lang");
const voiceLang = document.getElementById("voice-lang");
const micBtn = document.getElementById("mic-btn");
const muteBtn = document.getElementById("mute-btn");
const factList = document.getElementById("fact-list");
const sidebar = document.getElementById("sidebar");

let voiceEnabled = true;

// Load Permanent SQLite History & Memory Vault on Startup
window.addEventListener("DOMContentLoaded", async () => {
  try {
    const res = await fetch("/api/state");
    const data = await res.json();
    renderFacts(data.facts || []);
    if (data.history && data.history.length > 0) {
      data.history.forEach((m) => appendMessage(m.message, m.sender, m.ai_model, false));
    } else {
      appendMessage(
        "Yo! OmniBrain PRO is live. Connected to Gemini Flash Latest + 100% Free OpenAI, DeepSeek, Llama 3.3, Mistral & Qwen.\n\n• Ask for deep life/school advice or code.\n• Hit '🔥 2-3 Word Roast' for brutal comebacks in Hindi, Hinglish, English, or any language.\n• Open the '☰ Vault' to save permanent facts about your friends!",
        "ai",
        "council",
        false
      );
    }
  } catch (err) {
    appendMessage("⚠️ Loaded offline view. Start Flask backend to sync database.", "ai", "system", false);
  }
});

// Enter to send (Shift+Enter for new line)
userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

function toggleSidebar() {
  sidebar.classList.toggle("open");
}

function toggleVoiceOutput() {
  voiceEnabled = !voiceEnabled;
  muteBtn.textContent = voiceEnabled ? "🔊 Voice: ON" : "🔇 Voice: OFF";
  if (!voiceEnabled && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}

function speakText(text) {
  if (!voiceEnabled || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();

  const clean = text.replace(/[*#_`~>-]/g, "");
  const utter = new SpeechSynthesisUtterance(clean);
  utter.lang = voiceLang.value;
  utter.rate = 1.05;
  utter.pitch = 1.0;
  window.speechSynthesis.speak(utter);
}

function copyText(text) {
  navigator.clipboard.writeText(text);
}

function appendMessage(text, sender, modelTag = "council", autoSpeak = false) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${sender}`;

  const bodySpan = document.createElement("div");
  bodySpan.textContent = text;
  wrap.appendChild(bodySpan);

  if (sender === "ai") {
    const meta = document.createElement("div");
    meta.className = "msg-meta";
    meta.innerHTML = `<span>🧠 ${modelTag.toUpperCase()}</span>`;

    const actions = document.createElement("div");
    actions.className = "msg-actions";

    const speakBtn = document.createElement("button");
    speakBtn.textContent = "🔊 Speak";
    speakBtn.onclick = () => speakText(bodySpan.textContent);

    const copyBtn = document.createElement("button");
    copyBtn.textContent = "📋 Copy";
    copyBtn.onclick = () => copyText(bodySpan.textContent);

    actions.appendChild(speakBtn);
    actions.appendChild(copyBtn);
    meta.appendChild(actions);
    wrap.appendChild(meta);
  }

  chatBox.appendChild(wrap);
  chatBox.scrollTop = chatBox.scrollHeight;

  if (autoSpeak && sender === "ai") {
    speakText(text);
  }
  return bodySpan;
}

async function sendMessage(overrideText = null) {
  const text = overrideText || userInput.value.trim();
  if (!text) return;
  if (!overrideText) userInput.value = "";

  appendMessage(text, "user", aiMode.value, false);
  const thinkingNode = appendMessage("Syncing AI brains...", "ai", aiMode.value, false);

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        mode: aiMode.value,
        language: replyLang.value
      })
    });
    const data = await res.json();
    thinkingNode.textContent = data.reply;
    speakText(data.reply);
  } catch (e) {
    thinkingNode.textContent = "⚠️ Connection error. Check if server is awake.";
  }
}

function quickRoast() {
  const target = userInput.value.trim() || "someone acting oversmart in front of friends";
  userInput.value = "";
  sendMessage(
    `Deliver 6 brutal, witty, unfiltered 2-to-3 word comebacks/roasts in English, Hindi, and Hinglish school/street slang for: "${target}". Format them cleanly so I can use them immediately.`
  );
}

function triggerPresetRoast(style) {
  const target = userInput.value.trim() || "someone trying to act cool and roast me";
  userInput.value = "";
  sendMessage(`Style: ${style}. Give me 6 savage 2-to-3 word comebacks for: "${target}".`);
  if (window.innerWidth <= 820) toggleSidebar();
}

function quickPrompt(promptText) {
  sendMessage(promptText);
}

// --- MEMORY VAULT CRUD ---
function renderFacts(facts) {
  factList.innerHTML = "";
  if (!facts.length) {
    factList.innerHTML = `<div class="sidebar-sub">No facts saved yet. Add one above!</div>`;
    return;
  }
  facts.forEach((f) => {
    const item = document.createElement("div");
    item.className = "fact-item";
    item.innerHTML = `<div><strong>${f.fact_key}:</strong> ${f.fact_value}</div>`;
    const delBtn = document.createElement("button");
    delBtn.className = "fact-del";
    delBtn.textContent = "✖";
    delBtn.onclick = () => removeFact(f.fact_key);
    item.appendChild(delBtn);
    factList.appendChild(item);
  });
}

async function saveFact() {
  const keyEl = document.getElementById("fact-key");
  const valEl = document.getElementById("fact-val");
  if (!keyEl.value.trim() || !valEl.value.trim()) return;

  const res = await fetch("/api/facts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: keyEl.value, value: valEl.value })
  });
  const data = await res.json();
  keyEl.value = "";
  valEl.value = "";
  renderFacts(data.facts);
}

async function removeFact(key) {
  const res = await fetch("/api/facts/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key })
  });
  const data = await res.json();
  renderFacts(data.facts);
}

async function wipeHistory() {
  await fetch("/api/clear", { method: "POST" });
  chatBox.innerHTML = "";
  appendMessage("🧹 Chat history cleared! Your Memory Vault facts are still safe.", "ai", "system", false);
}

function exportChat() {
  const messages = Array.from(chatBox.querySelectorAll(".msg")).map((m) => m.innerText).join("\n\n---\n\n");
  const blob = new Blob([messages], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "omnibrain-chat-export.txt";
  a.click();
}

// --- MICROPHONE SPEECH RECOGNITION ---
function startListening() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert("Voice recognition works best in Google Chrome or Edge.");
    return;
  }
  const rec = new SpeechRecognition();
  rec.lang = voiceLang.value;
  rec.interimResults = false;

  micBtn.classList.add("listening");
  rec.onresult = (e) => {
    const text = e.results[0][0].transcript;
    userInput.value = text;
    sendMessage(text);
  };
  rec.onerror = () => micBtn.classList.remove("listening");
  rec.onend = () => micBtn.classList.remove("listening");
  rec.start();
}
