import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from ..models.chat import ChatRequest
from ..auth import get_current_user
from ..rag.utils import get_rag_context
from ..rag.retriever import supabase

router = APIRouter()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
PPLX_KEY = os.getenv("PPLX_API_KEY")
PPLX_MODEL = os.getenv("PPLX_MODEL", "sonar")

if not OPENAI_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno (.env)")

async def get_user_profiles_and_babies(user_id, supabase_client):
    # Ejemplo simple
    profiles = supabase_client.table("profiles").select("*").eq("id", user_id).execute()
    babies = supabase_client.table("babies").select("*").eq("user_id", user_id).execute()

    profile_texts = [f"{p['name']} ({p['birthdate']} años)" for p in profiles.data] if profiles.data else []
    baby_texts = [f"{b['name']} ({b['birthdate']} meses)" for b in babies.data] if babies.data else []

    return "\n".join(profile_texts + baby_texts)


@router.post("/api/chat")
async def chat_openai(payload: ChatRequest, user=Depends(get_current_user)):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message required")

    rag_context = await get_rag_context(payload.message)
    user_context = await get_user_profiles_and_babies(user["id"], supabase)

    system_prompt = "Eres un asistente experto en crianza. Responde con tono empático y práctico."
    profile_text = f"\n\nPerfil: {payload.profile}" if payload.profile else ""

    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"{payload.message}{profile_text}\n\n{user_context}\n\n{rag_context}",
            },
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