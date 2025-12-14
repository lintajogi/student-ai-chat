# ============================================================
# main.py — Render-safe FastAPI + Groq
# ============================================================

print("🚀 main.py loaded")

import os
import uuid
import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from groq import Groq

# ============================================================
# Logging
# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("student-ai-chat")

# ============================================================
# Environment variables (Render-safe)
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_DEFAULT_MODEL", "llama-3.1-8b-instant")

if not GROQ_API_KEY:
    logger.warning("⚠️ GROQ_API_KEY is missing. App will still start.")

# ============================================================
# FastAPI app
# ============================================================

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret-key")
)

# ============================================================
# Groq client (lazy-safe)
# ============================================================

groq_client = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

# ============================================================
# Storage (Render-safe)
# ============================================================

CHAT_LOG_DIR = Path("/tmp/chat_logs")
CHAT_LOG_DIR.mkdir(exist_ok=True)

# In-memory sessions
user_sessions = {}

# ============================================================
# Models
# ============================================================

class ChatRequest(BaseModel):
    message: str

# ============================================================
# Utilities
# ============================================================

def save_chat(session_id: str, messages: list):
    try:
        file_path = CHAT_LOG_DIR / f"{session_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "session_id": session_id,
                    "saved_at": datetime.utcnow().isoformat(),
                    "messages": messages
                },
                f,
                indent=2,
                ensure_ascii=False
            )
    except Exception:
        logger.exception("Failed to save chat")

# ============================================================
# Startup hook (VERY IMPORTANT FOR RENDER)
# ============================================================

@app.on_event("startup")
async def startup_event():
    logger.info("✅ FastAPI startup complete")
    logger.info(f"Using model: {GROQ_MODEL}")

# ============================================================
# Routes
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    try:
        with open("app/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            "<h2>index.html not found</h2>",
            status_code=500
        )

@app.post("/chat")
async def chat(request: Request, data: ChatRequest):
    session = request.session

    if "session_id" not in session:
        session["session_id"] = uuid.uuid4().hex

    session_id = session["session_id"]

    if session_id not in user_sessions:
        user_sessions[session_id] = [
            {
                "role": "system",
                "content": "You are a helpful student AI assistant."
            }
        ]

    messages = user_sessions[session_id]
    messages.append({"role": "user", "content": data.message})

    # If Groq is not available, fail gracefully
    if not groq_client:
        reply = "⚠️ AI service not configured."
    else:
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages
            )
            reply = response.choices[0].message.content
        except Exception:
            logger.exception("Groq API error")
            reply = "⚠️ AI error. Please try again."

    messages.append({"role": "assistant", "content": reply})
    save_chat(session_id, messages)

    return JSONResponse({"reply": reply})

# ============================================================
# Health check (VERY USEFUL)
# ============================================================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": GROQ_MODEL,
        "groq_ready": bool(groq_client)
    }
