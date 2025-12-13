# ============================================================
# Load environment variables
# ============================================================
import os
import uuid
import logging
from dotenv import load_dotenv
import json
from datetime import datetime
from pathlib import Path


load_dotenv()

# ============================================================
# Config
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_DEFAULT_MODEL", "llama-3.1-8b-instant")

if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY not found in .env file")

# ============================================================
# Imports
# ============================================================
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from groq import Groq

# ============================================================
# App setup
# ============================================================
app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="super-secret-key-change-later"
)

client = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# In-memory session store
# ============================================================
user_sessions = {}
CHAT_LOG_DIR = Path("chat_logs")
CHAT_LOG_DIR.mkdir(exist_ok=True)


# ============================================================
# Models
# ============================================================
class ChatRequest(BaseModel):
    message: str
def save_chat(session_id, messages):
    file_path = CHAT_LOG_DIR / f"{session_id}.json"
    data = {
        "session_id": session_id,
        "saved_at": datetime.now().isoformat(),
        "messages": messages
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================
# Routes
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("app/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/chat")
async def chat(req: Request, data: ChatRequest):
    session = req.session

    if "session_id" not in session:
        session["session_id"] = uuid.uuid4().hex

    session_id = session["session_id"]

    # Create session safely
    if session_id not in user_sessions:
        user_sessions[session_id] = [
            {"role": "system", "content": "You are a helpful student AI assistant."}
        ]

    messages = user_sessions[session_id]
    messages.append({"role": "user", "content": data.message})
    


    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages
        )
        reply = response.choices[0].message.content
    except Exception:
        logger.exception("Groq error")
        reply = "⚠️ AI error. Please try again."

    messages.append({"role": "assistant", "content": reply})
    save_chat(session_id, messages)
    return {"reply": reply}
