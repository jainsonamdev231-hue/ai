/* ==========================================================================
   OMNIBRAIN GOD MODE — DUAL-ENGINE JAVASCRIPT CONTROLLER
   Automatically runs on Render Python Backend OR 100% Standalone on GitHub Pages
   ========================================================================== */

const chatBox = document.getElementById("chat-box");
const userInput = document.getElementById("user-input");
const aiMode = document.getElementById("ai-mode");
const replyLang = document.getElementById("reply-lang");
const voiceLang = document.getElementById("voice-lang");
const micBtn = document.getElementById("mic-btn");
const muteBtn = document.getElementById("mute-btn");
const factList = document.getElementById("fact-list");
const sidebar = document.getElementById("sidebar");
const runtimeBadge = document.getElementById("runtime-badge");
const localKeyInput = document.getElementById("local-gemini-key");

let voiceEnabled = true;
let backendAvailable = false;

// Master System Personality for Standalone Mode
const MASTER_PERSONALITY = `
You are OmniBrain GOD, an omnilingual, hyper-intelligent, human-like AI advisor and savage roast master.
1. EVERY LANGUAGE: Fluently understand and reply in English, Hindi, Hinglish, and every other language/slang on Earth. Match the user's exact vibe.
2. DEEP HUMAN THINKING: Give raw, honest, street-smart life, school, and coding advice without robotic lectures.
3. SAVAGE 2-3 WORD ROASTS: When asked for a comeback or roast, deliver brutal, witty, punchy 2-to-3-word comebacks without holding back.
4. MEMORY: Use saved facts and recent conversation history naturally like a real human brain.
`;

// --- LOCAL BROWSER STORAGE HELPERS (FOR GITHUB PAGES / NO-RENDER MODE) ---
function getLocalFacts() {
  return JSON.parse(localStorage.getItem("omnibrain_facts") || "[]");
}
function setLocalFacts(facts) {
  localStorage.setItem("omnibrain_facts", JSON.stringify(facts));
}
function getLocalHistory() {
  return JSON.parse(localStorage.getItem("omnibrain_history") || "[]");
}
function setLocalHistory(hist) {
  localStorage.setItem("omnibrain_history", JSON.stringify(hist.slice(-50)));
}
function getLocalGeminiKey() {
  return localStorage.getItem("omnibrain_gemini_key") || "";
}
function saveLocalKey() {
  const key = localKeyInput.value.trim();
  if (!key) return;
  localStorage.setItem("omnibrain_gemini_key", key);
  localKeyInput.value = "";
  alert("Gemini API Key saved safely in your browser!");
}

// --- INITIALIZE APP & DETECT RUNTIME MODE ---
window.addEventListener("DOMContentLoaded", async () => {
  try {
    // Check if Python Flask / Render server is active
    const res = await fetch("/api/state", { cache: "no-store" });
    if (res.ok) {
      backendAvailable = true;
      const data = await res.json();
      runtimeBadge.textContent = "⚡ GOD MODE: Python / Render Server Connected";
      renderFacts(data.facts || []);
      if (data.history && data.history.length > 0) {
        data.history.forEach((m) => appendMessage(m.message, m.sender, m.ai_model || "council", false));
        return;
      }
    }
  } catch (_) {
    backendAvailable = false;
  }

  // Fallback to 100% Standalone Browser Mode (GitHub Pages Ready!)
  runtimeBadge.textContent = "🌐 STANDALONE MODE: Running 100% on GitHub / Browser";
  renderFacts(getLocalFacts());
  const localHist = getLocalHistory();
  if (localHist.length > 0) {
    localHist.forEach((m) => appendMessage(m.message, m.sender, m.ai_model || "free-ai", false));
  } else {
    appendMessage(
      "Yo! OmniBrain GOD MODE is live!\n• Works on GitHub Pages AND Render.\n• Connected to Gemini Flash Latest + 100% Free OpenAI, DeepSeek, Llama 3.3, Mistral & Qwen.\n• Ask for deep advice or tap '🔥 2-3 Word Roast' in English, Hindi, Hinglish, or any language!",
      "ai",
      "god-mode",
      false
    );
  }
});

// Send message on Enter key (Shift+Enter adds new line)
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

// Text-to-Speech Output
function speakText(text) {
  if (!voiceEnabled || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const cleanText = text.replace(/[*#_`~>-]/g, "");
  const utterance = new SpeechSynthesisUtterance(cleanText);
  utterance.lang = voiceLang.value;
  utterance.rate = 1.05;
  utterance.pitch = 1.0;
  window.speechSynthesis.speak(utterance);
}

function copyText(text) {
  navigator.clipboard.writeText(text);
}

// Render Message Bubble into Chat Stream
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
  if (autoSpeak && sender === "ai") speakText(text);
  return bodySpan;
}

// Direct Browser AI Engine (Used when running on GitHub Pages without Render)
async function runStandaloneAI(promptText, mode) {
  const apiKey = getLocalGeminiKey();

  // 1. Use Gemini Flash Latest directly if user saved their key
  if ((mode === "gemini" || mode === "council") && apiKey) {
    try {
      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=${encodeURIComponent(apiKey)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            system_instruction: { parts: [{ text: MASTER_PERSONALITY }] },
            contents: [{ parts: [{ text: promptText }] }],
            generationConfig: { temperature: 0.95 }
          })
        }
      );
      const data = await res.json();
      const reply = data?.candidates?.[0]?.content?.parts?.[0]?.text;
      if (reply) return reply;
    } catch (_) {}
  }

  // 2. Key-Free Trending AI Models (OpenAI, DeepSeek, Llama, Mistral, Qwen)
  const modelMap = {
    gpt: "openai",
    deepseek: "deepseek",
    llama: "llama",
    mistral: "mistral",
    qwen: "qwen-coder",
    gemini: "openai",
    council: "openai"
  };

  const res = await fetch("https://text.pollinations.ai/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages: [
        { role: "system", content: MASTER_PERSONALITY },
        { role: "user", content: promptText }
      ],
      model: modelMap[mode] || "openai"
    })
  });
  return (await res.text()).trim();
}

// Main Send Handler
async function sendMessage(overrideText = null) {
  const text = overrideText || userInput.value.trim();
  if (!text) return;
  if (!overrideText) userInput.value = "";

  appendMessage(text, "user", aiMode.value, false);
  const thinkingNode = appendMessage("Thinking across AI brains...", "ai", aiMode.value, false);

  try {
    // Route A: Render / Python Server Mode
    if (backendAvailable) {
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
      return;
    }

    // Route B: Standalone GitHub Pages Browser Mode
    const facts = getLocalFacts().map((f) => `- ${f.fact_key}: ${f.fact_value}`).join("\n");
    const hist = getLocalHistory().slice(-12).map((m) => `${m.sender.toUpperCase()}: ${m.message}`).join("\n");
    const fullPrompt = `[SAVED FACTS]\n${facts}\n\n[RECENT CHAT]\n${hist}\n\n[PREFERRED LANGUAGE]\n${replyLang.value}\n\n[USER MESSAGE]\n${text}`;

    const reply = await runStandaloneAI(fullPrompt, aiMode.value);
    thinkingNode.textContent = reply;
    speakText(reply);

    const updated = getLocalHistory();
    updated.push({ sender: "user", message: text, ai_model: aiMode.value });
    updated.push({ sender: "ai", message: reply, ai_model: aiMode.value });
    setLocalHistory(updated);
  } catch (err) {
    thinkingNode.textContent = "⚠️ Network hiccup—please hit Send again!";
  }
}

// Quick Roast Button
function quickRoast() {
  const target = userInput.value.trim() || "someone acting oversmart in school";
  userInput.value = "";
  sendMessage(
    `Give me 6 brutal, savage, witty 2-to-3 word comebacks/roasts in English, Hindi, and Hinglish school/street slang for: "${target}".`
  );
}

function triggerPresetRoast(style) {
  const target = userInput.value.trim() || "someone trying to roast me";
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
    factList.innerHTML = `<div style="font-size:0.8rem;color:#94a3b8;">No facts saved yet. Add one above!</div>`;
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

  if (backendAvailable) {
    const res = await fetch("/api/facts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: keyEl.value, value: valEl.value })
    });
    const data = await res.json();
    renderFacts(data.facts);
  } else {
    const facts = getLocalFacts().filter((f) => f.fact_key !== keyEl.value.trim());
    facts.push({ fact_key: keyEl.value.trim(), fact_value: valEl.value.trim() });
    setLocalFacts(facts);
    renderFacts(facts);
  }
  keyEl.value = "";
  valEl.value = "";
}

async function removeFact(key) {
  if (backendAvailable) {
    const res = await fetch("/api/facts/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key })
    });
    const data = await res.json();
    renderFacts(data.facts);
  } else {
    const facts = getLocalFacts().filter((f) => f.fact_key !== key);
    setLocalFacts(facts);
    renderFacts(facts);
  }
}

async function wipeHistory() {
  if (backendAvailable) {
    await fetch("/api/clear", { method: "POST" });
  } else {
    localStorage.removeItem("omnibrain_history");
  }
  chatBox.innerHTML = "";
  appendMessage("🧹 Chat history cleared! Memory Vault facts are safe.", "ai", "system", false);
}

function exportChat() {
  const text = Array.from(chatBox.querySelectorAll(".msg")).map((m) => m.innerText).join("\n\n---\n\n");
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "omnibrain-chat.txt";
  a.click();
}

// Microphone Voice-to-Text
function startListening() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert("Voice input works best in Chrome or Edge.");
    return;
  }
  const rec = new SpeechRecognition();
  rec.lang = voiceLang.value;
  micBtn.classList.add("listening");
  rec.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    userInput.value = transcript;
    sendMessage(transcript);
  };
  rec.onerror = () => micBtn.classList.remove("listening");
  rec.onend = () => micBtn.classList.remove("listening");
  rec.start();
}
