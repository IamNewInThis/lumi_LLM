# main.py
import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import httpx

load_dotenv()
PORT = int(os.getenv("PORT", 8000))

# OPEN AI
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o") 

# PPLX
PPLX_KEY = os.getenv("PPLX_API_KEY")
PPLX_API_URL = "https://api.perplexity.ai/chat/completions"
PPLX_MODEL = os.getenv("PPLX_MODEL", "sonar")

if not OPENAI_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno (.env)")

app = FastAPI(title="Sol Local Chat Proxy")

# CORS sencillo para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod restringir a tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    profile: dict | None = None

# POST CHAT BOT DE OPENAI   
@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="message required")

    system_prompt = "Eres un asistente experto en crianza. Responde con tono empático y práctico."
    profile_text = f"\n\nPerfil: {payload.profile}" if payload.profile else ""

    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{payload.message}{profile_text}"},
        ],
        "max_tokens": 800,
        "temperature": 0.7,
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json",
    }

    # Llamada a OpenAI (async)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(OPENAI_API_URL, json=body, headers=headers)

    try:
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="OpenAI returned non-json response")

    if resp.status_code // 100 != 2:
        # Reenvía el detalle del error de OpenAI para debugging
        raise HTTPException(status_code=502, detail={"openai_error": data})

    # Extraer texto de la respuesta
    assistant_text = ""
    try:
        assistant_text = data.get("choices", [])[0].get("message", {}).get("content", "")
    except Exception:
        assistant_text = ""

    usage = data.get("usage", {})

    return {"answer": assistant_text, "usage": usage}

# POST CHAT BOT DE OPENAI PERPLEXITY
@app.post("/api/chat/pplx")
async def chat_endpoint_pplx(payload: ChatRequest):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="message required")

    if not PPLX_KEY:
        raise HTTPException(status_code=500, detail="Falta PPLX_API_KEY en variables de entorno (.env)")

    system_prompt = "Eres un asistente experto en crianza. Responde con tono empático y práctico."
    profile_text = f"\n\nPerfil: {payload.profile}" if payload.profile else ""

    body = {
        "model": PPLX_MODEL,
        "messages": [
            {"role": "system", "content": "Responde siempre de manera muy breve, máximo 1 o 2 frases."},
            {"role": "user", "content": f"{payload.message}{profile_text}"},
        ],
        "max_tokens": 30,
        "temperature": 0.5,
    }

    headers = {
        "Authorization": f"Bearer {PPLX_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(PPLX_API_URL, json=body, headers=headers)

    try:
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Perplexity devolvió una respuesta no-JSON")

    if resp.status_code // 100 != 2:
        raise HTTPException(status_code=502, detail={"perplexity_error": data})

    assistant_text = ""
    try:
        assistant_text = data.get("choices", [])[0].get("message", {}).get("content", "")
    except Exception:
        assistant_text = ""

    usage = data.get("usage", {})

    return {"answer": assistant_text, "usage": usage}
