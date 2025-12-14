# ============================================================
# Render-safe FastAPI + Groq (MINIMAL & STABLE)
# ============================================================

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

print("🚀 app/main.py loaded")

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("student-ai-chat")

# ------------------------------------------------------------
# Environment variables (Render provides these)
# ------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_DEFAULT_MODEL", "llama-3.1-8b-instant")

# ------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------
app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "render-dev-secret")
)

# ------------------------------------------------------------
# Groq client (safe)
# ------------------------------------------------------------
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ------------------------------------------------------------
# Storage (Render-safe: /tmp only)
# ------------------------------------------------------------
CHAT_LOG_DIR = Path("/tmp/chat_logs")
CHAT_LOG_DIR.mkdir(exist_ok=True)

user_sessions = {}

# ------------------------------------------------------------
# Models
# ------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str

# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "ok", "service": "student-ai-chat"}

@app.post("/chat")
async def chat(request: Request, data: ChatRequest):
    session = request.session

    if "session_id" not in session:
        session["session_id"] = uuid.uuid4().hex

    sid = session["session_id"]

    if sid not in user_sessions:
        user_sessions[sid] = [
            {"role": "system", "content": "You are a helpful student AI assistant."}
        ]

    messages = user_sessions[sid]
    messages.append({"role": "user", "content": data.message})

    if not groq_client:
        reply = "⚠️ GROQ_API_KEY not configured."
    else:
        try:
            res = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages
            )
            reply = res.choices[0].message.content
        except Exception as e:
            logger.exception("Groq error")
            reply = "⚠️ AI error. Try again."

    messages.append({"role": "assistant", "content": reply})

    with open(CHAT_LOG_DIR / f"{sid}.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2)

    return JSONResponse({"reply": reply})

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "groq_ready": bool(groq_client),
        "model": GROQ_MODEL
    }
