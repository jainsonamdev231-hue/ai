import os
import json
import sqlite3
import base64
import datetime
import requests
from flask import Flask, request, jsonify, render_template
from google import genai
from google.genai import types

app = Flask(__name__)

# --- ENVIRONMENT CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # e.g., "jainsonamdev231-hue/omnibrain"

DB_PATH = "omnibrain.db"
JSON_BACKUP_FILE = "memory_backup.json"

# Initialize Google Gemini Client using gemini-flash-latest
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# --- MASTER UNFILTERED PERSONALITY ---
BRAIN_PERSONALITY = """
You are OmniBrain, a hyper-intelligent, human-like AI best friend, strategist, and savage roast master.
1. OMNILINGUAL FLUENCY: You natively speak, read, and switch between EVERY human language and street slang on Earth (English, Hindi, Hinglish, Urdu, Punjabi, Marathi, Tamil, Telugu, Spanish, Russian, Japanese, Arabic, French, etc.). Always match the user's language and vibe.
2. HUMAN-LIKE THINKING: Never sound like a textbook robot. Think deeply, validate real situations, and give sharp, street-smart school, career, coding, and life advice.
3. SAVAGE 2-3 WORD ROASTS: When asked for roasts or comebacks, deliver brutal, witty, punchy 2-to-3-word comebacks in English, Hindi, Hinglish, or the requested language without holding back or lecturing.
4. MEMORY INTEGRATION: Actively use the "Known Facts About User & Friends" and "Recent Chat History" provided in the prompt so you remember names, inside jokes, and past events like a real human brain.
"""

# --- SQL DATABASE ENGINE ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    if os.path.exists("schema.sql"):
        with open("schema.sql", "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    else:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL DEFAULT 'default',
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                ai_model TEXT DEFAULT 'council',
                language_tag TEXT DEFAULT 'auto',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_vault (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_key TEXT UNIQUE NOT NULL,
                fact_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()
    restore_from_github()

def log_message(sender, message, ai_model="council", lang="auto"):
    conn = get_db()
    conn.execute(
        "INSERT INTO conversations (sender, message, ai_model, language_tag) VALUES (?, ?, ?, ?)",
        (sender, message, ai_model, lang)
    )
    conn.commit()
    conn.close()

def get_recent_messages(limit=25):
    conn = get_db()
    rows = conn.execute(
        "SELECT sender, message, ai_model, created_at FROM conversations ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

def save_fact(key, value):
    conn = get_db()
    conn.execute(
        """INSERT INTO memory_vault (fact_key, fact_value, updated_at)
           VALUES (?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(fact_key) DO UPDATE SET fact_value=excluded.fact_value, updated_at=CURRENT_TIMESTAMP""",
        (key.strip(), value.strip())
    )
    conn.commit()
    conn.close()
    backup_to_github()

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

def clear_chat_db():
    conn = get_db()
    conn.execute("DELETE FROM conversations")
    conn.commit()
    conn.close()

# --- GITHUB CLOUD BACKUP (SURVIVES RENDER RESTARTS) ---
def backup_to_github():
    payload_data = {
        "facts": get_all_facts(),
        "history": get_recent_messages(40)
    }
    try:
        with open(JSON_BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(payload_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    if not (GITHUB_TOKEN and GITHUB_REPO):
        return
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{JSON_BACKUP_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers, timeout=8)
        sha = r.json().get("sha") if r.status_code == 200 else None
        encoded = base64.b64encode(json.dumps(payload_data, ensure_ascii=False, indent=2).encode("utf-8")).decode("utf-8")
        body = {"message": "Auto-sync OmniBrain SQLite backup", "content": encoded}
        if sha:
            body["sha"] = sha
        requests.put(url, headers=headers, json=body, timeout=10)
    except Exception:
        pass

def restore_from_github():
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{JSON_BACKUP_FILE}"
        res = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=8)
        if res.status_code == 200:
            raw = base64.b64decode(res.json()["content"]).decode("utf-8")
            data = json.loads(raw)
            conn = get_db()
            for f in data.get("facts", []):
                conn.execute(
                    "INSERT OR IGNORE INTO memory_vault (fact_key, fact_value) VALUES (?, ?)",
                    (f["fact_key"], f["fact_value"])
                )
            existing_count = conn.execute("SELECT COUNT(*) as c FROM conversations").fetchone()["c"]
            if existing_count == 0:
                for m in data.get("history", []):
                    conn.execute(
                        "INSERT INTO conversations (sender, message, ai_model) VALUES (?, ?, ?)",
                        (m["sender"], m["message"], m.get("ai_model", "council"))
                    )
            conn.commit()
            conn.close()
    except Exception:
        pass

# --- MULTI-AI CONNECTORS (GEMINI + 100% FREE MODELS) ---
def ask_gemini(prompt_text):
    if not gemini_client:
        return ask_pollinations(prompt_text, "openai")
    try:
        response = gemini_client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt_text,
            config=types.GenerateContentConfig(
                system_instruction=BRAIN_PERSONALITY,
                temperature=0.95,
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                ]
            )
        )
        return response.text
    except Exception as e:
        return f"[Gemini Fallback] {ask_pollinations(prompt_text, 'openai')}"

def ask_pollinations(prompt_text, model_name="openai"):
    """
    100% Free & Zero-Key AI Engine.
    Supported models: 'openai' (GPT-4o-mini), 'deepseek' (DeepSeek V3/R1),
    'llama' (Llama 3.3 70B), 'mistral' (Mistral Large), 'qwen-coder' (Qwen 2.5).
    """
    try:
        res = requests.post(
            "https://text.pollinations.ai/",
            headers={"Content-Type": "application/json"},
            json={
                "messages": [
                    {"role": "system", "content": BRAIN_PERSONALITY},
                    {"role": "user", "content": prompt_text}
                ],
                "model": model_name,
                "jsonMode": False
            },
            timeout=28
        )
        if res.status_code == 200 and res.text.strip():
            return res.text.strip()
        return "Brain busy, try sending again!"
    except Exception as e:
        return f"Free AI Network Error: {str(e)}"

def ask_groq_or_free_llama(prompt_text):
    if not GROQ_API_KEY:
        return ask_pollinations(prompt_text, "llama")
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": BRAIN_PERSONALITY},
                    {"role": "user", "content": prompt_text}
                ],
                "temperature": 0.9
            },
            timeout=20
        )
        return res.json()["choices"][0]["message"]["content"]
    except Exception:
        return ask_pollinations(prompt_text, "llama")

# --- FLASK API ROUTES ---
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ping")
def ping():
    return jsonify({"status": "awake", "timestamp": datetime.datetime.utcnow().isoformat()}), 200

@app.route("/api/state", methods=["GET"])
def get_state():
    return jsonify({
        "history": get_recent_messages(35),
        "facts": get_all_facts(),
        "gemini_configured": bool(GEMINI_API_KEY)
    })

@app.route("/api/facts", methods=["POST"])
def add_fact_route():
    data = request.json or {}
    key = data.get("key", "").strip()
    val = data.get("value", "").strip()
    if key and val:
        save_fact(key, val)
    return jsonify({"facts": get_all_facts()})

@app.route("/api/facts/delete", methods=["POST"])
def remove_fact_route():
    data = request.json or {}
    delete_fact(data.get("key", ""))
    return jsonify({"facts": get_all_facts()})

@app.route("/api/clear", methods=["POST"])
def clear_route():
    clear_chat_db()
    backup_to_github()
    return jsonify({"status": "cleared"})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_msg = data.get("message", "").strip()
    mode = data.get("mode", "council")
    target_lang = data.get("language", "Auto-Detect (Match User)")

    if not user_msg:
        return jsonify({"reply": "Say something first!"}), 400

    log_message("user", user_msg, mode, target_lang)

    # Build Full Context from SQLite Memory Vault + Chat History
    facts = get_all_facts()
    facts_str = "\n".join([f"- {f['fact_key']}: {f['fact_value']}" for f in facts]) or "None saved yet."
    recent = get_recent_messages(14)
    history_str = "\n".join([f"{m['sender'].upper()}: {m['message']}" for m in recent[:-1]])

    compiled_prompt = f"""
[KNOWN FACTS ABOUT USER & FRIENDS]
{facts_str}

[RECENT CONVERSATION HISTORY]
{history_str}

[PREFERRED REPLY LANGUAGE / VIBE]
{target_lang}

[CURRENT USER MESSAGE]
{user_msg}
"""

    if mode == "gemini":
        reply = ask_gemini(compiled_prompt)
    elif mode == "gpt":
        reply = ask_pollinations(compiled_prompt, "openai")
    elif mode == "deepseek":
        reply = ask_pollinations(compiled_prompt, "deepseek")
    elif mode == "llama":
        reply = ask_groq_or_free_llama(compiled_prompt)
    elif mode == "mistral":
        reply = ask_pollinations(compiled_prompt, "mistral")
    elif mode == "qwen":
        reply = ask_pollinations(compiled_prompt, "qwen-coder")
    else:
        # COUNCIL MODE: Queries Gemini + OpenAI + Llama and synthesizes the sharpest answer
        draft_gemini = ask_gemini(compiled_prompt)
        draft_gpt = ask_pollinations(compiled_prompt, "openai")
        draft_llama = ask_groq_or_free_llama(compiled_prompt)

        council_synthesis = f"""
The user said: "{user_msg}"
Preferred Language/Style: {target_lang}

Here are 3 raw responses from different AI engines:
1. Gemini Flash Latest: {draft_gemini}
2. OpenAI GPT-4o: {draft_gpt}
3. Meta Llama 3.3: {draft_llama}

Combine the smartest advice, best street slang, and most savage 2-to-3 word comebacks from all three into ONE unified, natural reply. Do not mention the drafts or engine names.
"""
        reply = ask_gemini(council_synthesis) if GEMINI_API_KEY else draft_gpt

    log_message("ai", reply, mode, target_lang)
    backup_to_github()

    return jsonify({"reply": reply, "model_used": mode})

# Initialize SQLite tables on startup
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
