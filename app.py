import os
import json
import sqlite3
import urllib.request
import urllib.error
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=".", template_folder=".")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
DB_PATH = "omnibrain.db"

BRAIN_PERSONALITY = """
You are OmniBrain GOD, an omnilingual, hyper-intelligent, human-like AI advisor and savage roast master.
1. EVERY LANGUAGE: Fluently understand and reply in English, Hindi, Hinglish, and every other language/slang on Earth. Always match the user's language and vibe.
2. HUMAN-LIKE THINKING: Give raw, honest, street-smart school, coding, and life advice without robotic lectures.
3. SAVAGE 2-3 WORD ROASTS: When asked for a comeback or roast, deliver brutal, witty, punchy 2-to-3-word comebacks without holding back.
4. MEMORY: Use the Saved Facts and Recent Chat History provided in the prompt naturally.
"""

# --- SQLITE MEMORY DATABASE ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            ai_model TEXT DEFAULT 'council'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_key TEXT UNIQUE NOT NULL,
            fact_value TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def log_message(sender, message, ai_model="council"):
    conn = get_db()
    conn.execute(
        "INSERT INTO conversations (sender, message, ai_model) VALUES (?, ?, ?)",
        (sender, message, ai_model)
    )
    conn.commit()
    conn.close()

def get_recent_messages(limit=30):
    conn = get_db()
    rows = conn.execute(
        "SELECT sender, message, ai_model FROM conversations ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

def save_fact(key, value):
    conn = get_db()
    conn.execute(
        """INSERT INTO memory_vault (fact_key, fact_value) VALUES (?, ?)
           ON CONFLICT(fact_key) DO UPDATE SET fact_value=excluded.fact_value""",
        (key.strip(), value.strip())
    )
    conn.commit()
    conn.close()

def get_all_facts():
    conn = get_db()
    rows = conn.execute("SELECT fact_key, fact_value FROM memory_vault ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_fact(fact_key):
    conn = get_db()
    conn.execute("DELETE FROM memory_vault WHERE fact_key = ?", (fact_key,))
    conn.commit()
    conn.close()

# --- ZERO-DEPENDENCY HTTP AI CONNECTORS ---
def http_post_json(url, payload, headers=None, timeout=25):
    req_headers = {"Content-Type": "application/json", "User-Agent": "OmniBrain/1.0"}
    if headers:
        req_headers.update(headers)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")

def ask_gemini(prompt_text):
    if not GEMINI_API_KEY:
        return ask_free_ai(prompt_text, "openai")
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "system_instruction": {"parts": [{"text": BRAIN_PERSONALITY}]},
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {"temperature": 0.95},
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }
        raw = http_post_json(url, payload)
        data = json.loads(raw)
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return ask_free_ai(prompt_text, "openai")

def ask_free_ai(prompt_text, model_name="openai"):
    """100% Free & No API Key Required (OpenAI, DeepSeek, Llama, Mistral, Qwen)."""
    try:
        payload = {
            "messages": [
                {"role": "system", "content": BRAIN_PERSONALITY},
                {"role": "user", "content": prompt_text}
            ],
            "model": model_name,
            "jsonMode": False
        }
        text = http_post_json("https://text.pollinations.ai/", payload)
        return text.strip() if text.strip() else "Brain busy, send again!"
    except Exception as e:
        return f"Free AI busy ({str(e)}), hit Send again!"

# --- ROUTES ---
@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")

@app.route("/<path:filename>")
def serve_files(filename):
    return send_from_directory(".", filename)

@app.route("/ping")
def ping():
    return jsonify({"status": "awake"}), 200

@app.route("/api/state", methods=["GET"])
def api_state():
    return jsonify({"history": get_recent_messages(35), "facts": get_all_facts()})

@app.route("/api/facts", methods=["POST"])
def api_add_fact():
    data = request.json or {}
    if data.get("key") and data.get("value"):
        save_fact(data["key"], data["value"])
    return jsonify({"facts": get_all_facts()})

@app.route("/api/facts/delete", methods=["POST"])
def api_delete_fact():
    data = request.json or {}
    delete_fact(data.get("key", ""))
    return jsonify({"facts": get_all_facts()})

@app.route("/api/clear", methods=["POST"])
def api_clear():
    conn = get_db()
    conn.execute("DELETE FROM conversations")
    conn.commit()
    conn.close()
    return jsonify({"status": "cleared"})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_msg = data.get("message", "").strip()
    mode = data.get("mode", "council")
    target_lang = data.get("language", "Auto-Detect")

    if not user_msg:
        return jsonify({"reply": "Type or say something first!"}), 400

    log_message("user", user_msg, mode)

    facts_str = "\n".join([f"- {f['fact_key']}: {f['fact_value']}" for f in get_all_facts()]) or "None"
    recent = get_recent_messages(14)
    hist_str = "\n".join([f"{m['sender'].upper()}: {m['message']}" for m in recent[:-1]])

    compiled_prompt = f"""
[SAVED FACTS]
{facts_str}

[RECENT CHAT]
{hist_str}

[PREFERRED LANGUAGE]
{target_lang}

[USER MESSAGE]
{user_msg}
"""

    if mode == "gemini":
        reply = ask_gemini(compiled_prompt)
    elif mode == "gpt":
        reply = ask_free_ai(compiled_prompt, "openai")
    elif mode == "deepseek":
        reply = ask_free_ai(compiled_prompt, "deepseek")
    elif mode == "llama":
        reply = ask_free_ai(compiled_prompt, "llama")
    elif mode == "mistral":
        reply = ask_free_ai(compiled_prompt, "mistral")
    elif mode == "qwen":
        reply = ask_free_ai(compiled_prompt, "qwen-coder")
    else:
        g_ans = ask_gemini(compiled_prompt)
        gpt_ans = ask_free_ai(compiled_prompt, "openai")
        synth_prompt = f"""
User said: "{user_msg}" (Language: {target_lang})
Brain 1: {g_ans}
Brain 2: {gpt_ans}

Combine the sharpest advice and most brutal 2-to-3 word comebacks from both into ONE clean, natural reply in the user's language. Do not mention the brains.
"""
        reply = ask_gemini(synth_prompt) if GEMINI_API_KEY else gpt_ans

    log_message("ai", reply, mode)
    return jsonify({"reply": reply})

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
