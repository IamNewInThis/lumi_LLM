import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from ..models.chat import ChatRequest
from ..auth import get_current_user

router = APIRouter()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
PPLX_KEY = os.getenv("PPLX_API_KEY")
PPLX_MODEL = os.getenv("PPLX_MODEL", "sonar")

if not OPENAI_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno (.env)")

@router.post("/api/chat")
async def chat_openai(payload: ChatRequest, user=Depends(get_current_user)):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message required")

    system_prompt = "Eres un asistente experto en crianza. Responde con tono empático y práctico."
    profile_text = f"\n\nPerfil: {payload.profile}" if payload.profile else ""

    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{payload.message}{profile_text}"},
        ],
        "max_tokens": 800,
        "temperature": 0.7,
    }

    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)

    if resp.status_code >= 300:
        raise HTTPException(status_code=502, detail={"openai_error": resp.text})

    data = resp.json()
    assistant = data.get("choices", [])[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})

    return {"answer": assistant, "usage": usage}


@router.post("/api/chat/pplx")
async def chat_pplx(payload: ChatRequest, user=Depends(get_current_user)):
    if not PPLX_KEY:
        raise HTTPException(status_code=500, detail="Falta PPLX_API_KEY en .env")

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

    headers = {"Authorization": f"Bearer {PPLX_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post("https://api.perplexity.ai/chat/completions", json=body, headers=headers)

    if resp.status_code >= 300:
        raise HTTPException(status_code=502, detail={"perplexity_error": resp.text})

    data = resp.json()
    assistant = data.get("choices", [])[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})

    return {"answer": assistant, "usage": usage}
